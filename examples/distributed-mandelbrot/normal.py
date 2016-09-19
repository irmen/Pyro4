# ascii animation of zooming a mandelbrot fractal,  z=z^2+c
from __future__ import print_function, division
import os
import time
import platform
from server import Mandelbrot

res_x = 100
res_y = 40


def screen(start, width):
    mandel = Mandelbrot()
    dr = width / res_x
    di = dr*(res_x/res_y)
    di *= 0.8   # aspect ratio correction
    lines = mandel.calc_lines(start, res_x, dr, di, 0, res_y)
    return "\n".join(x[1] for x in lines)


def cls():
    if platform.platform().startswith("Windows"):
        os.system("cls")
    else:
        print(chr(27)+"[2J"+chr(27)+"[1;1H", end="")  # ansi clear screen
    

def zoom():
    start = -2.0-1.0j
    width = 3.0
    duration = 30.0
    wallclock_start = time.time()
    frames = 0
    cls()
    print("This is a mandelbrot zoom animation running without Pyro, in a single Python process.")
    time.sleep(2)
    while True:
        time_passed = time.time() - wallclock_start
        if time_passed >= duration:
            break
        actual_width = width * (1-time_passed/duration/1.1)
        actual_start = start + (0.06-0.002j)*time_passed
        frame = screen(actual_start, actual_width)
        cls()
        fps = frames/time_passed if time_passed > 0 else 0
        print("%.1f FPS time=%.2f width=%.2f" % (fps, time_passed, actual_width))
        print(frame)
        frames += 1
    print("Final FPS: %.2f" % fps)


if __name__ == "__main__":
    zoom()
