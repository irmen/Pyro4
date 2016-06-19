This is an example that more or less presents an online multiplayer game.
The game is a robot destruction derby.
It is played on a grid. There are some obstructing walls on the grid that
hurt when you collide into them. If you collide into another robot, the
other robot takes damage. All robots start with a certain amount of health.
If it reaches zero, the robot dies.  The last man standing wins!

Before starting the gameserver, you need to start a nameserver,
if you want to connect remotely to the game server! If you don't
have a nameserver running, you can still launch the gameserver but
you won't be able to connect to it with the Pyro clients.

You can click a button to add a couple of robots that are controlled
by the server itself. But it is more interesting to actually connect
remote robots to the server! Use client.py for that (provide a name
and a robot type). The client supports a few robot types that have
different behaviors. The robot behavior is controlled by the client!
The server only handles game mechanics.

In the game server, the Pyro calls are handled by a daemon thread.
The GUI updates are done by Tkinter using after() calls.

The most interesting parts of this example are perhaps these:
 - server uses identical code to work with local and remote robots
   (it did require a few minor tweaks to work around serialization requirements)
 - Pyro used together with an interactive GUI application (Tkinter)
 - game state handled by the server, influenced by the clients (robot behavior)
 - this example uses Pyro's AutoProxy feature. Registering
   observers and getting a robot object back is done via proxies
   automatically because those are Pyro objects.
