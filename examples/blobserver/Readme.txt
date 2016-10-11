Pyro isn't ideal for transfering large amounts of data or lots of binary data.
In some situations it's okay such as sending the occasional PNG file of a forum
profile portrait, but generally for intensive file transfer it's better to use
one of the established protocols that are optimized for this (rsync, ftp, http,
etcetera).

That being said you could opt for a hybrid approach: use Pyro for regular remote
calls and provide a second network interface for the large data transfers, that will
avoid the Pyro protocol and serialization overhead and size limitations (2 Gb).

This example does exactly that: it runs a Pyro server that also serves a raw socket
interface over which the large binary data files are sent. They're prepared in
the regular Pyro server code and identified via a guid. The client then obtains
the binary data by first sending the guid and then receiving the data over the
raw socket connection in a streaming manner.

If the binary data is very large it is better to store it first as temporary files on
the disk in the server, otherwise you risk running out of system memory which will crash
your python process.  The client code as given selects the file storage approach.
It will then stream the data from the server, thereby avoiding the need to allocate
a huge amount of memory.  (ofcourse if you need to process all of the data at once
you end up collecting it together anyway, but you'll be able to do this yourself in
the most efficient way suitable for your application)

As the data transfer averages at the end will show, the raw socket transfer is
much faster than transferring the data via regular Pyro calls, and it will use
a lot less memory and CPU as well. The speed does depend a bit on the performance
and fragmentation of your hard drive where the temporary files are created.
Also if your OS supports the os.sendfile() function (usually on Linux, BSD and OSX,
but not Windows) you'll benefit even more from optimized data transfer.


Note:
Performance of the download via iterator is almost identical to the normal transfer
speed of regular python/pyro calls.


Note:
the only "security" on the raw socket interface is that you have to know
the id of a data file that you want to obtain. It's not advised to use this
example as-is in a production environment.

For more benchmark numbers regarding large binary data transfer using Pyro, see
the 'hugetransfer' example.
