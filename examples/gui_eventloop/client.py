from __future__ import print_function
import sys
import time

import Pyro4


print("First make sure one of the gui servers is running.")
print("Enter the object uri that was printed:")
if sys.version_info < (3, 0):
    uri = raw_input()
else:
    uri = input()
uri = uri.strip()
guiserver = Pyro4.Proxy(uri)

guiserver.message("Hello there!")
time.sleep(0.5)
guiserver.message("How's it going?")
time.sleep(2)

for i in range(20):
    guiserver.message("Counting {0}".format(i))

guiserver.message("now calling the sleep method with 5 seconds")
guiserver.sleep(5)
print("done!")
