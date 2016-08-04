"""
This example shows a Tkinter GUI application that uses event loop callbacks
to integrate Pyro's event loop into the Tkinter GUI mainloop.

No threads are used. The Pyro event callback is called every so often
to check if there are Pyro events to handle, and handles them synchronously.
"""
import time
import select
import Pyro4

try:
    from tkinter import *
    import tkinter.simpledialog as simpledialog
except ImportError:
    from Tkinter import *
    import tkSimpleDialog as simpledialog

# Set the Pyro servertype to the multiplexing select-based server that doesn't
# use a threadpool to service method calls. This way the method calls are
# handled inside the main thread as well.
Pyro4.config.SERVERTYPE = "multiplex"

# The frequency with which the GUI loop calls the Pyro event handler.
PYRO_EVENTLOOP_HZ = 50


class PyroGUI(object):
    """
    The Tkinter GUI application that also listens for Pyro calls.
    """

    def __init__(self):
        self.tk = Tk()
        self.tk.wm_title("Pyro in a Tkinter GUI eventloop - without threads")
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

    def install_pyro_event_callback(self, daemon):
        """
        Add a callback to the tkinter event loop that is invoked every so often.
        The callback checks the Pyro sockets for activity and dispatches to the
        daemon's event process method if needed.
        """

        def pyro_event():
            while True:
                # for as long as the pyro socket triggers, dispatch events
                s, _, _ = select.select(daemon.sockets, [], [], 0.01)
                if s:
                    daemon.events(s)
                else:
                    # no more events, stop the loop, we'll get called again soon anyway
                    break
            self.tk.after(1000 // PYRO_EVENTLOOP_HZ, pyro_event)

        self.tk.after(1000 // PYRO_EVENTLOOP_HZ, pyro_event)

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
    """

    def __init__(self, gui):
        self.gui = gui

    def message(self, messagetext):
        # Add the message to the screen.
        # Note that you can't do anything that requires gui interaction
        # (such as popping a dialog box asking for user input),
        # because the gui (tkinter) is busy processing this pyro call.
        # It can't do two things at the same time when embedded this way.
        # If you do something in this method call that takes a long time
        # to process, the GUI is frozen during that time (because no GUI update
        # events are handled while this callback is active).
        self.gui.add_message("from Pyro: " + messagetext)

    def sleep(self, duration):
        # Note that you can't perform blocking stuff at all because the method
        # call is running in the gui mainloop thread and will freeze the GUI.
        # Try it - you will see the first message but everything locks up until
        # the sleep returns and the method call ends
        self.gui.add_message("from Pyro: sleeping {0} seconds...".format(duration))
        self.gui.tk.update()
        time.sleep(duration)
        self.gui.add_message("from Pyro: woke up!")


def main():
    gui = PyroGUI()

    # create a pyro daemon with object
    daemon = Pyro4.Daemon()
    obj = MessagePrinter(gui)
    uri = daemon.register(obj, "pyrogui.message")

    gui.add_message("Pyro server started. Not using threads.")
    gui.add_message("Use the command line client to send messages.")
    urimsg = "Pyro object uri = {0}".format(uri)
    gui.add_message(urimsg)
    print(urimsg)

    # add a Pyro event callback to the gui's mainloop
    gui.install_pyro_event_callback(daemon)
    # enter the mainloop
    gui.mainloop()


if __name__ == "__main__":
    main()
