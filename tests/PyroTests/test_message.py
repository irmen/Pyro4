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
import Pyro4.util
import Pyro4.errors


def pyrohmac(data, annotations={}):
    mac = hmac.new(Pyro4.config.HMAC_KEY, data, digestmod=hashlib.sha1)
    for k, v in annotations.items():
        if k != "HMAC":
            mac.update(v)
    return mac.digest()


class ConnectionMock(object):
    def __init__(self, data=b""):
        self.received = data
    def send(self, data):
        self.received += data
    def recv(self, datasize):
        chunk = self.received[:datasize]
        self.received = self.received[datasize:]
        return chunk


class MessageTestsHmac(unittest.TestCase):
    def setUp(self):
        Pyro4.config.HMAC_KEY = b"testsuite"
        self.ser = Pyro4.util.get_serializer(Pyro4.config.SERIALIZER)

    def tearDown(self):
        Pyro4.config.HMAC_KEY = None

    def testMessage(self):
        Message(99, b"", self.ser.serializer_id, 0, 0) # doesn't check msg type here
        self.assertRaises(Pyro4.errors.ProtocolError, Message.from_header, "FOOBAR")
        msg = Message(Pyro4.message.MSG_CONNECT, b"hello", self.ser.serializer_id, 0, 0)
        self.assertEqual(Pyro4.message.MSG_CONNECT, msg.type)
        self.assertEqual(5, msg.data_size)
        self.assertEqual(b"hello", msg.data)
        self.assertEqual(4+2+20, msg.annotations_size)
        mac = pyrohmac(b"hello", msg.annotations)
        self.assertDictEqual({"HMAC": mac}, msg.annotations)

        hdr = msg.to_bytes()[:24]
        msg = Message.from_header(hdr)
        self.assertEqual(Pyro4.message.MSG_CONNECT, msg.type)
        self.assertEqual(4+2+20, msg.annotations_size)
        self.assertEqual(5, msg.data_size)

        hdr = Message(Pyro4.message.MSG_RESULT, b"", self.ser.serializer_id, 0, 0).to_bytes()[:24]
        msg = Message.from_header(hdr)
        self.assertEqual(Pyro4.message.MSG_RESULT, msg.type)
        self.assertEqual(4+2+20, msg.annotations_size)
        self.assertEqual(0, msg.data_size)

        hdr = Message(Pyro4.message.MSG_RESULT, b"hello", 12345, 60006, 30003).to_bytes()[:24]
        msg = Message.from_header(hdr)
        self.assertEqual(Pyro4.message.MSG_RESULT, msg.type)
        self.assertEqual(60006, msg.flags)
        self.assertEqual(5, msg.data_size)
        self.assertEqual(12345, msg.serializer_id)
        self.assertEqual(30003, msg.seq)

        msg = Message(255, b"", self.ser.serializer_id, 0, 255).to_bytes()
        self.assertEqual(50, len(msg))
        msg = Message(1, b"", self.ser.serializer_id, 0, 255).to_bytes()
        self.assertEqual(50, len(msg))
        msg = Message(1, b"", self.ser.serializer_id, flags=253, seq=254).to_bytes()
        self.assertEqual(50, len(msg))

        # compression is a job of the code supplying the data, so the messagefactory should leave it untouched
        data = b"x"*1000
        msg = Message(Pyro4.message.MSG_INVOKE, data, self.ser.serializer_id, 0, 0).to_bytes()
        msg2 = Message(Pyro4.message.MSG_INVOKE, data, self.ser.serializer_id, Pyro4.message.FLAGS_COMPRESSED, 0).to_bytes()
        self.assertEqual(len(msg), len(msg2))

    def testMessageHeaderDatasize(self):
        msg = Message(Pyro4.message.MSG_RESULT, b"hello", 12345, 60006, 30003)
        msg.data_size = 0x12345678   # hack it to a large value to see if it comes back ok
        hdr = msg.to_bytes()[:24]
        msg = Message.from_header(hdr)
        self.assertEqual(Pyro4.message.MSG_RESULT, msg.type)
        self.assertEqual(60006, msg.flags)
        self.assertEqual(0x12345678, msg.data_size)
        self.assertEqual(12345, msg.serializer_id)
        self.assertEqual(30003, msg.seq)

    def testAnnotations(self):
        annotations = { "TEST": b"abcde" }
        msg = Message(Pyro4.message.MSG_CONNECT, b"hello", self.ser.serializer_id, 0, 0, annotations)
        data = msg.to_bytes()
        annotations_size = 4+2+20 + 4+2+5
        self.assertEqual(msg.header_size + 5 + annotations_size, len(data))
        self.assertEqual(annotations_size, msg.annotations_size)
        self.assertEqual(2, len(msg.annotations))
        self.assertEqual(b"abcde", msg.annotations["TEST"])
        mac = pyrohmac(b"hello", annotations)
        self.assertEqual(mac, msg.annotations["HMAC"])

    def testAnnotationsIdLength4(self):
        try:
            msg = Message(Pyro4.message.MSG_CONNECT, b"hello", self.ser.serializer_id, 0, 0, { "TOOLONG": b"abcde" })
            data = msg.to_bytes()
            self.fail("should fail, too long")
        except Pyro4.errors.ProtocolError:
            pass
        try:
            msg = Message(Pyro4.message.MSG_CONNECT, b"hello", self.ser.serializer_id, 0, 0, { "QQ": b"abcde" })
            data = msg.to_bytes()
            self.fail("should fail, too short")
        except Pyro4.errors.ProtocolError:
            pass


    def testRecvAnnotations(self):
        annotations = { "TEST": b"abcde" }
        msg = Message(Pyro4.message.MSG_CONNECT, b"hello", self.ser.serializer_id, 0, 0, annotations)
        c = ConnectionMock()
        c.send(msg.to_bytes())
        msg = Message.recv(c)
        self.assertEqual(0, len(c.received))
        self.assertEqual(5, msg.data_size)
        self.assertEqual(b"hello", msg.data)
        self.assertEqual(b"abcde", msg.annotations["TEST"])
        self.assertTrue("HMAC" in msg.annotations)

    def testProtocolVersion(self):
        version = Pyro4.constants.PROTOCOL_VERSION
        Pyro4.constants.PROTOCOL_VERSION = 0     # fake invalid protocol version number
        msg = Message(Pyro4.message.MSG_RESULT, b"", self.ser.serializer_id, 0, 1).to_bytes()
        Pyro4.constants.PROTOCOL_VERSION = version
        self.assertRaises(Pyro4.errors.ProtocolError, Message.from_header, msg)

    def testHmac(self):
        try:
            hk = Pyro4.config.HMAC_KEY
            Pyro4.config.HMAC_KEY = b"test key"
            data = Message(Pyro4.message.MSG_RESULT, b"test", 42, 0, 1).to_bytes()
            c = ConnectionMock(data)
        finally:
            Pyro4.config.HMAC_KEY = hk
        # test checking of different hmacs
        try:
            Message.recv(c)
            self.fail("crash expected")
        except Pyro4.errors.SecurityError as x:
            self.assertTrue("hmac" in str(x))
        c = ConnectionMock(data)
        # test that it works again when resetting the key
        try:
            hk = Pyro4.config.HMAC_KEY
            Pyro4.config.HMAC_KEY = b"test key"
            Message.recv(c)
        finally:
            Pyro4.config.HMAC_KEY = hk
        c = ConnectionMock(data)
        # test that it doesn't work when no key is set
        try:
            hk = Pyro4.config.HMAC_KEY
            Pyro4.config.HMAC_KEY = b""
            Message.recv(c)
            self.fail("crash expected")
        except Pyro4.errors.SecurityError as x:
            self.assertTrue("hmac key config" in str(x))
        finally:
            Pyro4.config.HMAC_KEY = hk


    def testChecksum(self):
        msg = Message(Pyro4.message.MSG_RESULT, b"test", 42, 0, 1)
        c = ConnectionMock()
        c.send(msg.to_bytes())
        # corrupt the checksum bytes
        data = c.received
        data = data[:msg.header_size-2] + b'\x00\x00' + data[msg.header_size:]
        c = ConnectionMock(data)
        try:
            Message.recv(c)
            self.fail("crash expected")
        except Pyro4.errors.ProtocolError as x:
            self.assertTrue("checksum" in str(x))


class MessageTestsNoHmac(unittest.TestCase):
    def testRecvNoAnnotations(self):
        msg = Message(Pyro4.message.MSG_CONNECT, b"hello", 42, 0, 0)
        c = ConnectionMock()
        c.send(msg.to_bytes())
        msg = Message.recv(c)
        self.assertEqual(0, len(c.received))
        self.assertEqual(5, msg.data_size)
        self.assertEqual(b"hello", msg.data)
        self.assertEqual(0, msg.annotations_size)
        self.assertEqual(0, len(msg.annotations))


if __name__ == "__main__":
    unittest.main()
