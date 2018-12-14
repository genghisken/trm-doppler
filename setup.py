import os, sys
from distutils.core import setup, Extension
import numpy

# Ensure C99 compilation to avoid a problem with the fftw_complex
# that can occur otherwise. 'c99' is apparently the standard way to
# do this (but is basically gcc with a flag)
#os.environ['CC'] = 'c99'

library_dirs = []
include_dirs = []

# need to direct to where includes and  libraries are
if 'TRM_SOFTWARE' in os.environ:
    library_dirs.append(os.path.join(os.environ['TRM_SOFTWARE'], 'lib'))
    include_dirs.append(os.path.join(os.environ['TRM_SOFTWARE'], 'include'))
else:
    print >>sys.stderr, \
        "Environment variable TRM_SOFTWARE pointing to location of shareable libraries and includes not defined!"

include_dirs.append(numpy.get_include())

doppler = Extension(
    'trm.doppler._doppler',
    define_macros = [('MAJOR_VERSION', '1'),('MINOR_VERSION', '0')],
    undef_macros = ['USE_NUMARRAY'],
    include_dirs = include_dirs,
    library_dirs = library_dirs,
    runtime_library_dirs = library_dirs,
    libraries = ['mem', 'fftw3', 'gomp', 'm'],
    extra_compile_args=['-fopenmp'],
    sources = [os.path.join('trm', 'doppler', 'doppler.cc')]
)

setup(name='trm.doppler',
      version='1.0',
      packages = ['trm', 'trm.doppler'],
      ext_modules=[doppler],
      scripts=['scripts/comdat.py',
               'scripts/comdef.py',
               'scripts/drlimit.py',
               'scripts/makedata.py',
               'scripts/makegrid.py',
               'scripts/makemap.py',
               'scripts/memit.py',
               'scripts/mol2dopp.py',
               'scripts/mspruit.py',
               'scripts/optscl.py',
               'scripts/precover.py',
               'scripts/psearch.py',
               'scripts/svdfit.py',
               'scripts/svd.py',
               'scripts/trtest.py',
               'scripts/vrend.py'],

      # metadata
      author='Tom Marsh',
      author_email='t.r.marsh@warwick.ac.uk',
      description="Python Doppler tomography module",
      url='http://www.astro.warwick.ac.uk/',
      long_description="""
doppler is an implementation of Doppler tomography package. It has many advantages over the
former set of F77 routines.
""",

      )

