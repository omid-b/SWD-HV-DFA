## HV-SWD-DFA: H/V Spectral Ratio and Surface Wave Dispersion Modeling (Diffuse Wavefield Assumption)

Fortran implementation of H/V spectral ratio and surface-wave dispersion, with a thin Python wrapper. The Python API mirrors the original CLI and offers simple functions.

- **Original authors**: HV‑INV project team (see headers in `HV.f90`)
- **Modifications and API**: Shihao Yuan (`shihao.yuan@univ-grenoble-alpes.fr`)

### DISCLAIMER
This is a development build. The code may contain errors or unstable functionality. Contributions and feedback are welcome.

---

### Repository layout

```
SWD-HV-DFA/
├── pyproject.toml            # Python project metadata & build-system config
├── meson.build               # Top-level Meson build file
├── meson_options.txt         # Meson build options (e.g. OpenMP toggle)
├── environment.yml           # Conda environment specification
├── README.md
├── LICENSE
├── src/
│   ├── cli/                  # Fortran CLI sources (hv_orig)
│   │   ├── HV.f90
│   │   ├── cli_args.f90
│   │   └── ...
│   └── hvswdpy/              # Python package (src layout)
│       ├── __init__.py
│       ├── hvswdpy.py
│       ├── meson.build
│       └── _fortran/         # Fortran sources & f2py interface
│           ├── modules.f90
│           ├── hvdfa.pyf
│           └── ...
└── tests/                    # Scripts, notebooks, and data
    ├── models/               # Layered earth model files
    │   ├── model.txt
    │   └── model2.txt
    ├── results/              # Output plots (git-ignored)
    ├── compare_API_CLI.*     # CLI vs Python API comparison
    ├── compare_disba_hvswdpy.*           # Dispersion: hvswdpy vs Disba
    └── compare_efficiency_disba_hvswdpy.*  # Runtime benchmarks
```

---

### Requirements

- **gfortran** — install via conda or your system package manager (see below)
- **Python ≥ 3.9** with NumPy ≥ 1.20 (tested with NumPy 2.x)
- **Meson ≥ 1.1** and **meson-python ≥ 0.16** (installed automatically by pip)
- macOS or Linux

---

### Build / Install

#### Option 1: Conda environment (recommended)

```bash
conda env create -f environment.yml
conda activate hvswdpy
```

This creates a complete environment with all dependencies, compiles the Fortran extension, and installs the `hv_orig` CLI — all in one step.

#### Option 2: pip install (from project root)

```bash
pip install .
```

Builds and installs everything: the `hvswdpy` Python package (with compiled Fortran extension), the `hv_orig` CLI executable, and all required dependencies (`numpy`, `matplotlib`, `disba`).

#### Option 3: Editable install (for development)

```bash
pip install --no-build-isolation --editable .
```

#### Prerequisites

Install gfortran before running any of the options above:

| Platform | Command |
|---|---|
| **Linux (conda)** | `conda install -c conda-forge gfortran_linux-64` |
| **macOS ARM (conda)** | `conda install -c conda-forge gfortran_osx-arm64` |
| **macOS Intel (conda)** | `conda install -c conda-forge gfortran_osx-64` |
| **Ubuntu / Debian** | `sudo apt-get install gfortran` |
| **Fedora** | `sudo dnf install gcc-gfortran` |

#### Build options

Disable OpenMP (if you encounter OpenMP-related build issues):

```bash
pip install . -Csetup-args=-Dopenmp=disabled
```

---

### Python API

```python
import numpy as np
import hvswdpy as hv

vp = np.array([300., 1500.])
vs = np.array([150., 800.])
rho = np.array([1800., 2200.])
thickness = np.array([20.])   # nlayers-1 values (halfspace excluded)
f = np.logspace(-1, 2, 100)

# H/V spectral ratio
hv_curve, status = hv.hv(
    frequencies_hz=f,
    vp=vp, vs=vs, rho=rho, thickness=thickness,
    n_rayleigh_modes=1, n_love_modes=0, precision_percent=1.0,
)

# H/V individual components
comps = hv.hv_components(f, vp, vs, rho, thickness)

# Dispersion curves (slowness → velocity via 1/slowness)
disp = hv.dispersion(
    frequencies_hz=f,
    vp=vp, vs=vs, rho=rho, thickness=thickness,
    n_rayleigh_modes=1, n_love_modes=0, precision_percent=1.0,
)
mask = (disp.rayleigh_valid[:, 0] != 0)
rayleigh_vel_mode0 = 1.0 / disp.rayleigh_slowness[mask, 0]
```

### Model format

- **API arrays**: `vp` (m/s), `vs` (m/s), `rho` (kg/m³), `thickness` (m) for all layers except the halfspace. At least 2 layers (including halfspace) so `thickness` has length `nlayers - 1`.
- **CLI model file** (`model.txt`):
  ```
  N_LAYERS
  THICKNESS  VP  VS  RHO     ← one line per layer, THICKNESS=0 for halfspace
  ```

---

### CLI usage

After installation, `hv_orig` is available on your PATH:

```bash
hv_orig -f tests/models/model.txt \
        -fmin 0.1 -fmax 100 -nf 100 -logsam \
        -nmr 3 -nml 3 -prec 1.0 -nks 0 \
        -ph -hv > HV.dat
```

Output files are written to the current working directory: `Rph.dat` (Rayleigh slowness), `Lph.dat` (Love slowness), and `HV.dat` (frequency, H/V ratio) via stdout redirection.

---

### Tests / Examples

All test scripts and notebooks live in `tests/`. Run them after installing the package:

| File | Description |
|---|---|
| `compare_API_CLI.py` / `.ipynb` | Compares H/V and dispersion output between the CLI and Python API |
| `compare_disba_hvswdpy.py` / `.ipynb` | Overlays Rayleigh and Love dispersion curves from hvswdpy and [Disba](https://github.com/keurfonluu/disba) |
| `compare_efficiency_disba_hvswdpy.py` / `.ipynb` | Benchmarks runtime: CLI vs API, and hvswdpy vs Disba |

```bash
cd tests
python compare_API_CLI.py
python compare_disba_hvswdpy.py
python compare_efficiency_disba_hvswdpy.py
```

Plots are saved to `tests/results/`.

---

### License

This project is licensed under the MIT License. See `LICENSE` for details.
