This example shows two ways of embedding Pyro's event loop in another
application, in this case a GUI application (written using Tkinter).

There's one application where a background thread is used for the Pyro
daemon. This means you can't directly update the GUI from the Pyro objects
(because GUI update calls need to be performed from the GUI mainloop thread).
So the threaded gui server submits the gui update calls via a Queue to the
actual gui thread.  There is a nice thing however, the GUI won't freeze up
if a Pyro method call takes a while to execute.

The other application doesn't use any threads besides the normal GUI thread.
It uses a Tkinter-callback to check Pyro's sockets at a fast interval rate
to see if it should dispatch any events to the daemon.
Not using threads means you can directly update the GUI from Pyro calls but
it also means the GUI will freeze if a Pyro method call takes a while.
You also can't use Pyro's requestloop anymore, as it will lock up the GUI
while it waits for incoming calls. You'll need to check yourself, using
select() on the Pyro socket(s) and dispatching to the daemon manually.

