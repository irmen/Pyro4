from __future__ import with_statement

import unittest
import copy
import Pyro.core
import Pyro.config
import Pyro.errors

class Thing(object):
    def __init__(self, arg):
        self.arg=arg
    def __eq__(self,other):
        return self.arg==other.arg
    __hash__=object.__hash__

class CoreTests(unittest.TestCase):

    def testUriStrAndRepr(self):
        uri="PYRONAME:some_obj_name"
        p=Pyro.core.PyroURI(uri)
        self.assertEqual(uri,str(p))
        uri="PYRONAME:some_obj_name@host.com"
        p=Pyro.core.PyroURI(uri)
        self.assertEqual(uri+":"+str(Pyro.config.NS_PORT),str(p))   # a PYRONAME uri with a hostname gets a port too if omitted
        uri="PYRONAME:some_obj_name@host.com:8888"
        p=Pyro.core.PyroURI(uri)
        self.assertEqual(uri,str(p))
        self.assertTrue("PyroURI object at" in repr(p))
        uri="PYRO:12345@host.com:9999"
        p=Pyro.core.PyroURI(uri)
        self.assertEqual(uri,str(p))
        self.assertEqual(uri,p.asString())
        uri="PYRO:12345@./p:pipename"
        p=Pyro.core.PyroURI(uri)
        self.assertEqual(uri,str(p))
        uri="PYRO:12345@./u:sockname"
        p=Pyro.core.PyroURI(uri)
        self.assertEqual(uri,str(p))
        uri="PYRO:12345@./u:sockname"
        unicodeuri=unicode(uri)
        p=Pyro.core.PyroURI(unicodeuri)
        self.assertEqual(uri,str(p))
        self.assertEqual(unicodeuri,unicode(p))
        self.assertTrue(type(p.sockname) is unicode)

    def testUriParsingPyro(self):
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("some_obj_name",p.object)
        self.assertEqual(None,p.host)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(None,p.port)
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name@host.com:9999")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("some_obj_name",p.object)
        self.assertEqual("host.com",p.host)
        self.assertEqual(9999,p.port)

        p=Pyro.core.PyroURI("PYRO:12345@host.com:4444")
        self.assertEqual("PYRO",p.protocol)
        self.assertEqual("12345",p.object)
        self.assertEqual("host.com",p.host)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(4444,p.port)
        p=Pyro.core.PyroURI("PYRO:12345@./p:pipename")
        self.assertEqual("12345",p.object)
        self.assertEqual("pipename",p.pipename)
        p=Pyro.core.PyroURI("PYRO:12345@./u:sockname")
        self.assertEqual("12345",p.object)
        self.assertEqual("sockname",p.sockname)

    def testUriParsingPyroname(self):
        p=Pyro.core.PyroURI("PYRONAME:objectname")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual(None,p.host)
        self.assertEqual(None,p.port)
        p=Pyro.core.PyroURI("PYRONAME:objectname@nameserverhost")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual("nameserverhost",p.host)
        self.assertEqual(Pyro.config.NS_PORT,p.port)   # Pyroname uri with host gets a port too if not specified
        p=Pyro.core.PyroURI("PYRONAME:objectname@nameserverhost:4444")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual("nameserverhost",p.host)
        self.assertEqual(4444,p.port)

    def testInvalidUris(self):
        self.assertRaises(TypeError, Pyro.core.PyroURI, None)
        self.assertRaises(TypeError, Pyro.core.PyroURI, 99999)
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "a")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO::")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:a")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:x@")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:x@hostname")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:@hostname:portstr")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:@hostname:7766")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:objid@hostname:7766:bogus")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYROLOC:objname")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYROLOC:objname@host")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYROLOC:objectname@hostname:4444")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRONAME:")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRONAME:objname@nameserver:bogus")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRONAME:objname@nameserver:7766:bogus")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "FOOBAR:")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "FOOBAR:objid@hostname:7766")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:12345@./p:pipename/slash")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:12345@./u:sockname/slash")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:12345@./p:pipename:9999")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRO:12345@./u:sockname:9999")

    def testUriUnicode(self):
        p=Pyro.core.PyroURI(u"PYRO:12345@host.com:4444") 
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
        p=Pyro.core.PyroURI(uri)
        pu=Pyro.core.PyroURI(unicode(uri))
        self.assertEqual("PYRO",pu.protocol)
        self.assertEqual("hostname",pu.host)
        self.assertEqual(p,pu)
        self.assertEqual(str(p), str(pu))
        unicodeuri=u"PYRO:weirdchars\u20AC@host\u20AC.com:4444"
        pu=Pyro.core.PyroURI(unicodeuri)
        self.assertEqual("PYRO",pu.protocol)
        self.assertEqual(u"host\u20AC.com",pu.host)
        self.assertEqual(u"weirdchars\u20AC",pu.object)
        self.assertEqual(pu.asString(), pu.__str__())
        self.assertEqual(u"PYRO:weirdchars\u20ac@host\u20ac.com:4444", pu.asString())
        self.assertEqual(u"PYRO:weirdchars\u20ac@host\u20ac.com:4444", unicode(pu))
        self.assertTrue("PyroURI object at" in repr(pu))
    
    def testUriCopy(self):
        p1=Pyro.core.PyroURI("PYRO:12345@hostname:9999")
        p2=Pyro.core.PyroURI(p1)
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
        p1=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        p2=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        p3=Pyro.core.PyroURI("PYRO:99999@host.com:4444")
        self.assertEqual(p1,p2)
        self.assertNotEqual(p1,p3)
        self.assertNotEqual(p2,p3)
        p2.port=4444
        p2.object="99999"
        self.assertNotEqual(p1,p2)
        self.assertEqual(p2,p3)
        
    def testLocation(self):
        self.assertTrue(Pyro.core.PyroURI.isPipeOrUnixsockLocation("./p:name"))
        self.assertTrue(Pyro.core.PyroURI.isPipeOrUnixsockLocation("./u:name"))
        self.assertFalse(Pyro.core.PyroURI.isPipeOrUnixsockLocation("./x:name"))
        self.assertFalse(Pyro.core.PyroURI.isPipeOrUnixsockLocation("foobar"))

    def testMsgFactory(self):
        MF=Pyro.core.MessageFactory
        MF.createMessage(99, None) # doesn't check msg type here
        self.assertRaises(Pyro.errors.ProtocolError, MF.parseMessageHeader, "FOOBAR")
        hdr=MF.createMessage(MF.MSG_CONNECT, "hello")[:-5]
        msgType,flags,dataLen=MF.parseMessageHeader(hdr)
        self.assertEqual(MF.MSG_CONNECT, msgType)
        self.assertEqual(0, flags)
        self.assertEqual(5, dataLen)
        hdr=MF.createMessage(MF.MSG_RESULT, None)
        msgType,flags,dataLen=MF.parseMessageHeader(hdr)
        self.assertEqual(MF.MSG_RESULT, msgType)
        self.assertEqual(0, flags)
        self.assertEqual(0, dataLen)
        hdr=MF.createMessage(MF.MSG_RESULT, "hello", 42)[:-5]
        msgType,flags,dataLen=MF.parseMessageHeader(hdr)
        self.assertEqual(MF.MSG_RESULT, msgType)
        self.assertEqual(42, flags)
        self.assertEqual(5, dataLen)
        msg=MF.createMessage(255,None)
        self.assertEqual("PYRO\x00"+chr(Pyro.constants.PROTOCOL_VERSION)+"\x00\xff\x00\x00\x00\x00\x00\x00",msg)
        msg=MF.createMessage(1,None)
        self.assertEqual("PYRO\x00"+chr(Pyro.constants.PROTOCOL_VERSION)+"\x00\x01\x00\x00\x00\x00\x00\x00",msg)
        msg=MF.createMessage(1,None,flags=255)
        self.assertEqual("PYRO\x00"+chr(Pyro.constants.PROTOCOL_VERSION)+"\x00\x01\x00\xff\x00\x00\x00\x00",msg)
        # compression is a job of the code supplying the data, so the messagefactory should leave it untouched
        data="x"*1000
        msg=MF.createMessage(MF.MSG_INVOKE, data, 0)
        msg2=MF.createMessage(MF.MSG_INVOKE, data, MF.FLAGS_COMPRESSED)
        self.assertEquals(len(msg),len(msg2))

    def testProxyOffline(self):
        # only offline stuff here.
        # online stuff needs a running daemon, so we do that in another test, to keep this one simple
        self.assertRaises(TypeError, Pyro.core.Proxy, 999)  # wrong arg
        p1=Pyro.core.Proxy("PYRO:9999@localhost:15555")
        p2=Pyro.core.Proxy(Pyro.core.PyroURI("PYRO:9999@localhost:15555"))
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
        self.assertFalse(p3._pyroSerializer is p1._pyroSerializer)

    def testProxyStr(self):
        p=Pyro.core.Proxy("PYRO:9999@localhost:15555")
        self.assertEqual("<Pyro Proxy for PYRO:9999@localhost:15555>", str(p))
        self.assertEqual(u"<Pyro Proxy for PYRO:9999@localhost:15555>", unicode(p))
        self.assertTrue("Proxy object at" in repr(p))
        
    def testProxyWithStmt(self):
        class ConnectionMock(object):
            closeCalled=False
            def close(self):
                self.closeCalled=True

        connMock=ConnectionMock()
        p=Pyro.core.Proxy("PYRO:9999@localhost:15555")
        p._pyroConnection=connMock
        self.assertFalse(connMock.closeCalled)
        p._pyroRelease()
        self.assertTrue(p._pyroConnection is None)
        self.assertTrue(connMock.closeCalled)
        
        connMock=ConnectionMock()
        with Pyro.core.Proxy("PYRO:9999@localhost:15555") as p:
            p._pyroConnection=connMock
        self.assertTrue(p._pyroConnection is None)
        self.assertTrue(connMock.closeCalled)
        connMock=ConnectionMock()
        try:
            with Pyro.core.Proxy("PYRO:9999@localhost:15555") as p:
                p._pyroConnection=connMock
                print 1//0  # cause an error
            self.fail("expected error")
        except ZeroDivisionError:
            pass
        self.assertTrue(p._pyroConnection is None)
        self.assertTrue(connMock.closeCalled)
        connMock=ConnectionMock()
        p=Pyro.core.Proxy("PYRO:9999@localhost:15555")
        with p:
            self.assertTrue(p._pyroUri is not None)
        with p:
            self.assertTrue(p._pyroUri is not None)            

    def testRemoteMethod(self):
        class Proxy(object):
            def invoke(self, name, args, kwargs):
                return "INVOKED name=%s args=%s kwargs=%s" % (name,args,kwargs)
            def __getattr__(self, name):
                return Pyro.core._RemoteMethod(self.invoke, name)
        o=Proxy()
        self.assertEqual("INVOKED name=foo args=(1,) kwargs={}", o.foo(1))
        self.assertEqual("INVOKED name=foo.bar args=(1,) kwargs={}", o.foo.bar(1))
        self.assertEqual("INVOKED name=foo.bar args=(1, 'hello') kwargs={'a': True}", o.foo.bar(1,"hello",a=True))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
