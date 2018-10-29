These examples are about calculating the Mandelbrot fractal set (z=z^2+c).

First, a few notes:
- The ascii animation runs at 100x40 resolution so make sure your console window is large enough.
- The maximum iteration count is set to a quite high value to make the calculcations
  more time consuming. If you want you can change both maxiter values in server.py down
  to something more reasonable such as 256.
- try using Pypy instead of CPython to improve the speed dramatically


The 'normal' code simply runs the calculation in a single Python process.
It calculates every frame of the animation in one go and prints it to the screen.


The 'client_asciizoom' program uses Pyro to offload the calculations to whatever
mandelbrot server processes that are available.
It discovers the available servers by using the metadata in the name server.
To distribute the load evenly, it hands out the calculation of a single line in the
frame to each server in a cyclic sequence. It uses Pyro batch calls to cluster these
calls again to avoid having to do hundreds of remote calls per second, instead it
will just call every server once per frame. The calls will return a bunch of resulting lines
that are merged into the final animation frame, which is then printed to the screen.


The graphics version is interesting too because it actually creates a nice picture!
