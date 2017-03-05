from __future__ import print_function
import time
import zlib
import Pyro4.core


svr = Pyro4.core.Proxy("PYRONAME:example.annotationsstreamer")

start = time.time()
total_size = 0
perform_checksum = False
print("downloading...")
for progress, checksum in svr.download(perform_checksum):
    chunk = Pyro4.current_context.response_annotations["FDAT"]
    if perform_checksum and zlib.crc32(chunk) != checksum:
        raise ValueError("checksum error")
    total_size += len(chunk)
    assert progress == total_size

Pyro4.current_context.response_annotations.clear()   # we're done with them
duration = time.time()-start
print("downloaded: ", total_size)
print("download finished in {:.2f} seconds; {:f} Mb/sec".format(duration, total_size/1024.0/1024.0/duration))
