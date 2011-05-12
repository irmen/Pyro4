"""
Tests for the core logic.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong.
irmen@razorvine.net - http://www.razorvine.net/python/Pyro
"""

from __future__ import with_statement
import unittest
import copy
import sys
import Pyro4.core
import Pyro4.config
import Pyro4.errors

if sys.version_info>=(3,0):
    unicode=str
    unichr=chr
if sys.version_info<(3,0):
    def tobytes(string, encoding=None):
        return string
else:
    def tobytes(string, encoding="iso-8859-1"):
        return bytes(string,encoding)

class Thing(object):
    def __init__(self, arg):
        self.arg=arg
    def __eq__(self,other):
        return self.arg==other.arg
    __hash__=object.__hash__

class CoreTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY="testsuite"
    def tearDown(self):
        Pyro4.config.HMAC_KEY=None

    def testConfig(self):
        self.assertTrue(type(Pyro4.config.COMPRESSION) is bool)
        self.assertTrue(type(Pyro4.config.NS_PORT) is int)
        config=Pyro4.config.asDict()
        self.assertTrue(type(config) is dict)
        self.assertTrue("COMPRESSION" in config)
        self.assertEqual(Pyro4.config.COMPRESSION, config["COMPRESSION"])

    def testConfigValid(self):
        try:
            Pyro4.config.XYZ_FOOBAR=True  # don't want to allow weird config names
            self.fail("expected exception for weird config item")
        except Pyro4.errors.PyroError:
            pass

    def testUriStrAndRepr(self):
        uri="PYRONAME:some_obj_name"
        p=Pyro4.core.URI(uri)
        self.assertEqual(uri,str(p))
        uri="PYRONAME:some_obj_name@host.com"
        p=Pyro4.core.URI(uri)
        self.assertEqual(uri+":"+str(Pyro4.config.NS_PORT),str(p))   # a PYRONAME uri with a hostname gets a port too if omitted
        uri="PYRONAME:some_obj_name@host.com:8888"
        p=Pyro4.core.URI(uri)
        self.assertEqual(uri,str(p))
        self.assertTrue("URI object at" in repr(p))
        uri="PYRO:12345@host.com:9999"
        p=Pyro4.core.URI(uri)
        self.assertEqual(uri,str(p))
        self.assertEqual(uri,p.asString())
        uri="PYRO:12345@./p:pipename"
        p=Pyro4.core.URI(uri)
        self.assertEqual(uri,str(p))
        uri="PYRO:12345@./u:sockname"
        p=Pyro4.core.URI(uri)
        self.assertEqual(uri,str(p))
        uri="PYRO:12345@./u:sockname"
        unicodeuri=unicode(uri)
        p=Pyro4.core.URI(unicodeuri)
        self.assertEqual(uri,str(p))
        self.assertEqual(unicodeuri,unicode(p))
        self.assertTrue(type(p.sockname) is unicode)

    def testUriParsingPyro(self):
        p=Pyro4.core.URI("PYRONAME:some_obj_name")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("some_obj_name",p.object)
        self.assertEqual(None,p.host)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(None,p.port)
        p=Pyro4.core.URI("PYRONAME:some_obj_name@host.com:9999")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("some_obj_name",p.object)
        self.assertEqual("host.com",p.host)
        self.assertEqual(9999,p.port)

        p=Pyro4.core.URI("PYRO:12345@host.com:4444")
        self.assertEqual("PYRO",p.protocol)
        self.assertEqual("12345",p.object)
        self.assertEqual("host.com",p.host)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(4444,p.port)
        p=Pyro4.core.URI("PYRO:12345@./p:pipename")
        self.assertEqual("12345",p.object)
        self.assertEqual("pipename",p.pipename)
        p=Pyro4.core.URI("PYRO:12345@./u:sockname")
        self.assertEqual("12345",p.object)
        self.assertEqual("sockname",p.sockname)

    def testUriParsingPyroname(self):
        p=Pyro4.core.URI("PYRONAME:objectname")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual(None,p.host)
        self.assertEqual(None,p.port)
        p=Pyro4.core.URI("PYRONAME:objectname@nameserverhost")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual("nameserverhost",p.host)
        self.assertEqual(Pyro4.config.NS_PORT,p.port)   # Pyroname uri with host gets a port too if not specified
        p=Pyro4.core.URI("PYRONAME:objectname@nameserverhost:4444")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual("nameserverhost",p.host)
        self.assertEqual(4444,p.port)

    def testInvalidUris(self):
        self.assertRaises(TypeError, Pyro4.core.URI, None)
        self.assertRaises(TypeError, Pyro4.core.URI, 99999)
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "a")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO::")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:a")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:x@")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:x@hostname")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:@hostname:portstr")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:@hostname:7766")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:objid@hostname:7766:bogus")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYROLOC:objname")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYROLOC:objname@host")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYROLOC:objectname@hostname:4444")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRONAME:")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRONAME:objname@nameserver:bogus")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRONAME:objname@nameserver:7766:bogus")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "FOOBAR:")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "FOOBAR:objid@hostname:7766")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:12345@./p:pipename/slash")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:12345@./u:sockname/slash")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:12345@./p:pipename:9999")
        self.assertRaises(Pyro4.errors.PyroError, Pyro4.core.URI, "PYRO:12345@./u:sockname:9999")

    def testUriUnicode(self):
        p=Pyro4.core.URI(unicode("PYRO:12345@host.com:4444")) 
        self.assertEqual("PYRO",p.protocol)
        self.assertEqual("12345",p.object)
        self.assertEqual("host.com",p.host)
        self.assertTrue(type(p.protocol) is unicode)
        self.assertTrue(type(p.object) is unicode)
        self.assertTrue(type(p.host) is unicode)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(4444,p.port)

        uri="PYRO:12345@hostname:9999"
        p=Pyro4.core.URI(uri)
        pu=Pyro4.core.URI(unicode(uri))
        self.assertEqual("PYRO",pu.protocol)
        self.assertEqual("hostname",pu.host)
        self.assertEqual(p,pu)
        self.assertEqual(str(p), str(pu))
        unicodeuri="PYRO:weirdchars"+unichr(0x20ac)+"@host"+unichr(0x20AC)+".com:4444"
        pu=Pyro4.core.URI(unicodeuri)
        self.assertEqual("PYRO",pu.protocol)
        self.assertEqual("host"+unichr(0x20AC)+".com",pu.host)
        self.assertEqual("weirdchars"+unichr(0x20AC),pu.object)
        self.assertEqual(pu.asString(), pu.__str__())
        self.assertEqual("PYRO:weirdchars"+unichr(0x20ac)+"@host"+unichr(0x20ac)+".com:4444", pu.asString())
        self.assertEqual("PYRO:weirdchars"+unichr(0x20ac)+"@host"+unichr(0x20ac)+".com:4444", unicode(pu))
        self.assertTrue("URI object at" in repr(pu))
    
    def testUriCopy(self):
        p1=Pyro4.core.URI("PYRO:12345@hostname:9999")
        p2=Pyro4.core.URI(p1)
        p3=copy.copy(p1)
        self.assertEqual(p1.protocol, p2.protocol)
        self.assertEqual(p1.host, p2.host)
        self.assertEqual(p1.port, p2.port)
        self.assertEqual(p1.object, p2.object)
        self.assertEqual(p1,p2)
        self.assertEqual(p1.protocol, p3.protocol)
        self.assertEqual(p1.host, p3.host)
        self.assertEqual(p1.port, p3.port)
        self.assertEqual(p1.object, p3.object)
        self.assertEqual(p1,p3)
        
    def testUriEqual(self):
        p1=Pyro4.core.URI("PYRO:12345@host.com:9999")
        p2=Pyro4.core.URI("PYRO:12345@host.com:9999")
        p3=Pyro4.core.URI("PYRO:99999@host.com:4444")
        self.assertEqual(p1,p2)
        self.assertNotEqual(p1,p3)
        self.assertNotEqual(p2,p3)
        p2.port=4444
        p2.object="99999"
        self.assertNotEqual(p1,p2)
        self.assertEqual(p2,p3)
        
    def testLocation(self):
        self.assertTrue(Pyro4.core.URI.isPipeOrUnixsockLocation("./p:name"))
        self.assertTrue(Pyro4.core.URI.isPipeOrUnixsockLocation("./u:name"))
        self.assertFalse(Pyro4.core.URI.isPipeOrUnixsockLocation("./x:name"))
        self.assertFalse(Pyro4.core.URI.isPipeOrUnixsockLocation("foobar"))

    def testMsgFactory(self):
        import hashlib, hmac
        def pyrohmac(data):
            hmac_key = tobytes(Pyro4.config.HMAC_KEY)
            data=tobytes(data)
            return hmac.new(hmac_key, data, digestmod=hashlib.sha1).digest()
        MF=Pyro4.core.MessageFactory
        MF.createMessage(99, None, 0,0) # doesn't check msg type here
        self.assertRaises(Pyro4.errors.ProtocolError, MF.parseMessageHeader, "FOOBAR")
        hdr=MF.createMessage(MF.MSG_CONNECT, tobytes("hello"),0,0)[:-5]
        msgType,flags,seq,dataLen,datahmac=MF.parseMessageHeader(hdr)
        self.assertEqual(MF.MSG_CONNECT, msgType)
        self.assertEqual(0, flags)
        self.assertEqual(5, dataLen)
        self.assertEqual(pyrohmac("hello"), datahmac)
        hdr=MF.createMessage(MF.MSG_RESULT, None,0,0)
        msgType,flags,seq,dataLen,datahmac=MF.parseMessageHeader(hdr)
        self.assertEqual(MF.MSG_RESULT, msgType)
        self.assertEqual(0, flags)
        self.assertEqual(0, dataLen)
        hdr=MF.createMessage(MF.MSG_RESULT, tobytes("hello"), 42, 0)[:-5]
        msgType,flags,seq,dataLen,datahmac=MF.parseMessageHeader(hdr)
        self.assertEqual(MF.MSG_RESULT, msgType)
        self.assertEqual(42, flags)
        self.assertEqual(5, dataLen)
        msg=MF.createMessage(255,None,0,255)
        self.assertEqual(38,len(msg))
        msg=MF.createMessage(1,None,0,255)
        self.assertEqual(38,len(msg))
        msg=MF.createMessage(1,None,flags=253,seq=254)
        self.assertEqual(38,len(msg))
        # compression is a job of the code supplying the data, so the messagefactory should leave it untouched
        data=tobytes("x"*1000)
        msg=MF.createMessage(MF.MSG_INVOKE, data, 0,0)
        msg2=MF.createMessage(MF.MSG_INVOKE, data, MF.FLAGS_COMPRESSED,0)
        self.assertEqual(len(msg),len(msg2))

    def testMsgFactoryProtocolVersion(self):
        version=Pyro4.constants.PROTOCOL_VERSION
        Pyro4.constants.PROTOCOL_VERSION=0;     # fake invalid protocol version number
        msg=Pyro4.core.MessageFactory.createMessage(Pyro4.core.MessageFactory.MSG_RESULT, tobytes("result"), 0, 1)
        try:
            Pyro4.core.MessageFactory.parseMessageHeader(msg)
            self.fail("expected protocolerror")
        except Pyro4.errors.ProtocolError:
            pass
        finally:
            Pyro4.constants.PROTOCOL_VERSION=version
        
    def testProxyOffline(self):
        # only offline stuff here.
        # online stuff needs a running daemon, so we do that in another test, to keep this one simple
        self.assertRaises(TypeError, Pyro4.core.Proxy, 999)  # wrong arg
        p1=Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p2=Pyro4.core.Proxy(Pyro4.core.URI("PYRO:9999@localhost:15555"))
        self.assertEqual(p1._pyroUri, p2._pyroUri)
        self.assertTrue(p1._pyroConnection is None)
        p1._pyroRelease()
        p1._pyroRelease()
        # try copying a not-connected proxy
        p3=copy.copy(p1)
        self.assertTrue(p3._pyroConnection is None)
        self.assertTrue(p1._pyroConnection is None)
        self.assertEqual(p3._pyroUri, p1._pyroUri)
        self.assertFalse(p3._pyroUri is p1._pyroUri)
        self.assertEqual(p3._pyroSerializer, p1._pyroSerializer)
        self.assertTrue(p3._pyroSerializer is p1._pyroSerializer)

    def testProxyStr(self):
        p=Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        self.assertEqual("<Pyro Proxy for PYRO:9999@localhost:15555>", str(p))
        self.assertEqual(unicode("<Pyro Proxy for PYRO:9999@localhost:15555>"), unicode(p))
        self.assertTrue("Proxy object at" in repr(p))
        
    def testProxySettings(self):
        p1=Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p2=Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p1._pyroOneway.add("method")
        self.assertTrue("method" in p1._pyroOneway, "p1 should have oneway method")
        self.assertFalse("method" in p2._pyroOneway, "p2 should not have the same oneway method")
        self.assertFalse(p1._pyroOneway is p2._pyroOneway, "p1 and p2 should have different oneway tables")
        
    def testProxyWithStmt(self):
        class ConnectionMock(object):
            closeCalled=False
            def close(self):
                self.closeCalled=True

        connMock=ConnectionMock()
        p=Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        p._pyroConnection=connMock
        self.assertFalse(connMock.closeCalled)
        p._pyroRelease()
        self.assertTrue(p._pyroConnection is None)
        self.assertTrue(connMock.closeCalled)
        
        connMock=ConnectionMock()
        with Pyro4.core.Proxy("PYRO:9999@localhost:15555") as p:
            p._pyroConnection=connMock
        self.assertTrue(p._pyroConnection is None)
        self.assertTrue(connMock.closeCalled)
        connMock=ConnectionMock()
        try:
            with Pyro4.core.Proxy("PYRO:9999@localhost:15555") as p:
                p._pyroConnection=connMock
                print(1//0)  # cause an error
            self.fail("expected error")
        except ZeroDivisionError:
            pass
        self.assertTrue(p._pyroConnection is None)
        self.assertTrue(connMock.closeCalled)
        connMock=ConnectionMock()
        p=Pyro4.core.Proxy("PYRO:9999@localhost:15555")
        with p:
            self.assertTrue(p._pyroUri is not None)
        with p:
            self.assertTrue(p._pyroUri is not None)            

    def testRemoteMethod(self):
        class Proxy(object):
            def invoke(self, name, args, kwargs):
                return "INVOKED name=%s args=%s kwargs=%s" % (name,args,kwargs)
            def __getattr__(self, name):
                return Pyro4.core._RemoteMethod(self.invoke, name)
        o=Proxy()
        self.assertEqual("INVOKED name=foo args=(1,) kwargs={}", o.foo(1)) #normal
        self.assertEqual("INVOKED name=foo.bar args=(1,) kwargs={}", o.foo.bar(1)) #dotted
        self.assertEqual("INVOKED name=foo.bar args=(1, 'hello') kwargs={'a': True}", o.foo.bar(1,"hello",a=True))
        p=Pyro4.core.Proxy("PYRO:obj@host:666")
        a=p.someattribute
        self.assertTrue(isinstance(a, Pyro4.core._RemoteMethod), "attribute access should just be a RemoteMethod")
        a2=a.nestedattribute
        self.assertTrue(isinstance(a2, Pyro4.core._RemoteMethod), "nested attribute should just be another RemoteMethod")

    def testTimeoutGetSet(self):
        class ConnectionMock(object):
            def __init__(self):
                self.timeout=Pyro4.config.COMMTIMEOUT
            def close(self):
                pass
        Pyro4.config.COMMTIMEOUT=None
        p=Pyro4.core.Proxy("PYRO:obj@host:555")
        self.assertEqual(None, p._pyroTimeout)
        p._pyroTimeout=5
        self.assertEqual(5, p._pyroTimeout)
        p=Pyro4.core.Proxy("PYRO:obj@host:555")
        p._pyroConnection=ConnectionMock()
        self.assertEqual(None, p._pyroTimeout)
        p._pyroTimeout=5
        self.assertEqual(5, p._pyroTimeout)
        self.assertEqual(5, p._pyroConnection.timeout)
        Pyro4.config.COMMTIMEOUT=2
        p=Pyro4.core.Proxy("PYRO:obj@host:555")
        p._pyroConnection=ConnectionMock()
        self.assertEqual(2, p._pyroTimeout)
        self.assertEqual(2, p._pyroConnection.timeout)
        p._pyroTimeout=None
        self.assertEqual(None, p._pyroTimeout)
        self.assertEqual(None, p._pyroConnection.timeout)
        Pyro4.config.COMMTIMEOUT=None

    def testDecorators(self):
        # just test the decorator itself, testing the callback
        # exception handling is kinda hard in unit tests. Maybe later.
        class Test(object):
            @Pyro4.callback
            def method(self):
                pass
            def method2(self):
                pass
        t=Test()
        self.assertEqual(True, getattr(t.method,"_pyroCallback"))
        self.assertEqual(False, getattr(t.method2,"_pyroCallback", False))
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
