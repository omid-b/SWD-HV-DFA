# Simple Makefile for HV-DFA
# Build targets:
#   make hv_orig       - original FORTRAN program 
#   make python        - Python wrapper (editable install via meson-python)
#   make all           - both
#   make clean         - remove build artifacts

FC=gfortran
OPT ?= -O2
USE_OPENMP ?= 1

MODDIR = hvswdpy/_fortran
BINDIR = ../bin

ifeq ($(USE_OPENMP),1)
  OMPFLAG = -fopenmp
else
  OMPFLAG =
endif

FFLAGS ?= $(OPT) $(OMPFLAG) -J$(MODDIR)
LDFLAGS ?= $(OMPFLAG)

# Python wrapper configuration
PYTHON ?= python3

.PHONY: all clean python hv_orig

# Ensure BINDIR exists
$(BINDIR):
	mkdir -p $(BINDIR)

# Build both targets
all: hv_orig python

# Original FORTRAN CLI: sources are under src/cli/, includes modules from hvswdpy/_fortran
hv_orig: cli/HV.f90 | $(BINDIR)
	$(FC) $(FFLAGS) -ffree-form -I$(MODDIR) $< -o $(BINDIR)/hv_orig $(LDFLAGS)

# Python wrapper: editable install via meson-python
python:
	$(PYTHON) -m pip install --no-build-isolation --editable .

clean:
	rm -f *.o *.mod $(BINDIR)/hv_orig
	rm -rf build/ ../build/ builddir/
	rm -f hvswdpy/_fortran/HVSWDpy-f2pywrappers2.f90 hvswdpy/_fortran/HVSWDpymodule.c
	rm -f hvswdpy/HVSWDpy*.so hvswdpy/HVSWDpy*.cpython-*.so
	rm -f HVSWDpy*.so HVSWDpy-f2pywrappers2.f90 HVSWDpymodule.c
	rm -f HVSWDpy*.cpython-*.so
