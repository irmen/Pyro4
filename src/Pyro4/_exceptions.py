"""

The exceptions module was removed from Python 2 to Python 3.
Here is the Python 3 version of the exceptions module.



"""

classes = set()

def add(cls):
    if cls in classes or cls.__module__ != Exception.__module__:
        return
    # tribute to
    #   http://stackoverflow.com/questions/436159/how-to-get-all-subclasses
    for cls in cls.__subclasses__():
        add(cls)
    globals()[cls.__name__] = cls
    classes.add(cls)

add(BaseException)
