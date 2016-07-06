This example shows two ways of dealing with a third party library whose
source code you cannot or don't want to change, and still use its classes directly in Pyro.

The first server uses the @expose decorator but applies it as a regular function to create a wrapped,
eposed class from the library class. That wrapped class is then registered instead.
There are a couple of caveats when using this approach, see the relevant paragraph
in the server chapter in the documentation for details.

The second server2 shows the approach that I personally prefer: creating explicit adapter classes
that call out to the library. You then have full control over what is happening.
