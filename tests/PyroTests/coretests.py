import unittest

import Pyro.util
import Pyro.core
import Pyro.config
import Pyro.errors

class Thing(Pyro.core.ObjBase):
    def __init__(self, arg):
        super(Thing,self).__init__()
        self.arg=arg
    def __eq__(self,other):
        return self.arg==other.arg and self._pyroObjectId==other._pyroObjectId

class CoreTests(unittest.TestCase):

    def testUriStr(self):
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name")
        self.assertEqual("PYRONAME:some_obj_name",str(p))
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name@host.com")
        self.assertEqual("PYRONAME:some_obj_name@host.com:9090",str(p))
        p=Pyro.core.PyroURI("PYRONAME:some_obj_name@host.com:8888")
        self.assertEqual("PYRONAME:some_obj_name@host.com:8888",str(p))
        p=Pyro.core.PyroURI("PYRO:12345@host.com")
        self.assertEqual("PYRO:12345@host.com:7766",str(p))
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

    def testUriParsing(self):
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

        p=Pyro.core.PyroURI("PYRO:12345@host.com")
        self.assertEqual("PYRO",p.protocol)
        self.assertEqual("12345",p.object)
        self.assertEqual("host.com",p.host)
        self.assertEqual(None,p.pipename)
        self.assertEqual(None,p.sockname)
        self.assertEqual(Pyro.config.DEFAULT_PORT,p.port)
        p=Pyro.core.PyroURI("PYRO:12345@host.com:9999")
        self.assertEqual("host.com",p.host)
        self.assertEqual(9999,p.port)

        p=Pyro.core.PyroURI("PYRO:12345@./p:pipename")
        self.assertEqual("12345",p.object)
        self.assertEqual("pipename",p.pipename)
        p=Pyro.core.PyroURI("PYRO:12345@./u:sockname")
        self.assertEqual("12345",p.object)
        self.assertEqual("sockname",p.sockname)

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

    def testSerializability(self):
        ser=Pyro.util.Serializer()
        uri=Pyro.core.PyroURI("PYRO:9999@host.com:4444")
        p=ser.serialize(uri)
        uri2=ser.deserialize(p)
        self.assertEqual(uri, uri2)
        
        thing=Thing(42)
        self.assertTrue(thing._pyroObjectId is not None)
        p=ser.serialize(thing)
        thing2=ser.deserialize(p)
        self.assertEquals(thing2,thing)
        self.assertEqual(thing2._pyroObjectId, thing._pyroObjectId)

        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()