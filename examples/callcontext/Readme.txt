This example shows the use of several advanced Pyro constructs:

- overriding proxy and daemon to customize their behavior
- setting the hmac key
- using the call context in the server to obtain information about the client
- setting and printing correlation ids
- using custom message annotations (both old style with proxy/daemon method override,
  and new style using the call context which is possible since Pyro 4.56)
