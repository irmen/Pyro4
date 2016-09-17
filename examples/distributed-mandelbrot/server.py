from __future__ import print_function, division
import uuid
import Pyro4


@Pyro4.expose
class Mandelbrot(object):
    maxiter = 250

    def calc_line(self, start, res_x, ii, dr, line_nr):
        line = ""
        z = start + complex(0, ii)
        for r in range(res_x):
            z += complex(dr, 0)
            iters = self.iterations(z)
            line += " " if iters >= self.maxiter else chr(iters % 64 + 32)
        return line_nr, line

    def calc_lines(self, start, res_x, dr, di, start_line_nr, num_lines):
        lines = []
        for i in range(num_lines):
            line = ""
            for r in range(res_x):
                z = start + complex(r*dr, i*di)
                iters = self.iterations(z)
                line += " " if iters >= self.maxiter else chr(iters % 64 + 32)
            lines.append((i+start_line_nr, line))
        return lines

    def iterations(self, z):
        c = z
        for n in range(self.maxiter):
            if abs(z) > 2:
                return n
            z = z*z + c
        return self.maxiter


if __name__ == "__main__":
    with Pyro4.Daemon() as d:
        uri = d.register(Mandelbrot)
        with Pyro4.locateNS() as ns:
            name = "mandel.calc_"+str(uuid.uuid4())
            ns.register(name, uri, safe=True, metadata={"class:mandelbrot_calc"})
        print("Mandelbrot calculation server ready:", name)
        d.requestLoop()
