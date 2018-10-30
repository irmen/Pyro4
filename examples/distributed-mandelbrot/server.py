from __future__ import print_function, division
import sys
import Pyro4


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
            if abs(z) > 2:
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
        iters = 0
        for iters in range(self.maxiters+1):
            if abs(z) > 2:
                break
            z = z*z + c
        if iters >= self.maxiters:
            return 0, 0, 0
        r = (iters+32) % 255
        g = iters % 255
        b = (iters+40) % 255
        return int(r), int(g), int(b)


if __name__ == "__main__":
    # spawn a Pyro daemon process
    # (can't use threads, because of the GIL)
    if len(sys.argv) != 2:
        raise SystemExit("give argument: server_id number")

    server_id = int(sys.argv[1])
    with Pyro4.Daemon() as d:
        with Pyro4.locateNS() as ns:
            mandel_server = d.register(Mandelbrot)
            mandel_color_server = d.register(MandelbrotColorPixels)
            ns.register("mandelbrot_"+str(server_id), mandel_server, safe=True, metadata={"class:mandelbrot_calc"})
            ns.register("mandelbrot_color_"+str(server_id), mandel_color_server, safe=True, metadata={"class:mandelbrot_calc_color"})
        print("Mandelbrot calculation server #{} ready.".format(server_id))
        d.requestLoop()
