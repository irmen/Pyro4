"""
The pyro wire protocol message.

Pyro - Python Remote Objects.  Copyright by Irmen de Jong (irmen@razorvine.net).
"""

from __future__ import with_statement
import hashlib
import hmac
import struct
import logging

import Pyro4
from Pyro4 import constants, errors

__all__ = ["Message", "PingMessage"]

log = logging.getLogger("Pyro4.message")

MSG_CONNECT = 1
MSG_CONNECTOK = 2
MSG_CONNECTFAIL = 3
MSG_INVOKE = 4
MSG_RESULT = 5
MSG_PING = 6
FLAGS_EXCEPTION = 1<<0
FLAGS_COMPRESSED = 1<<1
FLAGS_ONEWAY = 1<<2
FLAGS_HMAC = 1<<3
FLAGS_BATCH = 1<<4
SERIALIZER_SERPENT = 1
SERIALIZER_JSON = 2
SERIALIZER_MARSHAL = 3
SERIALIZER_PICKLE = 4


class Message(object):
    """
    Pyro write protocol message.
    Note that it doesn't deal with the actual payload,
    (De) serialization and handling of the data is done elsewhere.
    """
    __slots__ = ["type", "flags", "seq", "data", "datasize", "serializer_id", "hmac"]
    # The header format is:
    #   4   id ('PYRO')
    #   2   version
    #   2   message type
    #   2   flags
    #   2   sequence number
    #   4   data length
    #   2   data serialization format (serializer id)
    #   2   annotations length (currently unused)
    #   2   (reserved)
    #   2   checksum
    #   20  hmac (or all 0)
    # note: the sequencenumber is used to check if response messages correspond to the
    # actual request message. This prevents the situation where Pyro would perhaps return
    # the response data from another remote call (which would not result in an error otherwise!)
    # This could happen for instance if the socket data stream gets out of sync, perhaps due To
    # some form of signal that interrupts I/O.
    # The header checksum is a simple sum of the header fields to make reasonably sure
    # that we are dealing with an actual correct PYRO protocol header and not some random
    # data that happens to start with the 'PYRO' protocol identifier.
    header_format = '!4sHHHHiHHHH20s'
    header_size = struct.calcsize(header_format)
    checksum_magic = 0x34E9

    def __init__(self, msgType, databytes, serializer_id, flags, seq):
        self.type = msgType
        self.flags = flags
        self.seq = seq
        self.data = databytes
        self.datasize = len(self.data)
        self.serializer_id = serializer_id
        if 0 < Pyro4.config.MAX_MESSAGE_SIZE < self.datasize:
            raise errors.ProtocolError("max message size exceeded (%d where max=%d)" % (self.datasize, Pyro4.config.MAX_MESSAGE_SIZE))
        if Pyro4.config.HMAC_KEY:
            self.flags |= FLAGS_HMAC
            self.hmac = hmac.new(Pyro4.config.HMAC_KEY, databytes, digestmod=hashlib.sha1).digest()
        else:
            self.hmac = b"\0"*20

    def __repr__(self):
        return "<%s.%s at %x, type=%d flags=%d seq=%d datasize=%d>" % (self.__module__, self.__class__.__name__, id(self), self.type, self.flags, self.seq, self.datasize)

    def to_bytes(self):
        """creates a byte stream containing the header followed by the data"""
        return self.__header_bytes() + self.data

    def __header_bytes(self):
        checksum = (self.type+constants.PROTOCOL_VERSION+self.datasize+self.serializer_id+self.flags+self.seq+self.checksum_magic)&0xffff
        return struct.pack(self.header_format, b"PYRO", constants.PROTOCOL_VERSION, self.type, self.flags, self.seq, len(self.data), self.serializer_id, 0, 0, checksum, self.hmac)

    @classmethod
    def from_header(cls, headerData):
        """Parses a message header. Does not yet process the message data."""
        if not headerData or len(headerData)!=cls.header_size:
            raise errors.ProtocolError("header data size mismatch")
        tag, ver, msgType, flags, seq, dataLen, serializer_id, annotationsLen, _, headerchecksum, datahmac = struct.unpack(cls.header_format, headerData)
        if tag!=b"PYRO" or ver!=constants.PROTOCOL_VERSION:
            raise errors.ProtocolError("invalid data or unsupported protocol version")
        if headerchecksum!=(msgType+ver+dataLen+flags+serializer_id+seq+cls.checksum_magic)&0xffff:
            raise errors.ProtocolError("header checksum mismatch")
        msg = Message(msgType, b"", serializer_id, flags, seq)
        msg.datasize = dataLen
        msg.hmac = datahmac
        return msg

    def send(self, connection):
        """send the message as bytes over the connection"""
        connection.send(self.__header_bytes())
        connection.send(self.data)

    @classmethod
    def recv(cls, connection, requiredMsgTypes=None):
        """Receives a pyro message from a given connection. Accepts the given message types (None=any, or pass a sequence)."""
        headerdata = connection.recv(cls.header_size)
        msg = cls.from_header(headerdata)
        if 0 < Pyro4.config.MAX_MESSAGE_SIZE < msg.datasize:
            errorMsg = "max message size exceeded (%d where max=%d)" % (msg.datasize, Pyro4.config.MAX_MESSAGE_SIZE)
            log.error("connection "+str(connection)+": "+errorMsg)
            connection.close()   # close the socket because at this point we can't return the correct sequence number for returning an error message
            raise errors.ProtocolError(errorMsg)
        if requiredMsgTypes and msg.type not in requiredMsgTypes:
            err = "invalid msg type %d received" % msg.type
            log.error(err)
            raise errors.ProtocolError(err)
        msg.data = connection.recv(msg.datasize)
        local_hmac_set = Pyro4.config.HMAC_KEY is not None and len(Pyro4.config.HMAC_KEY) > 0
        if msg.flags&FLAGS_HMAC and local_hmac_set:
            if msg.hmac != hmac.new(Pyro4.config.HMAC_KEY, msg.data, digestmod=hashlib.sha1).digest():
                raise errors.SecurityError("message hmac mismatch")
        elif msg.flags&FLAGS_HMAC != local_hmac_set:
            # Message contains hmac and local HMAC_KEY not set, or vice versa. This is not allowed.
            err = "hmac key config not symmetric"
            log.warning(err)
            raise errors.SecurityError(err)
        return msg
