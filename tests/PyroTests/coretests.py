import unittest

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

    def testUriStr(self):
        #freeport=Pyro.socketutil.findUnusedPort()
        #Pyro.config.PORT=freeport
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name")
        self.assertEqual("PYRONAME:some_obj_name",str(p))
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name@host.com")
        self.assertEqual("PYRONAME:some_obj_name@host.com:9090",str(p))
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name@host.com:8888")
        self.assertEqual("PYRONAME:some_obj_name@host.com:8888",str(p))
        p=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        self.assertEqual("PYRO:12345@host.com:9999",str(p))
        p=Pyro.core.PyroURI("PYRO:12345@./p:pipename")
        self.assertEqual("PYRO:12345@./p:pipename",str(p))
        p=Pyro.core.PyroURI("PYRO:12345@./u:sockname")
        self.assertEqual("PYRO:12345@./u:sockname",str(p))
        # silly unicode uri
        p=Pyro.core.PyroURI(u"PYRO:12345@./u:sockname")
        self.assertEqual("PYRO:12345@./u:sockname",str(p))
        self.assertTrue(type(p.sockname) is str)

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
        self.assertEqual(Pyro.config.NS_PORT,p.port)
        p=Pyro.core.PyroURI("PYRONAME:objectname@nameserverhost:4444")
        self.assertEqual("PYRONAME",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual("nameserverhost",p.host)
        self.assertEqual(4444,p.port)

    def testUriParsingPyroloc(self):
        p=Pyro.core.PyroURI("PYROLOC:objectname@hostname:4444")
        self.assertEqual("PYROLOC",p.protocol)
        self.assertEqual("objectname",p.object)
        self.assertEqual("hostname",p.host)
        self.assertEqual(4444,p.port)

    def testInvalidUris(self):
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, None)
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
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRONAME:")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRONAME:objname@nameserver:bogus")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "PYRONAME:objname@nameserver:7766:bogus")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "FOOBAR:")
        self.assertRaises(Pyro.errors.PyroError, Pyro.core.PyroURI, "FOOBAR:objid@hostname:7766")
    
    def testUriUnicode(self):
        uri="PYRO:12345@hostname:9999"
        p=Pyro.core.PyroURI(uri)
        pu=Pyro.core.PyroURI(unicode(uri))
        self.assertEqual("PYRO",pu.protocol)
        self.assertEqual("hostname",pu.host)
        self.assertEqual(p,pu)
    
    def testUriCopy(self):
        p1=Pyro.core.PyroURI("PYRO:12345@hostname:9999")
        p2=Pyro.core.PyroURI(p1)
        self.assertEqual(p1.protocol, p2.protocol)
        self.assertEqual(p1.host, p2.host)
        self.assertEqual(p1.port, p2.port)
        self.assertEqual(p1.object, p2.object)
        self.assertEqual(p1,p2)
        
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

    def testMsgFactory(self):
        MF=Pyro.core.MessageFactory
        self.assertRaises(Pyro.errors.ProtocolError, MF.createMessage, 99, None)
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
        import copy
        p3=copy.copy(p1)
        self.assertTrue(p3._pyroConnection is None)
        self.assertTrue(p1._pyroConnection is None)
        self.assertEqual(p3._pyroUri, p1._pyroUri)
        self.assertFalse(p3._pyroUri is p1._pyroUri)
        self.assertEqual(p3._pyroSerializer, p1._pyroSerializer)
        self.assertFalse(p3._pyroSerializer is p1._pyroSerializer)

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