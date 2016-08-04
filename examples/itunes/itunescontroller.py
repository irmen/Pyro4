from __future__ import print_function
import subprocess
import socket

import Pyro4


#  You can get a lot more info about scripting iTunes here:
#  http://dougscripts.com/itunes/

@Pyro4.expose
class ITunes(object):
    def __init__(self):
        # start itunes
        subprocess.call(["osascript", "-e", "tell application \"iTunes\" to player state"])

    def play(self):
        # continue play
        subprocess.call(["osascript", "-e", "tell application \"iTunes\" to play"])

    def pause(self):
        # pause play
        subprocess.call(["osascript", "-e", "tell application \"iTunes\" to pause"])

    def stop(self):
        # stop playing
        subprocess.call(["osascript", "-e", "tell application \"iTunes\" to stop"])

    def next(self):
        # next song in list
        subprocess.call(["osascript", "-e", "tell application \"iTunes\" to next track"])

    def previous(self):
        # previous song in list
        subprocess.call(["osascript", "-e", "tell application \"iTunes\" to previous track"])

    def playlist(self, listname):
        # start playling a defined play list
        subprocess.call(["osascript", "-e", "tell application \"iTunes\" to play playlist \"{0}\"".format(listname)])

    def currentsong(self):
        # return title and artist of current song
        return subprocess.check_output(["osascript", "-e", "tell application \"iTunes\"",
                                        "-e", "set thisTitle to name of current track",
                                        "-e", "set thisArtist to artist of current track",
                                        "-e", "set output to thisTitle & \" - \" & thisArtist",
                                        "-e", "end tell"]).strip()


print("starting...")
itunes = ITunes()
daemon = Pyro4.Daemon(host=socket.gethostname(), port=39001)
uri = daemon.register(itunes, "itunescontroller")
print("iTunes controller started, uri =", uri)
daemon.requestLoop()
