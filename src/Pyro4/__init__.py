"""
Pyro package. Some generic init stuff to set up logging etc.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import sys

if sys.version_info < (2, 7):
    import warnings
    warnings.warn("This Pyro version is unsupported on Python versions older than 2.7", ImportWarning)


def _configLogging():
    """Do some basic config of the logging module at package import time.
    The configuring is done only if the PYRO_LOGLEVEL env var is set.
    If you want to use your own logging config, make sure you do
    that before any Pyro imports. Then Pyro will skip the autoconfig.
    Set the env var PYRO_LOGFILE to change the name of the autoconfigured
    log file (default is pyro.log in the current dir). Use '{stderr}' to
    make the log go to the standard error output."""
    import os
    import logging

    level = os.environ.get("PYRO_LOGLEVEL")
    logfilename = os.environ.get("PYRO_LOGFILE", "pyro.log")
    if logfilename == "{stderr}":
        logfilename = None
    if level not in (None, ""):
        levelvalue = getattr(logging, level)
        if len(logging.root.handlers) == 0:
            # configure the logging with some sensible defaults.
            try:
                import tempfile
                tempfile = tempfile.TemporaryFile(dir=".")
                tempfile.close()
            except OSError:
                # cannot write in current directory, use the default console logger
                logging.basicConfig(level=levelvalue)
            else:
                # set up a basic logfile in current directory
                logging.basicConfig(
                    level=levelvalue,
                    filename=logfilename,
                    datefmt="%Y-%m-%d %H:%M:%S",
                    format="[%(asctime)s.%(msecs)03d,%(name)s,%(levelname)s] %(message)s"
                )
            log = logging.getLogger("Pyro4")
            log.info("Pyro log configured using built-in defaults, level=%s", level)
    else:
        # PYRO_LOGLEVEL is not set, disable Pyro logging. No message is printed about this fact.
        log = logging.getLogger("Pyro4")
        log.setLevel(9999)


_configLogging()
del _configLogging

# initialize Pyro's configuration
from Pyro4.configuration import Configuration

config = Configuration()
del Configuration

# import the required Pyro symbols into this package
from Pyro4.core import URI, Proxy, Daemon, callback, batch, async, oneway, expose, current_context
from Pyro4.naming import locateNS, resolve
from Pyro4.futures import Future
from Pyro4.constants import VERSION as __version__
from Pyro4.serializers import get_serializer, get_serializer_by_id
