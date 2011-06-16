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
        keywords="distributed objects, middleware, network communication, remote method call, IPC",
        url = "http://irmen.home.xs4all.nl/pyro4/",
        package_dir={'':'src'},
        packages=['Pyro4', 'Pyro4.socketserver', 'Pyro4.test'],
        scripts = [],
        platforms="any",
        classifiers=[
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
    )
    
    if len(sys.argv)>=2 and sys.argv[1].startswith("install"):
        print("\nOnly the Pyro library has been installed (version %s)." % Pyro4.constants.VERSION)
        print("If you want to install the tests, the examples, and/or the manual,")
        print("you have to copy them manually to the desired location.")
