#!/usr/bin/env python3
"""
Efficiency comparison: CLI vs Python API, and hvswdpy vs Disba

Part 1 — CLI vs API: compares computing efficiency of the original Fortran CLI
  (hv_orig) and the Python API (hvswdpy.hv) for computing H/V curves.

Part 2 — hvswdpy vs Disba: benchmarks runtime for computing Rayleigh and Love
  phase-velocity dispersion curves, sweeping number of frequency samples.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: CLI vs Python API efficiency
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import shutil
from pathlib import Path
import subprocess
import time
import statistics as stats
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches
import numpy as np
from typing import Tuple

EXAMPLES_DIR = Path(__file__).resolve().parent if '__file__' in dir() else Path.cwd().resolve()
ROOT = EXAMPLES_DIR.parent
SRC = ROOT / 'src'
BIN = ROOT / 'bin'
BIN.mkdir(exist_ok=True)

print(f"[setup] Examples dir : {EXAMPLES_DIR}")
print(f"[setup] Root dir     : {ROOT}")
print(f"[setup] Source dir   : {SRC}")
print(f"[setup] Binary dir   : {BIN}")

try:
    import hvswdpy as hv
except ModuleNotFoundError:
    sys.path.insert(0, str(SRC))
    import hvswdpy as hv
print(f"[setup] hvswdpy imported from: {hv.__file__}")

hv_which = shutil.which('hv_orig')
if hv_which:
    HV_EXE = hv_which
elif (BIN / 'hv_orig').exists():
    HV_EXE = str(BIN / 'hv_orig')
else:
    print('[setup] CLI binary not found, building via make hv_orig in src ...')
    subprocess.run(['make', 'hv_orig'], cwd=str(SRC), check=True)
    assert (BIN / 'hv_orig').exists(), 'Expected hv_orig to be built in bin/'
    HV_EXE = str(BIN / 'hv_orig')
print(f"[setup] CLI binary   : {HV_EXE}")
print("[setup] Setup complete.\n")


# ── Helper functions ─────────────────────────────────────────────────────────

def read_model(path: Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    print(f"[read_model] Reading: {path}")
    with open(path, 'r') as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    n = int(lines[0])
    vp, vs, rho, th = [], [], [], []
    for i in range(1, n + 1):
        t, a, b, d = lines[i].split()
        if i < n:
            th.append(float(t))
        vp.append(float(a))
        vs.append(float(b))
        rho.append(float(d))
    print(f"[read_model] {n} layers (Vp: {min(vp):.1f}-{max(vp):.1f}, "
          f"Vs: {min(vs):.1f}-{max(vs):.1f} m/s)")
    return (np.array(vp, dtype=np.float64),
            np.array(vs, dtype=np.float64),
            np.array(rho, dtype=np.float64),
            np.array(th, dtype=np.float64))


def run_cli_hv(model_file: Path, *, nf=100, fmin=0.1, fmax=10.0, nmr=20, nml=20, prec=0.0001, nks=0):
    cmd = [
        str(HV_EXE),
        '-f', str(model_file),
        '-fmin', str(fmin),
        '-fmax', str(fmax),
        '-nf', str(nf),
        '-logsam',
        '-nmr', str(nmr),
        '-nml', str(nml),
        '-prec', str(prec),
        '-nks', str(nks),
        '-hv',
    ]
    res = subprocess.run(cmd, cwd=str(EXAMPLES_DIR), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f'CLI failed: {res.stderr}')
    arr = np.fromstring(res.stdout, sep=' ')
    if arr.size % 2 != 0:
        raise ValueError('Unexpected HV stdout format from CLI')
    pairs = arr.reshape(-1, 2)
    return pairs[:, 0], pairs[:, 1]


def compute_api_hv(vp, vs, rho, th, *, nf=100, fmin=0.1, fmax=10.0, nmr=20, nml=20, prec=0.1, nks=0):
    freq = np.logspace(np.log10(fmin), np.log10(fmax), nf)
    hv_vals, status = hv.hv(
        frequencies_hz=freq,
        vp=vp, vs=vs, rho=rho, thickness=th,
        n_rayleigh_modes=nmr, n_love_modes=nml, precision_percent=prec, nks=nks)
    return freq, hv_vals


# ── Model loading and benchmark config ───────────────────────────────────────

MODEL = EXAMPLES_DIR / 'models/model.txt'
assert MODEL.exists(), f'Model file not found: {MODEL}'

params = dict(nf=100, fmin=0.1, fmax=10.0, nmr=20, nml=20, prec=1, nks=0)

vp, vs, rho, th = read_model(MODEL)

print("\n" + "=" * 60)
print("[bench-part1] CLI vs API efficiency benchmark")
print("=" * 60)

print("[bench-part1] Warm-up run (CLI) ...")
_ = run_cli_hv(MODEL, **params)
print("[bench-part1] Warm-up run (API) ...")
_ = compute_api_hv(vp, vs, rho, th, **params)
print("[bench-part1] Warm-up complete.")

REPEATS = 5000
print(f"[bench-part1] Starting {REPEATS} repeats for each method...")

cli_times = []
api_times = []

print(f"[bench-part1] Timing CLI ({REPEATS} repeats) ...")
for rep in range(REPEATS):
    t0 = time.perf_counter()
    cli_f, cli_hv = run_cli_hv(MODEL, **params)
    cli_times.append(time.perf_counter() - t0)
    if (rep + 1) % 1000 == 0:
        print(f"[bench-part1]   CLI repeat {rep+1}/{REPEATS} done")

print(f"[bench-part1] Timing API ({REPEATS} repeats) ...")
for rep in range(REPEATS):
    t0 = time.perf_counter()
    api_f, api_hv = compute_api_hv(vp, vs, rho, th, **params)
    api_times.append(time.perf_counter() - t0)
    if (rep + 1) % 1000 == 0:
        print(f"[bench-part1]   API repeat {rep+1}/{REPEATS} done")

cli_mean, cli_std = stats.mean(cli_times), stats.pstdev(cli_times)
api_mean, api_std = stats.mean(api_times), stats.pstdev(api_times)
speedup = cli_mean / api_mean if api_mean > 0 else float('inf')

print(f"\n[bench-part1] Results:")
print(f"[bench-part1]   CLI mean +/- std (s): {cli_mean:.5f} +/- {cli_std:.5f}")
print(f"[bench-part1]   API mean +/- std (s): {api_mean:.5f} +/- {api_std:.5f}")
print(f"[bench-part1]   Speedup (CLI/API)   : {speedup:.2f}x")


# ── Plot HV curves + runtime bar chart ───────────────────────────────────────

print("\n[plot-part1] Generating HV comparison + runtime bar chart...")

fig, ax = plt.subplots(2, 1, figsize=(6, 8))

if not np.allclose(cli_f, api_f):
    print("[plot-part1] Frequency vectors differ — interpolating API onto CLI grid")
    api_hv_plot = np.interp(cli_f, api_f, api_hv)
    x = cli_f
else:
    api_hv_plot = api_hv
    x = api_f

ax[0].semilogx(cli_f, cli_hv, label='CLI', lw=2)
ax[0].semilogx(x, api_hv_plot, '--', label='API', lw=2)
ax[0].set_xlabel('Frequency (Hz)', fontsize=14)
ax[0].set_ylabel('H/V ratio', fontsize=14)
ax[0].grid(True, linestyle='dashed', alpha=0.3)
ax[0].legend(fontsize=12)
ax[0].set_title('HV curves', fontsize=14)

labels = ['CLI', 'API']
means = [cli_mean, api_mean]
errs = [cli_std, api_std]
bars = ax[1].bar(labels, means, yerr=errs, color=['C0', 'C1'], width=0.4, alpha=0.8, capsize=6)
ax[1].tick_params(axis='x', labelsize=14)
ax[1].set_ylabel('Runtime (s)', fontsize=14)
ax[1].set_title(f'Runtime comparison - Repeats: {REPEATS} \n (speedup ~ {speedup:.2f}x)', fontsize=14)
cli_patch = mpatches.Patch(color='C0', label='CLI mean')
api_patch = mpatches.Patch(color='C1', label='API mean')
err_proxy = Line2D([0], [0], color='k', marker='_', linestyle='None', markersize=10, label='std')
ax[1].legend(handles=[cli_patch, api_patch, err_proxy], loc='best', fontsize=12)
ax[1].grid(True, linestyle='dashed', axis='y', alpha=0.3)

plt.tight_layout()
print("[plot-part1] Displaying HV + runtime plot...")
plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: hvswdpy vs Disba dispersion benchmark
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("[bench-part2] hvswdpy vs Disba dispersion benchmark")
print("=" * 60)

from time import perf_counter
from statistics import median

try:
    from disba import PhaseDispersion
    print("[bench-part2] disba imported successfully")
except ModuleNotFoundError as e:
    raise ModuleNotFoundError("Install DISBA with `pip install disba`.") from e


# ── Read model for Part 2 ───────────────────────────────────────────────────

def read_model_p2(path: Path):
    print(f"[read_model] Reading: {path}")
    with open(path, 'r') as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    n = int(lines[0])
    vp, vs, rho, th = [], [], [], []
    for i in range(1, n + 1):
        t, a, b, d = lines[i].split()
        if i < n:
            th.append(float(t))
        vp.append(float(a))
        vs.append(float(b))
        rho.append(float(d))
    return (
        np.array(vp, dtype=float),
        np.array(vs, dtype=float),
        np.array(rho, dtype=float),
        np.array(th, dtype=float),
    )

VP, VS, RHO, TH = read_model_p2(EXAMPLES_DIR / 'model.txt')
print(f"[bench-part2] Loaded model with {VP.size} layers (including half-space)")

N_RAY_MODES = 1
N_LOVE_MODES = 1
PREC = 1  # percent

FMIN, FMAX = 0.5, 30.0
GRID_SIZES = [100, 400, 800, 1600, 3200]
BENCH_REPEATS = 5

print(f"[bench-part2] Frequency range  : {FMIN} - {FMAX} Hz")
print(f"[bench-part2] Grid sizes       : {GRID_SIZES}")
print(f"[bench-part2] Repeats per size  : {BENCH_REPEATS}")
print(f"[bench-part2] Rayleigh modes    : {N_RAY_MODES}, Love modes: {N_LOVE_MODES}")


# ── Timing functions ─────────────────────────────────────────────────────────

def time_hv_dispersion(freq):
    t0 = perf_counter()
    disp = hv.dispersion(
        frequencies_hz=freq,
        vp=VP, vs=VS, rho=RHO, thickness=TH,
        n_rayleigh_modes=N_RAY_MODES, n_love_modes=N_LOVE_MODES,
        precision_percent=PREC,
    )
    _ = disp.rayleigh_slowness, disp.love_slowness
    return perf_counter() - t0


th_km = np.append(TH, 0.0) / 1000.0
vp_kms = VP / 1000.0
vs_kms = VS / 1000.0
rho_gcm3 = RHO / 1000.0

pd_ray = PhaseDispersion(th_km, vp_kms, vs_kms, rho_gcm3, dc=0.005)
pd_lov = PhaseDispersion(th_km, vp_kms, vs_kms, rho_gcm3, dc=0.005)


def time_disba_dispersion(freq):
    per = (1.0 / freq)[::-1]
    t0 = perf_counter()
    _ = pd_ray(per, wave='rayleigh', mode=0).velocity
    _ = pd_lov(per, wave='love', mode=0).velocity
    return perf_counter() - t0


# ── Warm-up ──────────────────────────────────────────────────────────────────

print("[bench-part2] Warm-up (hvswdpy) ...")
freq_warm = np.logspace(np.log10(1.0), np.log10(10.0), 50)
_ = time_hv_dispersion(freq_warm)
print("[bench-part2] Warm-up (disba) ...")
_ = time_disba_dispersion(freq_warm)
print("[bench-part2] Warm-up done.\n")


# ── Benchmark loop ───────────────────────────────────────────────────────────

print("[bench-part2] Running benchmark loop...")
hv_times = []
disba_times = []
for nf in GRID_SIZES:
    freq = np.logspace(np.log10(FMIN), np.log10(FMAX), nf)
    hv_rep = [time_hv_dispersion(freq) for _ in range(BENCH_REPEATS)]
    disba_rep = [time_disba_dispersion(freq) for _ in range(BENCH_REPEATS)]
    hv_times.append(median(hv_rep))
    disba_times.append(median(disba_rep))
    print(f"[bench-part2]   nf={nf:5d}: hvswdpy={hv_times[-1]*1e3:8.2f} ms, "
          f"disba={disba_times[-1]*1e3:8.2f} ms")

hv_times = np.array(hv_times)
disba_times = np.array(disba_times)

print("[bench-part2] Benchmark complete.")


# ── Plot timing vs number of frequencies ─────────────────────────────────────

print("\n[plot-part2] Generating dispersion runtime comparison plot...")
plt.figure(figsize=(8, 6))
plt.plot(GRID_SIZES, hv_times * 1e3, 'o-', lw=2, label='hvswdpy')
plt.plot(GRID_SIZES, disba_times * 1e3, 's--', lw=2, label='Disba')
plt.xlabel('Number of frequency samples (nf)', fontsize=14)
plt.ylabel('Median runtime (ms)', fontsize=14)
plt.title('Dispersion runtime', fontsize=16)
plt.grid(True, linestyle='dashed', alpha=0.5)
plt.legend(ncol=1, fontsize=14, loc=2)
plt.tight_layout()
print("[plot-part2] Displaying timing plot...")
plt.show()

print("\n[done] All benchmarks complete.")
