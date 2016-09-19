# mandelbrot fractal,  z=z^2+c
from __future__ import print_function, division
import time
try:
    import tkinter
except ImportError:
    import Tkinter as tkinter
import Pyro4

res_x = 1000
res_y = 800


class MandelWindow(object):
    def __init__(self):
        self.root = tkinter.Tk()
        self.root.title("Mandelbrot (Pyro multi core version)")
        canvas = tkinter.Canvas(self.root, width=res_x, height=res_y, bg="#000000")
        canvas.pack()
        self.img = tkinter.PhotoImage(width=res_x, height=res_y)
        canvas.create_image((res_x/2, res_y/2), image=self.img, state="normal")
        with Pyro4.locateNS() as ns:
            mandels = ns.list(metadata_any={"class:mandelbrot_calc_color"})
            mandels = list(mandels.items())
        print("{0} mandelbrot calculation servers found.".format(len(mandels)))
        if not mandels:
            raise ValueError("launch at least one mandelbrot calculation server before starting this")
        self.mandels = [Pyro4.async(Pyro4.Proxy(uri)) for _, uri in mandels]
        self.lines = list(reversed(range(res_y)))
        self.root.after(1000, self.draw_lines)
        tkinter.mainloop()

    def draw_lines(self):
        # start by putting each of the found servers to work on a single line,
        # the other lines will be done in turn when the results come back.
        self.start_time = time.time()
        for _ in range(len(self.mandels)):
            self.calc_new_line()

    def calc_new_line(self):
        y = self.lines.pop()
        server = self.mandels[y % len(self.mandels)]  # round robin server selection
        server.calc_photoimage_line(y, res_x, res_y).then(self.process_result)

    def process_result(self, result):
        y, pixeldata = result
        self.img.put(pixeldata, (0, y))
        if self.lines:
            self.calc_new_line()
        else:
            duration = time.time() - self.start_time
            print("Calculation took: %d seconds" % duration)


if __name__ == "__main__":
    window = MandelWindow()
