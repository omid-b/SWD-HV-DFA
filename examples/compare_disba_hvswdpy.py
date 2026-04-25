#!/usr/bin/env python3
"""
Compare dispersion curves: hvswdpy vs Disba

Computes Rayleigh and Love phase-velocity dispersion curves using both
hvswdpy and Disba, then overlays the results for visual comparison.

Uses the layered model in examples/models/model.txt.
"""

# ── Setup and imports ────────────────────────────────────────────────────────

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches

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

try:
    from disba import PhaseDispersion
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "Disba is not installed. Install with `pip install disba` in your environment."
    ) from e

print(f"[setup] Script directory : {SCRIPT_DIR}")
print(f"[setup] hvswdpy imported from: {hv.__file__}")
print("[setup] disba imported successfully")


# ── Load model ───────────────────────────────────────────────────────────────

def read_model(path: Path):
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

model_file = SCRIPT_DIR / 'models/model.txt'
VP, VS, RHO, TH = read_model(model_file)

print("[read_model] Model layers:")
for i in range(VP.size):
    lay = 'layer' if i < VP.size - 1 else 'half-space'
    t = TH[i] if i < TH.size else 0.0
    print(f"  {i+1} ({lay}): th={t} m, vp={VP[i]} m/s, vs={VS[i]} m/s, rho={RHO[i]} kg/m^3")


# ── Configuration ────────────────────────────────────────────────────────────

NF = 80
FMIN, FMAX = 0.5, 40.0
FREQ = np.logspace(np.log10(FMIN), np.log10(FMAX), NF)
PERIOD = 1.0 / FREQ

N_RAY_MODES = 5
N_LOVE_MODES = 5
PREC = 0.1

print(f"\n[config] Frequency range: {FMIN} - {FMAX} Hz ({NF} log-spaced points)")
print(f"[config] Rayleigh modes: {N_RAY_MODES}, Love modes: {N_LOVE_MODES}, precision: {PREC}%")


# ── Compute dispersion with hvswdpy ─────────────────────────────────────────

print("\n" + "=" * 60)
print("[hvswdpy] Computing dispersion...")
print("=" * 60)

disp = hv.dispersion(
    frequencies_hz=FREQ,
    vp=VP, vs=VS, rho=RHO, thickness=TH,
    n_rayleigh_modes=N_RAY_MODES, n_love_modes=N_LOVE_MODES, precision_percent=PREC,
)

ray_sl = disp.rayleigh_slowness
ray_va = disp.rayleigh_valid
lov_sl = disp.love_slowness
lov_va = disp.love_valid

ray_vel_hv = np.full_like(ray_sl, np.nan, dtype=float)
lov_vel_hv = np.full_like(lov_sl, np.nan, dtype=float)
np.divide(1.0, ray_sl, out=ray_vel_hv, where=(ray_sl > 0))
np.divide(1.0, lov_sl, out=lov_vel_hv, where=(lov_sl > 0))

print(f"[hvswdpy] Rayleigh valid points: {int(np.sum(ray_va != 0))}")
print(f"[hvswdpy] Love valid points    : {int(np.sum(lov_va != 0))}")


# ── Compute dispersion with Disba ───────────────────────────────────────────

print("\n" + "=" * 60)
print("[disba] Computing dispersion...")
print("=" * 60)

th_km = np.append(TH, 0.0) / 1000.0
vp_kms = VP / 1000.0
vs_kms = VS / 1000.0
rho_gcm3 = RHO / 1000.0

pd_ray = PhaseDispersion(th_km, vp_kms, vs_kms, rho_gcm3, dc=0.001)
pd_lov = PhaseDispersion(th_km, vp_kms, vs_kms, rho_gcm3, dc=0.001)

PER_ASC = PERIOD[::-1]
N_PER = PER_ASC.size


def compute_mode_velocity(pd_obj, wave, mode):
    try:
        res = pd_obj(PER_ASC, wave=wave, mode=mode)
    except Exception as e:
        print(f"[disba]   WARNING: {wave} mode {mode} failed ({e})")
        return np.full(N_PER, np.nan, dtype=float)
    vel = np.asarray(res.velocity).ravel()
    if hasattr(res, 'period'):
        p_ret = np.asarray(res.period).ravel()
    else:
        p_ret = PER_ASC
    full = np.full(N_PER, np.nan, dtype=float)
    key_grid = np.round(PER_ASC, 12)
    key_ret = np.round(p_ret, 12)
    index_by_period = {val: idx for idx, val in enumerate(key_grid)}
    for j, pr in enumerate(key_ret):
        idx = index_by_period.get(pr)
        if idx is not None and j < vel.size:
            full[idx] = vel[j]
    return full


ray_vel_disba = []
for m in range(N_RAY_MODES):
    full = compute_mode_velocity(pd_ray, 'rayleigh', m)
    ray_vel_disba.append(full[::-1])
    n_valid = int(np.sum(~np.isnan(full)))
    print(f"[disba]   Rayleigh mode {m}: {n_valid} valid points")
ray_vel_disba = np.stack(ray_vel_disba, axis=1)

lov_vel_disba = []
for m in range(N_LOVE_MODES):
    full = compute_mode_velocity(pd_lov, 'love', m)
    lov_vel_disba.append(full[::-1])
    n_valid = int(np.sum(~np.isnan(full)))
    print(f"[disba]   Love mode {m}: {n_valid} valid points")
lov_vel_disba = np.stack(lov_vel_disba, axis=1)

print("[disba] Dispersion computed.")


# ── Comparison plots ─────────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("[plot] Generating comparison plots...")
print("=" * 60)

colors = [f"C{i}" for i in range(max(N_RAY_MODES, N_LOVE_MODES))]

def _build_legend(ax, n_modes, colors):
    """Custom legend: one colored entry per mode + style key for solver."""
    handles = []
    handles.append(Line2D([], [], color='black', linestyle='-', lw=2, label='Disba'))
    handles.append(Line2D([], [], color='black', marker='o', linestyle='None',
                          markerfacecolor='black', markersize=6, label='hvswdpy'))
    for m in range(n_modes):
        handles.append(mpatches.Patch(color=colors[m % len(colors)], label=f'Mode {m}'))
    ax.legend(handles=handles, fontsize=11, loc='best', ncol=1)


# Rayleigh — overlay: Disba = solid lines, hvswdpy = scatter
fig, ax = plt.subplots(figsize=(10, 6))
n_ray_plot = min(N_RAY_MODES, ray_vel_disba.shape[1])
for m in range(n_ray_plot):
    disba_valid = ~np.isnan(ray_vel_disba[:, m])
    ax.plot(FREQ[disba_valid], ray_vel_disba[disba_valid, m] * 1000.0, '-', lw=2,
            color=colors[m % len(colors)], zorder=2)
for m in range(n_ray_plot):
    mask = (ray_va[:, m] != 0)
    if np.any(mask):
        ax.scatter(FREQ[mask], ray_vel_hv[mask, m], marker='o', s=60,
                   color=colors[m % len(colors)], zorder=3)
    disba_valid = ~np.isnan(ray_vel_disba[:, m])
    print(f"[plot]   Rayleigh mode {m}: hvswdpy={int(mask.sum())} pts, "
          f"disba={int(disba_valid.sum())} pts")
ax.set_xscale('log')
ax.set_xlabel('Frequency (Hz)', fontsize=14)
ax.set_ylabel('Phase velocity (m/s)', fontsize=14)
ax.set_title('Rayleigh wave dispersion: Disba (lines) vs hvswdpy (circles)', fontsize=16)
ax.grid(True, linestyle='dashed', alpha=0.5)
_build_legend(ax, n_ray_plot, colors)
plt.tight_layout()
print("[plot] Displaying Rayleigh comparison...")
plt.show()

# Love — overlay: Disba = solid lines, hvswdpy = scatter
fig, ax = plt.subplots(figsize=(10, 6))
n_lov_plot = min(N_LOVE_MODES, lov_vel_disba.shape[1])
for m in range(n_lov_plot):
    disba_valid = ~np.isnan(lov_vel_disba[:, m])
    ax.plot(FREQ[disba_valid], lov_vel_disba[disba_valid, m] * 1000.0, '-', lw=2,
            color=colors[m % len(colors)], zorder=2)
for m in range(n_lov_plot):
    mask = (lov_va[:, m] != 0)
    if np.any(mask):
        ax.scatter(FREQ[mask], lov_vel_hv[mask, m], marker='o', s=60,
                   color=colors[m % len(colors)], zorder=3)
    disba_valid = ~np.isnan(lov_vel_disba[:, m])
    print(f"[plot]   Love mode {m}: hvswdpy={int(mask.sum())} pts, "
          f"disba={int(disba_valid.sum())} pts")
ax.set_xscale('log')
ax.set_xlabel('Frequency (Hz)', fontsize=14)
ax.set_ylabel('Phase velocity (m/s)', fontsize=14)
ax.set_title('Love wave dispersion: Disba (lines) vs hvswdpy (dots)', fontsize=16)
ax.grid(True, linestyle='dashed', alpha=0.5)
_build_legend(ax, n_lov_plot, colors)
plt.tight_layout()
print("[plot] Displaying Love comparison...")
plt.show()

print("\n[done] All comparisons complete.")
