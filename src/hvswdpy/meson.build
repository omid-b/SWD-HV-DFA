f2py = find_program('f2py')

fortran_sources = files(
  '_fortran/modules.f90',
  '_fortran/aux_procedures.f90',
  '_fortran/dispersion_solver.f90',
  '_fortran/root_solver.f90',
  '_fortran/dispersion_equation.f90',
  '_fortran/greens_rayleigh.f90',
  '_fortran/greens_love.f90',
  '_fortran/rayleigh_mode.f90',
  '_fortran/love_mode.f90',
  '_fortran/bodywave_integrals.f90',
  '_fortran/hv_api.f90',
)

pyf_file = files('_fortran/hvdfa.pyf')

hvswdpy_wrappers = custom_target('HVSWDpy_wrappers',
  input: pyf_file,
  output: ['HVSWDpymodule.c', 'HVSWDpy-f2pywrappers2.f90'],
  command: [f2py, '@INPUT@', '--build-dir', '@OUTDIR@'],
)

fortran_args = ['-ffree-form', '-ffree-line-length-none']

omp_dep = dependency('openmp', language: 'fortran', required: get_option('openmp'))

ext_deps = [py.dependency()]
if omp_dep.found()
  ext_deps += omp_dep
endif

py.extension_module('HVSWDpy',
  hvswdpy_wrappers,
  fortran_sources,
  fortranobject_c,
  include_directories: inc_np,
  dependencies: ext_deps,
  fortran_args: fortran_args,
  install: true,
  subdir: 'hvswdpy',
)

py.install_sources(
  '__init__.py',
  'hvswdpy.py',
  subdir: 'hvswdpy',
)
