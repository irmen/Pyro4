from __future__ import print_function
import Pyro4.core


class Safe(object):
    @Pyro4.expose
    def echo(self, message):
        print("got message:", message)
        return "hi!"


Pyro4.config.SSL = True
Pyro4.config.SSL_REQUIRECLIENTCERT = True   # enable 2-way ssl
Pyro4.config.SSL_SERVERCERT = "../../certs/server_cert.pem"
Pyro4.config.SSL_SERVERKEY = "../../certs/server_key.pem"
Pyro4.config.SSL_CACERTS = "../../certs/client_cert.pem"    # to make ssl accept the self-signed client cert
print("SSL enabled (2-way).")


class CertValidatingDaemon(Pyro4.core.Daemon):
    def validateHandshake(self, conn, data):
        cert = conn.getpeercert()
        if not cert:
            raise Pyro4.errors.CommunicationError("client cert missing")
        # note: hostname and expiry date validation is already successfully performed by the SSL layer itself
        # not_before = datetime.datetime.utcfromtimestamp(ssl.cert_time_to_seconds(cert["notBefore"]))
        # print("not before:", not_before)
        # not_after = datetime.datetime.utcfromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]))
        # print("not after:", not_after)
        # today = datetime.datetime.now()
        # if today > not_after or today < not_before:
        #     raise Pyro4.errors.CommunicationError("cert not yet valid or expired")
        if cert["serialNumber"] != "9BFD9872D96F066C":
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
        print("(SSL client cert is ok: serial={ser}, subject={subj})"
              .format(ser=cert["serialNumber"], subj=subject["organizationName"]))
        return super(CertValidatingDaemon, self).validateHandshake(conn, data)


d = CertValidatingDaemon()
uri = d.register(Safe)
print("server uri:", uri)
d.requestLoop()
