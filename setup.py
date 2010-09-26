from distutils.core import setup
import sys

if __name__ == '__main__' :
    sys.path.insert(0, "src")
    import Pyro4.constants
    print('Pyro version = %s' % Pyro4.constants.VERSION)

    setup(name="Pyro4",
        version= Pyro4.constants.VERSION,
        license="MIT",
        description = "distributed object middleware for Python (RPC)",
        long_description = """Pyro stands for PYthon Remote Objects. It is an advanced and powerful Distributed Object Technology system written entirely in Python, that is designed to be fast and very easy to use.""",
        author = "Irmen de Jong",
        author_email="irmen@razorvine.net",
        keywords="distributed objects, middleware, network communication, RMI, IPC, DOT",
        url = "http://www.razorvine.net/python/Pyro",
        download_url="http://www.xs4all.nl/~irmen/pyro4/download/",
        package_dir={'':'src'},
        packages=['Pyro4', 'Pyro4.socketserver'],
        scripts = [],
        platforms="any",
        classifiers=[
                "Development Status :: 4 - Beta",
                "Intended Audience :: Developers",
                "License :: OSI Approved :: MIT License",
                "Operating System :: OS Independent",
                "Programming Language :: Python",
                "Topic :: Software Development :: Object Brokering",
                "Topic :: System :: Distributed Computing",
                "Topic :: System :: Networking"
            ]
    )
    
    if len(sys.argv)>=2 and sys.argv[1].startswith("install"):
        print("\nOnly the Pyro library has been installed (version %s)." % Pyro4.constants.VERSION)
        print("If you want to install the tests, the examples, and/or the manual,")
        print("you have to copy them manually to the desired location.")
