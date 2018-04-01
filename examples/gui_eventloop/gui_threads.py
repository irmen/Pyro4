"""
This example shows a Tkinter GUI application that uses a worker thread to
run Pyro's event loop.

Usually, the GUI toolkit requires that GUI operations are done from within
the GUI thread. So, if Pyro interfaces with the GUI, it cannot do that
directly because the method calls are done from a different thread.
This means we need a layer between them, this example uses a Queue to
submit GUI operations to Tkinter's main loop.

For this example, the mainloop runs a callback function every so often
to check for new work in that Queue and will process it if the Pyro worker
thread has put something in it.
"""
import time
import threading
try:
    import queue
except ImportError:
    import Queue as queue
import Pyro4

try:
    from tkinter import *
    import tkinter.simpledialog as simpledialog
except ImportError:
    from Tkinter import *
    import tkSimpleDialog as simpledialog


# The frequency with which the GUI mainloop checks for work in the Pyro queue.
PYRO_QUEUE_HZ = 50


class PyroGUI(object):
    """
    The Tkinter GUI application that also listens for Pyro calls.
    """

    def __init__(self):
        self.pyro_queue = queue.Queue()
        self.tk = Tk()
        self.tk.wm_title("Pyro in a Tkinter GUI eventloop - with threads")
        self.tk.wm_geometry("500x500")
        buttonframe = Frame(self.tk)
        button = Button(buttonframe, text="Messagebox", command=self.button_msgbox_clicked)
        button.pack(side=LEFT)
        button = Button(buttonframe, text="Add some text", command=self.button_text_clicked)
        button.pack(side=LEFT)
        button = Button(buttonframe, text="Clear all text", command=self.button_clear_clicked)
        button.pack(side=LEFT)
        quitbutton = Button(buttonframe, text="Quit", command=self.tk.quit)
        quitbutton.pack(side=RIGHT)
        frame = Frame(self.tk, padx=2, pady=2)
        buttonframe.pack(fill=X)
        rlabel = Label(frame, text="Pyro server messages:")
        rlabel.pack(fill=X)
        self.msg = Message(frame, anchor=NW, width=500, aspect=80, background="white", relief="sunken")
        self.msg.pack(fill=BOTH, expand=1)
        frame.pack(fill=BOTH)
        self.serveroutput = []

    def install_pyro_queue_callback(self):
        """
        Add a callback to the tkinter event loop that is invoked every so often.
        The callback checks the Pyro work queue for work and processes it.
        """

        def check_pyro_queue():
            try:
                while True:
                    # get a work item from the queue (until it is empty)
                    workitem = self.pyro_queue.get_nowait()
                    # execute it in the gui's mainloop thread
                    workitem["callable"](*workitem["vargs"], **workitem["kwargs"])
            except queue.Empty:
                pass
            self.tk.after(1000 // PYRO_QUEUE_HZ, check_pyro_queue)

        self.tk.after(1000 // PYRO_QUEUE_HZ, check_pyro_queue)

    def mainloop(self):
        self.tk.mainloop()

    def button_msgbox_clicked(self):
        # this button event handler is here only to show that gui events are still processed normally
        number = simpledialog.askinteger("A normal popup", "Hi there enter a number", parent=self.tk)

    def button_clear_clicked(self):
        self.serveroutput = []
        self.msg.config(text="")

    def button_text_clicked(self):
        # add some random text to the message list
        self.add_message("The quick brown fox jumps over the lazy dog!")

    def add_message(self, message):
        message = "[{0}] {1}".format(time.strftime("%X"), message)
        self.serveroutput.append(message)
        self.serveroutput = self.serveroutput[-27:]
        self.msg.config(text="\n".join(self.serveroutput))


@Pyro4.expose
class MessagePrinter(object):
    """
    The Pyro object that interfaces with the GUI application.
    It uses a Queue to transfer GUI update calls to Tkinter's mainloop.
    """

    def __init__(self, gui):
        self.gui = gui

    def message(self, messagetext):
        # put a gui-update work item in the queue
        self.gui.pyro_queue.put({
            "callable": self.gui.add_message,
            "vargs": ("from Pyro: " + messagetext,),
            "kwargs": {}
        })

    def sleep(self, duration):
        # Note that you *can* perform blocking stuff now because the method
        # call is running in its own thread. It won't freeze the GUI anymore.
        # However you cannot do anything that requires GUI interaction because
        # that needs to go through the queue so the mainloop can pick that up.
        # (opening a dialog from this worker thread will still freeze the GUI)
        # But a simple sleep() call works fine and the GUI stays responsive.
        self.gui.pyro_queue.put({
            "callable": self.gui.add_message,
            "vargs": ("from Pyro: sleeping {0} seconds...".format(duration),),
            "kwargs": {}
        })
        time.sleep(duration)
        self.gui.pyro_queue.put({
            "callable": self.gui.add_message,
            "vargs": ("from Pyro: woke up!",),
            "kwargs": {}
        })


class PyroDaemon(threading.Thread):
    def __init__(self, gui):
        threading.Thread.__init__(self)
        self.gui = gui
        self.started = threading.Event()

    def run(self):
        daemon = Pyro4.Daemon()
        obj = MessagePrinter(self.gui)
        self.uri = daemon.register(obj, "pyrogui.message2")
        self.started.set()
        daemon.requestLoop()


def main():
    gui = PyroGUI()

    # create a pyro daemon with object, running in its own worker thread
    pyro_thread = PyroDaemon(gui)
    pyro_thread.setDaemon(True)
    pyro_thread.start()
    pyro_thread.started.wait()

    gui.add_message("Pyro server started. Using Pyro worker thread.")
    gui.add_message("Use the command line client to send messages.")
    urimsg = "Pyro object uri = {0}".format(pyro_thread.uri)
    gui.add_message(urimsg)
    print(urimsg)

    # add a Pyro event callback to the gui's mainloop
    gui.install_pyro_queue_callback()
    # enter the mainloop
    gui.mainloop()


if __name__ == "__main__":
    main()
