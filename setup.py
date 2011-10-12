import sys
try:
    # try setuptools first, to get access to build_sphinx and test commands
    from setuptools import setup
    using_setuptools=True
except ImportError:
    from distutils.core import setup
    using_setuptools=False

if __name__ == '__main__' :
    sys.path.insert(0, "src")
    import Pyro4.constants
    print('Pyro version = %s' % Pyro4.constants.VERSION)

    setupargs={
        "name": "Pyro4",
        "version": Pyro4.constants.VERSION,
        "license": "MIT",
        "description": "distributed object middleware for Python (RPC)",
        "long_description": """Pyro means PYthon Remote Objects. 
It is a library that enables you to build applications in which
objects can talk to eachother over the network, with minimal programming effort.
You can just use normal Python method calls, with almost every possible parameter
and return value type, and Pyro takes care of locating the right object on the right
computer to execute the method. It is designed to be very easy to use, and to 
generally stay out of your way. But it also provides a set of powerful features that
enables you to build distributed applications rapidly and effortlessly.
Pyro is written in 100% pure Python and therefore runs on many platforms and Python versions,
including Python 2.x, Python 3.x, IronPython, Jython and Pypy.""",
        "author": "Irmen de Jong",
        "author_email": "irmen@razorvine.net",
        "keywords": "distributed objects, middleware, network communication, remote method call, IPC",
        "url": "http://irmen.home.xs4all.nl/pyro/",
        "package_dir": {'':'src'},
        "packages": ['Pyro4', 'Pyro4.socketserver', 'Pyro4.test', 'Pyro4.utils'],
        "scripts": [],
        "platforms": "any",
        "classifiers": [
                "Development Status :: 5 - Production/Stable",
                "Intended Audience :: Developers",
                "License :: OSI Approved :: MIT License",
                "Natural Language :: English",
                "Natural Language :: Dutch",
                "Operating System :: OS Independent",
                "Programming Language :: Python",
                "Programming Language :: Python :: 2.6",
                "Programming Language :: Python :: 2.7",
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.2",
                "Topic :: Software Development :: Object Brokering",
                "Topic :: System :: Distributed Computing",
                "Topic :: System :: Networking"
            ]
        }
        
    if using_setuptools:
        setupargs["test_suite"]="nose.collector"    # use Nose to run unittests
    
    setup(**setupargs)
    
    if len(sys.argv)>=2 and sys.argv[1].startswith("install"):
        print("\nOnly the Pyro library has been installed (version %s)." % Pyro4.constants.VERSION)
        print("If you want to install the tests, the examples, and/or the manual,")
        print("you have to copy them manually to the desired location.")
