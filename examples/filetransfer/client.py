from __future__ import print_function
import time
import threading
import sys
import socket
import zlib
import Pyro4
import serpent

if sys.version_info < (3, 0):
    input = raw_input


def regular_pyro(uri):
    blobsize = 10*1024*1024
    num_blobs = 10
    total_size = 0
    start = time.time()
    name = threading.currentThread().name
    with Pyro4.core.Proxy(uri) as p:
        for _ in range(num_blobs):
            print("thread {0} getting a blob using regular Pyro call...".format(name))
            data = p.get_with_pyro(blobsize)
            data = serpent.tobytes(data)   # in case of serpent encoded bytes
            total_size += len(data)
    assert total_size == blobsize*num_blobs
    duration = time.time() - start
    print("thread {0} done, {1:.2f} Mb/sec.".format(name, total_size/1024.0/1024.0/duration))


def via_iterator(uri):
    blobsize = 10*1024*1024
    num_blobs = 10
    total_size = 0
    start = time.time()
    name = threading.currentThread().name
    with Pyro4.core.Proxy(uri) as p:
        for _ in range(num_blobs):
            print("thread {0} getting a blob using remote iterators...".format(name))
            for chunk in p.iterator(blobsize):
                chunk = serpent.tobytes(chunk)   # in case of serpent encoded bytes
                total_size += len(chunk)
    assert total_size == blobsize*num_blobs
    duration = time.time() - start
    print("thread {0} done, {1:.2f} Mb/sec.".format(name, total_size/1024.0/1024.0/duration))


def via_annotation_stream(uri):
    name = threading.currentThread().name
    start = time.time()
    total_size = 0
    print("thread {0} downloading via annotation stream...".format(name))
    with Pyro4.core.Proxy(uri) as p:
        perform_checksum = False
        for progress, checksum in p.annotation_stream(perform_checksum):
            chunk = Pyro4.current_context.response_annotations["FDAT"]
            if perform_checksum and zlib.crc32(chunk) != checksum:
                raise ValueError("checksum error")
            total_size += len(chunk)
            assert progress == total_size
            Pyro4.current_context.response_annotations.clear()  # clean them up once we're done with them
    duration = time.time() - start
    print("thread {0} done, {1:.2f} Mb/sec.".format(name, total_size/1024.0/1024.0/duration))


def raw_socket(uri):
    blobsize = 40*1024*1024
    num_blobs = 10
    total_size = 0
    name = threading.currentThread().name
    with Pyro4.core.Proxy(uri) as p:
        print("thread {0} preparing {1} blobs of size {2} Mb".format(name, num_blobs, blobsize/1024.0/1024.0))
        blobs = {}
        for _ in range(num_blobs):
            file_id, blob_address = p.prepare_file_blob(blobsize)
            blobs[file_id] = blob_address

        start = time.time()
        for file_id in blobs:
            print("thread {0} retrieving blob using raw socket...".format(name))
            blob_address = blobs[file_id]
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(tuple(blob_address))
            sock.sendall(file_id.encode())
            size = 0
            chunk = "dummy"
            while chunk:
                chunk = sock.recv(60000)
                size += len(chunk)
            sock.close()
            assert size == blobsize
            total_size += size
        duration = time.time() - start
        assert total_size == blobsize * num_blobs
        print("thread {0} done, {1:.2f} Mb/sec.".format(name, total_size/1024.0/1024.0/duration))


if __name__ == "__main__":
    uri = input("Uri of filetransfer server? ").strip()
    print("\n\n**** regular pyro calls ****\n")
    t1 = threading.Thread(target=regular_pyro, args=(uri, ))
    t2 = threading.Thread(target=regular_pyro, args=(uri, ))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    input("enter to continue:")
    print("\n\n**** transfer via iterators ****\n")
    t1 = threading.Thread(target=via_iterator, args=(uri, ))
    t2 = threading.Thread(target=via_iterator, args=(uri, ))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    input("enter to continue:")
    print("\n\n**** transfer via annotation stream ****\n")
    t1 = threading.Thread(target=via_annotation_stream, args=(uri, ))
    t2 = threading.Thread(target=via_annotation_stream, args=(uri, ))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    input("enter to continue:")
    print("\n\n**** raw socket transfers ****\n")
    t1 = threading.Thread(target=raw_socket, args=(uri, ))
    t2 = threading.Thread(target=raw_socket, args=(uri, ))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    input("enter to exit:")
