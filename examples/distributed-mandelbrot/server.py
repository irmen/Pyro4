from __future__ import print_function, division
import math
import Pyro4


# A note about the abs(z) calls below not using abs(z),
# but instead squaring the imaginary and real components itself:
#
# This is because using abs(z) triggers a performance issue on pypy on windows,
# where it is much slower than it could have been. This seems to be an issue
# with the hypot() function in Microsoft's 32 bits runtime library.
# See bug report https://bitbucket.org/pypy/pypy/issues/2401
# The problem doesn't occur on other Pypy implementations.


@Pyro4.expose
class Mandelbrot(object):
    maxiters = 500

    def calc_line(self, start, res_x, ii, dr, line_nr):
        line = ""
        z = start + complex(0, ii)
        for r in range(res_x):
            z += complex(dr, 0)
            iters = self.iterations(z)
            line += " " if iters >= self.maxiters else chr(iters % 64 + 32)
        return line_nr, line

    def calc_lines(self, start, res_x, dr, di, start_line_nr, num_lines):
        lines = []
        for i in range(num_lines):
            line = ""
            for r in range(res_x):
                z = start + complex(r*dr, i*di)
                iters = self.iterations(z)
                line += " " if iters >= self.maxiters else chr(iters % 64 + 32)
            lines.append((i+start_line_nr, line))
        return lines

    def iterations(self, z):
        c = z
        for n in range(self.maxiters):
            if z.real*z.real + z.imag*z.imag > 4:      # abs(z) > 2
                return n
            z = z*z + c
        return self.maxiters


@Pyro4.expose
class MandelbrotColorPixels(object):
    maxiters = 500
    def calc_photoimage_line(self, y, res_x, res_y):
        line = []
        for x in range(res_x):
            rgb = self.mandel_iterate(x, y, res_x, res_y)
            line.append(rgb)
        # tailored response for easy drawing into a tkinter PhotoImage:
        return y, "{"+" ".join("#%02x%02x%02x" % rgb for rgb in line)+"}"

    def mandel_iterate(self, x, y, res_x, res_y):
        zr = (x/res_x - 0.5) * 1 - 0.3
        zi = (y/res_y - 0.5) * 1 - 0.9
        zi *= res_y/res_x  # aspect correction
        z = complex(zr, zi)
        c = z
        for iters in range(self.maxiters+1):
            if z.real*z.real + z.imag*z.imag > 4:      # abs(z) > 2
                break
            z = z*z + c
        if iters >= self.maxiters:
            return 0, 0, 0
        abs_z = math.sqrt(z.real*z.real + z.imag*z.imag)     # abs(z)
        r = (iters+32) % 255
        g = (iters - math.log(abs_z)) % 255
        b = (abs_z*iters) % 255
        return int(r), int(g), int(b)


if __name__ == "__main__":
    with Pyro4.Daemon() as d:
        uri_1 = d.register(Mandelbrot)
        uri_2 = d.register(MandelbrotColorPixels)
        with Pyro4.locateNS() as ns:
            ns.register(Mandelbrot._pyroId, uri_1, safe=True, metadata={"class:mandelbrot_calc"})
            ns.register(MandelbrotColorPixels._pyroId, uri_2, safe=True, metadata={"class:mandelbrot_calc_color"})
        print("Mandelbrot calculation server ready.")
        d.requestLoop()
