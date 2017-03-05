from __future__ import print_function
import Pyro4
import Pyro4.core
import Pyro4.naming
import tempfile
import zlib
import os


class ChunkStreamer(object):
    annotation_size = 65000     # leave some room for Pyro's internal annotation chunks

    @Pyro4.expose
    def download(self, with_checksum=False):
        with self.create_download_file() as f:
            print("transmitting file...")
            while True:
                chunk = f.read(self.annotation_size)
                if not chunk:
                    break
                Pyro4.current_context._chunk = chunk  # XXX todo set via context.response_annotations!?
                checksum = zlib.crc32(chunk) if with_checksum else 0
                yield f.tell(), checksum
        print("download finished!")

    def create_download_file(self):
        print("creating temporary file that will be downloaded...")
        f = tempfile.TemporaryFile()
        for _ in range(50000):
            f.write(b"1234567890!"*1000)
        print("filesize:", f.tell())
        f.seek(os.SEEK_SET, 0)
        return f


class MyDaemon(Pyro4.core.Daemon):
    def annotations(self):
        if hasattr(Pyro4.current_context, "_chunk"):
            return {"FDAT": Pyro4.current_context._chunk}  # XXX todo set via context.response_annotations!?
        return {}


daemon = MyDaemon()
uri = daemon.register(ChunkStreamer, None)
ns = Pyro4.naming.locateNS()
ns.register("example.annotationsstreamer", uri)
print("server ready.")
daemon.requestLoop()
