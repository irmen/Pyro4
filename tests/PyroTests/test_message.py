"""
Tests for pyro write protocol message.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

import hashlib
import hmac
from testsupport import unittest
import Pyro4.message
from Pyro4.message import Message
import Pyro4.constants


class MessageTests(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY = b"testsuite"

    def tearDown(self):
        Pyro4.config.HMAC_KEY = None

    def testMsgFactory(self):
        def pyrohmac(data):
            return hmac.new(Pyro4.config.HMAC_KEY, data, digestmod=hashlib.sha1).digest()
        Message(99, b"", 0, 0) # doesn't check msg type here
        self.assertRaises(Pyro4.errors.ProtocolError, Message.from_header, "FOOBAR")
        msg = Message(Pyro4.message.MSG_CONNECT, b"hello", 0, 0)
        self.assertEqual(Pyro4.message.MSG_CONNECT, msg.type)
        self.assertEqual(5, msg.datasize)
        self.assertEqual(b"hello", msg.data)
        self.assertEqual(Pyro4.message.FLAGS_HMAC, msg.flags)

        hdr = msg.to_bytes()[:-5]
        msg = Message.from_header(hdr)
        self.assertEqual(Pyro4.message.MSG_CONNECT, msg.type)
        self.assertEqual(Pyro4.message.FLAGS_HMAC, msg.flags)
        self.assertEqual(5, msg.datasize)
        self.assertEqual(pyrohmac(b"hello"), msg.hmac)

        hdr = Message(Pyro4.message.MSG_RESULT, b"", 0, 0).to_bytes()
        msg = Message.from_header(hdr)
        self.assertEqual(Pyro4.message.MSG_RESULT, msg.type)
        self.assertEqual(Pyro4.message.FLAGS_HMAC, msg.flags)
        self.assertEqual(0, msg.datasize)

        hdr = Message(Pyro4.message.MSG_RESULT, b"hello", 42, 0).to_bytes()[:-5]
        msg = Message.from_header(hdr)
        self.assertEqual(Pyro4.message.MSG_RESULT, msg.type)
        self.assertEqual(42, msg.flags)
        self.assertEqual(5, msg.datasize)

        msg = Message(255, b"", 0, 255).to_bytes()
        self.assertEqual(38, len(msg))
        msg = Message(1, b"", 0, 255).to_bytes()
        self.assertEqual(38, len(msg))
        msg = Message(1, b"", flags=253, seq=254).to_bytes()
        self.assertEqual(38, len(msg))

        # compression is a job of the code supplying the data, so the messagefactory should leave it untouched
        data = b"x"*1000
        msg = Message(Pyro4.message.MSG_INVOKE, data, 0,0).to_bytes()
        msg2 = Message(Pyro4.message.MSG_INVOKE, data, Pyro4.message.FLAGS_COMPRESSED,0).to_bytes()
        self.assertEqual(len(msg),len(msg2))

    def testMsgFactoryProtocolVersion(self):
        version=Pyro4.constants.PROTOCOL_VERSION
        Pyro4.constants.PROTOCOL_VERSION=0     # fake invalid protocol version number
        msg = Message(Pyro4.message.MSG_RESULT, b"", 0, 1).to_bytes()
        Pyro4.constants.PROTOCOL_VERSION=version
        self.assertRaises(Pyro4.errors.ProtocolError, Message.from_header, msg)


if __name__ == "__main__":
    unittest.main()
