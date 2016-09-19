This is an ascii-animation of zooming in on the Mandelbrot fractal set (z=z^2+c).
The animation runs at 100x40 resolution so make sure your console window is large enough.


The 'normal' code simply runs the calculation in a single Python process.
It calculates every frame of the animation in one go and prints it to the screen.
On my computer it runs at about 3 frames per second using CPython 3.5 and at about 6 fps
when using Pypy 5.4. This is in a windows console and will only use one CPU core.


The 'client_asciizoom' program uses Pyro to offload the calculations to whatever
mandelbrot server processes that are available.
It discovers the available servers by using the metadata in the name sever.
To distribute the load evenly, it hands out the calculation of a single line in the
frame to each server in a cyclic sequence. It uses Pyro batch calls to cluster these
calls again to avoid having to do hundreds of remote calls per second, instead it
will just call every server once per frame. The calls will return a bunch of resulting lines
that are merged into the final animation frame, which is then printed to the screen.

On my machine with 4 cpu cores, when starting 4 mandelbrot servers using Pypy 5.4,
the animation now runs at about 15 fps instead. It uses all 4 cores of the machine
at about 80% load. I guess the rest is I/O time spent printing the frames to the console.



The graphics version is interesting too because it shows a nice picture at the end :)
The single core normal version takes 43 seconds on my machine (20 with pypy). The Pyro
version only takes 12 seconds, when using 4 mandelbrot calculation servers.
(It only takes 6 seconds when those servers are being run on Pypy!)

It submits a single line to a mandelbrot server per call.
