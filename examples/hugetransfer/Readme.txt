This test transfers huge data structures to see how Pyro handles those.
It sets a socket timeout as well to see how Pyro handles that.


A couple of problems could be exposed by this test:

- Some systems don't really seem to like non blocking sockets and large
  data transfers. For instance Mac OS X seems eager to cause EAGAIN errors
  when your data exceeds 'the devils number' number of bytes.
  Note that this problem only occurs when using specific socket code.
  Pyro contains a workaround. More info:
    http://old.nabble.com/The-Devil%27s-Number-td9169165.html
    http://www.cherrypy.org/ticket/598
    
- Other systems seemed to have problems receiving large chunks of data.
  Windows causes memory errors when the receive buffer is too large.
  Pyro's receive loop works with comfortable smaller data chunks,
  to avoid these kind of problems.
