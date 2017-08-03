SSL example showing how to configure 2-way-SSL with custom certificate validation.

What this means is that the server has a certificate, and the client as well.
The server only accepts connections from clients that provide the proper certificate
(and ofcourse, clients only connect to servers having a proper certificate).

By using Pyro's handshake mechanism you can easily add custom certificate verification steps
in both the client (proxy) and server (daemon). This is more or less required, because
you should be checking if the certificate is indeed from the party you expected...

This example uses the self-signed demo certs that come with Pyro, so in the code
you'll also see that we configure the SSL_CACERTS so that SSL will accept the self-signed
certificate as a valid cert.



If the connection is successfully established, all communication is then encrypted and secure.
