"""Get testlib.h source code"""

import pathlib

here = pathlib.Path(__file__).parent.resolve()
testlib_dir = here / 'testlib.h'

__all__ = ['testlib_dir']
