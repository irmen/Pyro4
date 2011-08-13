from __future__ import print_function
import Pyro4
import sys
import time

if sys.version_info<(3,0):
	input=raw_input

host=input("enter the hostname of the itunescontroller: ")
itunes=Pyro4.Proxy("PYRO:itunescontroller@{0}:39001".format(host))

print("setting Playlist 'Music'...")
itunes.playlist("Music")
itunes.play()
print("Current song:", itunes.currentsong())
time.sleep(6)

print("setting Playlist 'itunes DJ'...")
itunes.playlist("itunes DJ")
itunes.play()
print("Current song:", itunes.currentsong())
time.sleep(6)

print("next song...")
itunes.next()
print("Current song:", itunes.currentsong())
time.sleep(6)

print("stop.")
itunes.stop()

