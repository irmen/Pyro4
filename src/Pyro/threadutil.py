"""
Threading abstraction which allows for threading2 use with a
transparent fallback to threading when not available.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

import Pyro.config

if Pyro.config.THREADING2:
    try:
        from threading2 import *
    except ImportError:
        from threading import *
else:    
    from threading import *
