This test is to show PYRO's remote exception capabilities.
The remote object contains various member functions which raise
various kinds of exceptions. The client will print those.

Note the special handling of the Pyro exception. 
It is possible to extract and print the *remote* traceback.
You can then see where in the code on the remote side the error occured!
By installing Pyro's excepthook (Pyro4.util.excepthook) you can even
see the remote traceback when you're not catching any exceptions.

Also try to set PYRO_DETAILED_TRACEBACK to True (on the server)
to get a very detailed traceback in your client. This can help
debugging.


Note: you can only use your own exception classes, when you are
using the pickle serializer. This is not the default.
