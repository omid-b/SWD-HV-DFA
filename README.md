## HV-SWD-DFA: H/V Spectral Ratio and Surface Wave Dispersion Modeling (Diffuse Wavefield Assumption)

Fortran implementation of H/V spectral ratio and surface-wave dispersion, with a thin Python wrapper. The Python API mirrors the original CLI and offers simple functions.

- **Original authors**: HV‑INV project team (see headers in `HV.f90`)
- **Modifications and API**: Shihao Yuan (`syuan@mines.edu`)

### DISCLAIMER:
This is a development build. The code may contain errors or unstable functionality. Contributions and feedback are welcome.

### Repository layout
```
SWD-HV-DFA/
├── pyproject.toml          # Python project metadata & build-system config
├── meson.build             # Top-level Meson build file
├── meson_options.txt       # Meson build options (e.g. OpenMP toggle)
├── environment.yml         # Conda environment specification
├── README.md
├── LICENSE
├── src/
│   ├── cli/                # Fortran CLI sources (hv_orig)
│   │   ├── HV.f90
│   │   ├── cli_args.f90
│   │   └── ...
│   └── hvswdpy/            # Python package (src layout)
│       ├── __init__.py
│       ├── hvswdpy.py
│       ├── meson.build
│       └── _fortran/       # Fortran sources & f2py interface
│           ├── modules.f90
│           ├── hvdfa.pyf
│           └── ...
└── examples/               # Scripts, notebooks, and data
    ├── models/
    └── results/
```

### Requirements
- gfortran (install via conda: `conda install -c conda-forge gfortran_linux-64` for Linux or `gfortran_osx-arm64`/`gfortran_osx-64` for macOS)
- Python 3.9+ with NumPy 1.20+ or NumPy 2.x (tested with NumPy 1.25.2 and 2.2.6)
- macOS/Linux (tested on macOS ARM with Conda)

### Build / Install

#### Option 1: Conda environment (recommended)
```bash
conda env create -f environment.yml
conda activate hvswdpy
```
This creates a complete environment, installs all dependencies, compiles the Fortran extension and the `hv_orig` CLI binary.

#### Option 2: pip install (from project root)
```bash
pip install .
```
This builds both the Python extension module and the `hv_orig` CLI executable, and installs all required dependencies (`numpy`, `matplotlib`, `disba`).

#### Option 3: Editable install (for development)
```bash
pip install --no-build-isolation --editable .
```

#### Prerequisites
1. Install gfortran:
   - **Linux**: `conda install -c conda-forge gfortran_linux-64`
   - **macOS (ARM)**: `conda install -c conda-forge gfortran_osx-arm64`
   - **macOS (Intel)**: `conda install -c conda-forge gfortran_osx-64`
   - Or use your system package manager (e.g., `apt-get install gfortran` on Ubuntu/Debian)

2. Activate your conda environment (if using conda):
   ```bash
   conda activate your_environment
   ```

#### Build Options

You can customize the build behavior using Meson options:

- **Disable OpenMP** (if you encounter OpenMP-related issues):
  ```bash
  pip install . -Csetup-args=-Dopenmp=disabled
  ```

### Model format (API)
- API arrays:
  - `vp` (m/s), `vs` (m/s), `rho` (kg/m³), `thickness` (m) for all layers except halfspace
  - At least 2 layers (including halfspace) so `thickness` has length `nlayers-1`
- CLI `model.txt` (used by examples):
  - First line: `N_LAYERS`
  - Next lines: `THICKNESS VP VS RHO`, with `THICKNESS=0` for the halfspace

### Original CLI usage
```bash
hv_orig -f examples/models/model.txt -fmin 0.1 -fmax 100 -nf 100 -logsam -nmr 3 -nml 3 -prec 1.0 -nks 0 -ph -hv > examples/HV.dat
# Outputs in examples/: Rph.dat (Rayleigh slowness), Lph.dat (Love slowness), HV.dat (freq, hv)
```

### Python API
  ```python
  import numpy as np
  import hvswdpy as hv
  vp = np.array([300., 1500.])
  vs = np.array([150., 800.])
  rho = np.array([1800., 2200.])
  thickness = np.array([20.])  # nlayers-1 values (halfspace excluded)
  f = np.logspace(-1, 2, 100)

  # H/V spectral ratio
  hv_curve, status = hv.hv(
      frequencies_hz=f,
      vp=vp, vs=vs, rho=rho, thickness=thickness,
      n_rayleigh_modes=1, n_love_modes=0, precision_percent=1.0,
  )
  ```
- Components
  ```python
  comps = hv.hv_components(f, vp, vs, rho, thickness)
  ```
- Dispersion (convert slowness to velocity via 1/slowness)
  ```python
  disp = hv.dispersion(
      frequencies_hz=f,
      vp=vp, vs=vs, rho=rho, thickness=thickness,
      n_rayleigh_modes=1, n_love_modes=0, precision_percent=1.0,
  )
  mask = (disp.rayleigh_valid[:, 0] != 0)
  rayleigh_vel_mode1 = 1.0 / disp.rayleigh_slowness[mask, 0]
  ```

### Examples
- Compare HV and dispersion (CLI vs API) — generates plots into `examples/results/`:
  ```bash
  jupyter notebook examples/compare_API_CLI.ipynb
  ```
  - `examples/results/compare_hv.png`
  - `examples/results/compare_rayleigh_dispersion.png` (phase velocity vs frequency)
  - `examples/results/compare_love_dispersion.png` (if Love modes requested)


### License
This project is licensed under the MIT License. See `LICENSE` for details.
