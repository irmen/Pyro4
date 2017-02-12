"""
Platform specific utilities.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""


def fixIronPythonExceptionForPickle(exceptionObject, addAttributes):
    """
    Function to hack around a bug in IronPython where it doesn't pickle
    exception attributes. We piggyback them into the exception's args.
    Bug report is at https://github.com/IronLanguages/main/issues/943
    Bug is still present in Ironpython 2.7.7
    """
    if hasattr(exceptionObject, "args"):
        if addAttributes:
            # piggyback the attributes on the exception args instead.
            ironpythonArgs = vars(exceptionObject)
            ironpythonArgs["__ironpythonargs__"] = True
            exceptionObject.args += (ironpythonArgs,)
        else:
            # check if there is a piggybacked object in the args
            # if there is, extract the exception attributes from it.
            if len(exceptionObject.args) > 0:
                piggyback = exceptionObject.args[-1]
                if type(piggyback) is dict and piggyback.get("__ironpythonargs__"):
                    del piggyback["__ironpythonargs__"]
                    exceptionObject.args = exceptionObject.args[:-1]
                    exceptionObject.__dict__.update(piggyback)
