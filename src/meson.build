project('hvswdpy', 'c', 'fortran',
  version: '0.1.0',
  meson_version: '>=1.1.0',
  default_options: ['warning_level=1'],
)

py = import('python').find_installation(pure: false)

incdir_numpy = run_command(py,
  ['-c', 'import numpy; print(numpy.get_include())'],
  check: true,
).stdout().strip()

incdir_f2py = run_command(py,
  ['-c', 'import numpy.f2py; print(numpy.f2py.get_include())'],
  check: true,
).stdout().strip()

inc_np = include_directories(incdir_numpy, incdir_f2py)

fortranobject_c = incdir_f2py / 'fortranobject.c'

subdir('hvswdpy')
