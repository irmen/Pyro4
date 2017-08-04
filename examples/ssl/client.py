from __future__ import print_function
import sys
import Pyro4.core
import Pyro4.errors

if sys.version_info < (3, 0):
    input = raw_input


Pyro4.config.SSL = True
Pyro4.config.SSL_CACERTS = "../../certs/server_cert.pem"    # to make ssl accept the self-signed server cert
Pyro4.config.SSL_CLIENTCERT = "../../certs/client_cert.pem"
Pyro4.config.SSL_CLIENTKEY = "../../certs/client_key.pem"
print("SSL enabled (2-way).")


def verify_cert(cert):
    if not cert:
        raise Pyro4.errors.CommunicationError("cert missing")
    # note: hostname and expiry date validation is already successfully performed by the SSL layer itself
    # not_before = datetime.datetime.utcfromtimestamp(ssl.cert_time_to_seconds(cert["notBefore"]))
    # print("not before:", not_before)
    # not_after = datetime.datetime.utcfromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]))
    # print("not after:", not_after)
    # today = datetime.datetime.now()
    # if today > not_after or today < not_before:
    #     raise Pyro4.errors.CommunicationError("cert not yet valid or expired")
    if cert["serialNumber"] != "D163AB82B8B74DE6":
        raise Pyro4.errors.CommunicationError("cert serial number incorrect")
    issuer = dict(p[0] for p in cert["issuer"])
    subject = dict(p[0] for p in cert["subject"])
    if issuer["organizationName"] != "Razorvine.net":
        # issuer is not often relevant I guess, but just to show that you have the data
        raise Pyro4.errors.CommunicationError("cert not issued by Razorvine.net")
    if subject["countryName"] != "NL":
        raise Pyro4.errors.CommunicationError("cert not for country NL")
    if subject["organizationName"] != "Razorvine.net":
        raise Pyro4.errors.CommunicationError("cert not for Razorvine.net")
    print("(SSL server cert is ok: serial={ser}, subject={subj})"
          .format(ser=cert["serialNumber"], subj=subject["organizationName"]))


# to make Pyro verify the certificate on new connections, use the handshake mechanism:
class CertCheckingProxy(Pyro4.core.Proxy):
    def _pyroValidateHandshake(self, response):
        cert = self._pyroConnection.getpeercert()
        verify_cert(cert)


# Note: to automatically enforce certificate verification for all proxy objects you create,
# you can also monkey-patch the method in the Proxy class itself.
# Then you don't have to make sure that you're using CertCheckingProxy every time.
# However some other Proxy subclass can (will) override this again!
#
# def certverifier(self, response):
#     cert = self._pyroConnection.getpeercert()
#     verify_cert(cert)
# Pyro4.core.Proxy._pyroValidateHandshake = certverifier


uri = input("Server uri: ").strip()
with CertCheckingProxy(uri) as p:
    response = p.echo("client speaking")
    print("response:", response)
