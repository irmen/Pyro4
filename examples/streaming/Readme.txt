Show the iterator item streaming support in Pyro 4.49 or newer.
If enabled in the server (it is enabled by default), you can return
an iterator or generator from a remote call.
The client receives a real iterator as a result and can iterate over
it to stream the elements one by one from the remote iterator.

