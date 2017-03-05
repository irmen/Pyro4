from __future__ import print_function
import select
import tempfile
import uuid
import io
import os
import threading
import zlib
import Pyro4
import Pyro4.core
import Pyro4.socketutil


datafiles = {}      # temporary files
datablobs = {}      # in-memory


@Pyro4.expose
class FileServer(object):
    def get_with_pyro(self, size):
        print("sending %d bytes" % size)
        data = b"x" * size
        return data

    def iterator(self, size):
        chunksize = size//100
        print("sending %d bytes via iterator, chunks of %d bytes" % (size, chunksize))
        data = b"x" * size
        i = 0
        while i < size:
            yield data[i:i+chunksize]
            i += chunksize

    def annotation_stream(self, with_checksum=False):
        # create a large temporary file
        f = tempfile.TemporaryFile()
        for _ in range(5000):
            f.write(b"1234567890!" * 1000)
        filesize = f.tell()
        f.seek(os.SEEK_SET, 0)
        # return the file data via annotation stream (remote iterator)
        print("transmitting file via annotations stream (%d bytes)..." % filesize)
        with f:
            annotation_size = 65000  # leave some room for Pyro's internal annotation chunks
            while True:
                chunk = f.read(annotation_size)
                if not chunk:
                    break
                # store the file data chunk in the FDAT response annotation,
                # and return the current file position and checksum (if asked).
                Pyro4.current_context.response_annotations = {"FDAT": chunk}
                yield f.tell(), zlib.crc32(chunk) if with_checksum else 0

    def prepare_file_blob(self, size):
        print("preparing file-based blob of size %d" % size)
        file_id = str(uuid.uuid4())
        f = tempfile.TemporaryFile()
        chunk = b"x" * 100000
        for _ in range(size//100000):
            f.write(chunk)
        f.write(b"x"*(size % 100000))
        f.flush()
        f.seek(0, io.SEEK_SET)
        # os.fsync(f)
        datafiles[file_id] = f
        blobsock_info = self._pyroDaemon.blobsocket.getsockname()  # return the port info for the blob socket as well
        return file_id, blobsock_info

    def prepare_memory_blob(self, size):
        print("preparing in-memory blob of size %d" % size)
        file_id = str(uuid.uuid4())
        datablobs[file_id] = b"x" * size
        blobsock_info = self._pyroDaemon.blobsocket.getsockname()  # return the port info for the blob socket as well
        return file_id, blobsock_info


class FileServerDaemon(Pyro4.core.Daemon):
    def __init__(self, host=None, port=0):
        super(FileServerDaemon, self).__init__(host, port)
        host, _ = self.transportServer.sock.getsockname()
        self.blobsocket = Pyro4.socketutil.createSocket(bind=(host, 0), timeout=Pyro4.config.COMMTIMEOUT, nodelay=False)
        print("Blob socket available on:", self.blobsocket.getsockname())
        
    def close(self):
        self.blobsocket.close()
        super(FileServerDaemon, self).close()

    def requestLoop(self, loopCondition=lambda: True):
        while loopCondition:
            rs = [self.blobsocket]
            rs.extend(self.sockets)
            rs, _, _ = select.select(rs, [], [], 3)
            daemon_events = []
            for sock in rs:
                if sock in self.sockets:
                    daemon_events.append(sock)
                elif sock is self.blobsocket:
                    self.handle_blob_connect(sock)
            if daemon_events:
                self.events(daemon_events)

    def handle_blob_connect(self, sock):
        csock, caddr = sock.accept()
        thread = threading.Thread(target=self.blob_client, args=(csock,))
        thread.daemon = True
        thread.start()

    def blob_client(self, csock):
        file_id = Pyro4.socketutil.receiveData(csock, 36).decode()
        print("{0} requesting file id {1}".format(csock.getpeername(), file_id))
        is_file, data = self.find_blob_data(file_id)
        if is_file:
            if hasattr(os, "sendfile"):
                print("...from file using sendfile()")
                out_fn = csock.fileno()
                in_fn = data.fileno()
                sent = 1
                offset = 0
                while sent:
                    sent = os.sendfile(out_fn, in_fn, offset, 512000)
                    offset += sent
            else:
                print("...from file using plain old read(); your os doesn't have sendfile()")
                while True:
                    chunk = data.read(512000)
                    if not chunk:
                        break
                    csock.sendall(chunk)
        else:
            print("...from memory")
            csock.sendall(data)
        csock.close()

    def find_blob_data(self, file_id):
        if file_id in datablobs:
            return False, datablobs.pop(file_id)
        elif file_id in datafiles:
            return True, datafiles.pop(file_id)
        else:
            raise KeyError("no data for given id")


with FileServerDaemon(host=Pyro4.socketutil.getIpAddress("")) as daemon:
    uri = daemon.register(FileServer, "example.filetransfer")
    print("Filetransfer server URI:", uri)
    daemon.requestLoop()
