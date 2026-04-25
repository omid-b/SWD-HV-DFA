#!/usr/bin/env python3
"""
CLI vs Python API Comparison

Compares the output of the original Fortran CLI (hv_orig) and the Python API
(hvswdpy) for computing H/V spectral ratios and dispersion curves.

Steps:
  - Read the layered model from models/model.txt
  - Run the CLI to generate HV and dispersion data
  - Use the Python API to compute the same quantities
  - Compare and visualize the results
  - Save comparison plots to the results/ directory
"""

# ── Setup and imports ────────────────────────────────────────────────────────
import os
import sys
import shutil
import subprocess
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

try:
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    SCRIPT_DIR = Path.cwd().resolve()
ROOT = SCRIPT_DIR.parent

try:
    import hvswdpy as hv
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT / 'src'))
    import hvswdpy as hv

print(f"[setup] Working directory : {SCRIPT_DIR}")
print(f"[setup] Root directory    : {ROOT}")
print(f"[setup] hvswdpy imported from: {hv.__file__}")


# ── Helper Functions ─────────────────────────────────────────────────────────

def read_model(path):
    print(f"[read_model] Reading model file: {path}")
    with open(path, 'r') as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    n = int(lines[0])
    vp = []
    vs = []
    rho = []
    th = []
    for i in range(1, n + 1):
        t, a, b, d = lines[i].split()
        if i < n:
            th.append(float(t))
        vp.append(float(a))
        vs.append(float(b))
        rho.append(float(d))
    print(f"[read_model] Parsed {n} layers (Vp range: {min(vp):.1f}-{max(vp):.1f} m/s, "
          f"Vs range: {min(vs):.1f}-{max(vs):.1f} m/s)")
    return (np.array(vp, dtype=np.float64),
            np.array(vs, dtype=np.float64),
            np.array(rho, dtype=np.float64),
            np.array(th, dtype=np.float64))


def run_cli(model_file, nf=100, fmin=0.1, fmax=100.0, nmr=3, nml=3, prec=1.0, nks=0):
    hv_orig = shutil.which('hv_orig')
    if not hv_orig:
        raise FileNotFoundError(
            'hv_orig not found on PATH. '
            'Install the package first: pip install . (from the project root)'
        )
    cmd = [
        hv_orig,
        '-f', str(model_file),
        '-fmin', str(fmin),
        '-fmax', str(fmax),
        '-nf', str(nf),
        '-logsam',
        '-nmr', str(nmr),
        '-nml', str(nml),
        '-prec', str(prec),
        '-nks', str(nks),
        '-ph',
        '-hv',
    ]
    print(f"[run_cli] Executing: {' '.join(cmd)}")
    with open(SCRIPT_DIR / 'HV.dat', 'w') as hv_out:
        res = subprocess.run(cmd, cwd=str(SCRIPT_DIR), stdout=hv_out, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"CLI failed (exit code {res.returncode}): {res.stderr}")
    if not (SCRIPT_DIR / 'Rph.dat').exists():
        raise FileNotFoundError('Rph.dat was not created')
    if not (SCRIPT_DIR / 'HV.dat').exists():
        raise FileNotFoundError('HV.dat was not created (stdout redirection)')
    print(f"[run_cli] CLI finished successfully (return code 0)")


def read_cli_hv(path=None):
    if path is None:
        path = SCRIPT_DIR / 'HV.dat'
    print(f"[read_cli_hv] Reading HV data from: {path}")
    arr = np.fromstring(open(path, 'r').read(), sep=' ')
    if arr.size % 2 != 0:
        raise ValueError('Unexpected HV.dat format')
    pairs = arr.reshape(-1, 2)
    print(f"[read_cli_hv] Loaded {pairs.shape[0]} frequency-HV pairs")
    return pairs[:, 0], pairs[:, 1]


def read_cli_dispersion(path):
    print(f"[read_cli_dispersion] Reading dispersion file: {path}")
    with open(path, 'r') as f:
        content = f.read().strip().split()
    nf = int(content[0]); nm = int(content[1])
    sl = np.array(list(map(float, content[2:2 + nf * nm])))
    flags_raw = content[2 + nf * nm: 2 + nf * nm + nf * nm]
    valid = np.array([tok == 'T' for tok in flags_raw])
    sl = sl.reshape(nm, nf)
    valid = valid.reshape(nm, nf)
    print(f"[read_cli_dispersion] {nm} modes x {nf} frequencies")
    return sl, valid


# ── Configuration and Model Loading ─────────────────────────────────────────

model_file = SCRIPT_DIR / 'models/model.txt'
nf = 100
fmin, fmax = 0.1, 50.0
nmr, nml = 5, 5
prec = 0.1
nks = 0

results_dir = SCRIPT_DIR / 'results'
results_dir.mkdir(parents=True, exist_ok=True)
print(f"[config] Results directory: {results_dir}")

vp, vs, rho, th = read_model(model_file)
print(f"[config] Model loaded: {len(vp)} layers")
print(f"[config] Frequency range: {fmin} - {fmax} Hz ({nf} log-spaced points)")
print(f"[config] Rayleigh modes: {nmr}, Love modes: {nml}, precision: {prec}%")

freq = np.logspace(np.log10(fmin), np.log10(fmax), nf)


# ── Run CLI Computation ─────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("[cli] Running CLI computation...")
print("=" * 60)
run_cli(model_file, nf=nf, fmin=fmin, fmax=fmax, nmr=nmr, nml=nml, prec=prec, nks=nks)

f_cli, hv_cli = read_cli_hv(SCRIPT_DIR / 'HV.dat')
r_sl_cli, r_va_cli = read_cli_dispersion(SCRIPT_DIR / 'Rph.dat')

l_sl_cli, l_va_cli = (None, None)
if (SCRIPT_DIR / 'Lph.dat').exists():
    l_sl_cli, l_va_cli = read_cli_dispersion(SCRIPT_DIR / 'Lph.dat')
    print("[cli] Love wave data found")
else:
    print("[cli] No Love wave data file (Lph.dat)")

print(f"[cli] HV data: {len(f_cli)} frequency points")
print(f"[cli] Rayleigh data: {r_sl_cli.shape[0]} modes, {r_sl_cli.shape[1]} frequencies")


# ── Run Python API Computation ───────────────────────────────────────────────

print("\n" + "=" * 60)
print("[api] Running Python API computation...")
print("=" * 60)

print("[api] Computing HV via hv.hv() ...")
hv_py, status_hv = hv.hv(
    frequencies_hz=freq,
    vp=vp, vs=vs, rho=rho, thickness=th,
    n_rayleigh_modes=nmr, n_love_modes=nml, precision_percent=prec, nks=nks)
print(f"[api] HV computation status: {status_hv}")

print("[api] Computing dispersion via hv.dispersion() ...")
disp = hv.dispersion(
    frequencies_hz=freq,
    vp=vp, vs=vs, rho=rho, thickness=th,
    n_rayleigh_modes=nmr, n_love_modes=nml, precision_percent=prec)

r_sl_py = disp.rayleigh_slowness
r_va_py = disp.rayleigh_valid
l_sl_py = disp.love_slowness
l_va_py = disp.love_valid
status_dp = disp.status
print(f"[api] Dispersion status: {status_dp}")

print(f"[api] HV data: {len(hv_py)} frequency points")
print(f"[api] Rayleigh data: {r_sl_py.shape[1]} modes, {r_sl_py.shape[0]} frequencies")
print(f"[api] Love data: {l_sl_py.shape[1]} modes, {l_sl_py.shape[0]} frequencies")


# ── Plot H/V Comparison ─────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("[plot] Generating H/V comparison plot...")
print("=" * 60)

if not np.allclose(f_cli, freq):
    print("[plot] Frequency vectors differ — interpolating API data onto CLI grid")
    hv_py_plot = np.interp(f_cli, freq, hv_py)
    f_plot = f_cli
else:
    hv_py_plot = hv_py
    f_plot = freq

plt.figure(figsize=(9, 6))
plt.semilogx(f_cli, hv_cli, 'k-', lw=2, label='CLI HV')
plt.semilogx(f_plot, hv_py_plot, 'r--', lw=2, label='API HV')
plt.xlabel('Frequency (Hz)', fontsize=14)
plt.ylabel('H/V ratio', fontsize=14)
plt.grid(True, linestyle='--', alpha=0.3)
plt.legend(fontsize=14)
plt.title('H/V Comparison (CLI vs API)', fontsize=16)
plt.tight_layout()

hv_png = results_dir / 'compare_hv.png'
plt.savefig(str(hv_png), dpi=300)
print(f"[plot] Saved HV plot: {hv_png}")
plt.show()


# ── Plot Rayleigh Dispersion Comparison ──────────────────────────────────────

print("\n" + "=" * 60)
print("[plot] Generating Rayleigh dispersion comparison plot...")
print("=" * 60)

fig, ax = plt.subplots(1, 1, figsize=(10, 6))

colors = ['C0', 'C1', 'C2', 'C3', 'C4']
nm_ray = r_sl_cli.shape[0]

for im in range(nm_ray):
    mask = r_va_cli[im]
    vel_cli = 1.0 / r_sl_cli[im, mask]
    ax.plot(f_cli[mask], vel_cli, color=colors[im % len(colors)],
            linewidth=2, alpha=0.8, label=f'CLI M{im+1}' if im < 5 else "")
    print(f"[plot]   CLI Rayleigh mode {im+1}: {mask.sum()} valid points")

nm_ray_py = r_sl_py.shape[1]
for im in range(nm_ray_py):
    mask = (r_va_py[:, im] != 0)
    vel_py = 1.0 / r_sl_py[mask, im]
    ax.scatter(freq[mask], vel_py, s=25, color=colors[im % len(colors)],
               marker='o', alpha=0.9, edgecolors='black', linewidth=0.5,
               label=f'API M{im+1}' if im < 5 else "")
    print(f"[plot]   API Rayleigh mode {im+1}: {mask.sum()} valid points")

ax.set_xscale('log')
ax.set_xlabel('Frequency (Hz)', fontsize=14)
ax.set_ylabel('Phase velocity (m/s)', fontsize=14)
ax.set_title('Rayleigh Wave Dispersion: CLI (lines) vs API (dots)', fontsize=16)
ax.grid(True, linestyle='--', alpha=0.3)

handles, labels = ax.get_legend_handles_labels()
if handles:
    ax.legend(handles[:10], labels[:10], title='Modes', fontsize=14, ncol=2)

plt.tight_layout()
ray_png = results_dir / 'compare_rayleigh_dispersion.png'
plt.savefig(str(ray_png), dpi=300)
print(f"[plot] Saved Rayleigh dispersion plot: {ray_png}")
plt.show()


# ── Plot Love Dispersion Comparison ──────────────────────────────────────────

print("\n" + "=" * 60)
print("[plot] Generating Love dispersion comparison plot...")
print("=" * 60)

if l_sl_cli is not None:
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    nm_lov = l_sl_cli.shape[0]
    for im in range(nm_lov):
        mask = l_va_cli[im]
        vel_cli = 1.0 / l_sl_cli[im, mask]
        ax.plot(f_cli[mask], vel_cli, color=colors[im % len(colors)],
                linewidth=2, alpha=0.8, label=f'CLI M{im+1}' if im < 5 else "")
        print(f"[plot]   CLI Love mode {im+1}: {mask.sum()} valid points")

    nm_lov_py = l_sl_py.shape[1]
    for im in range(nm_lov_py):
        mask = (l_va_py[:, im] != 0)
        vel_py = 1.0 / l_sl_py[mask, im]
        ax.scatter(freq[mask], vel_py, s=25, color=colors[im % len(colors)],
                   marker='o', alpha=0.9, edgecolors='black', linewidth=0.5,
                   label=f'API M{im+1}' if im < 5 else "")
        print(f"[plot]   API Love mode {im+1}: {mask.sum()} valid points")

    ax.set_xscale('log')
    ax.set_xlabel('Frequency (Hz)', fontsize=14)
    ax.set_ylabel('Phase velocity (m/s)', fontsize=14)
    ax.set_title('Love Wave Dispersion: CLI (lines) vs API (dots)', fontsize=16)
    ax.grid(True, linestyle='--', alpha=0.3)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles[:10], labels[:10], title='Modes', fontsize=14, ncol=2)

    plt.tight_layout()
    lov_png = results_dir / 'compare_love_dispersion.png'
    plt.savefig(str(lov_png), dpi=150)
    print(f"[plot] Saved Love dispersion plot: {lov_png}")
    plt.show()
else:
    print("[plot] No Love wave data available — skipping Love dispersion plot")
    lov_png = None

print("\n[done] All comparisons complete.")
