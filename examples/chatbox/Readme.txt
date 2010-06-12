Chat box example.

This chat box example is constructed as follows:

A Chat Server (Pyro object) handles the login/logoff process
and keeps track of all chat channels and clients that are
subscribed to each channel.
It implements the chatting and distributing of chat messages
to all subscribers. It uses oneway calls for that to improve
performance with a large number of subscribers, and to avoid
blocking.

The chat client runs the user input processing in the main thread.
It runs another thread with the Pyro daemon that is listening 
for server chat messages, so that they can be printed while
the main thread is still waiting for user input. 
 