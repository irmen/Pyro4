from __future__ import with_statement
import random
import time
import robot
import remote
try:
    from tkinter import *
except ImportError:
    from Tkinter import *
import Pyro4
from Pyro4 import threadutil

class VisibleRobot(robot.Robot):
    """represents a robot that is visible on the screen."""
    def __init__(self, name, position, direction, grid, color='red'):
        super(VisibleRobot,self).__init__(name, (grid.width, grid.height), position, direction)
        self.grid=grid
        x=self.x*grid.squaresize
        y=self.y*grid.squaresize
        self.tkid=grid.create_rectangle(x,y,x+grid.squaresize,y+grid.squaresize,fill=color,outline='black')
        self.text_tkid=None
    def popuptext(self, text, sticky=False):
        if self.text_tkid:
            self.grid.delete(self.text_tkid)
        self.text_tkid=self.grid.create_text(self.x*self.grid.squaresize,self.y*self.grid.squaresize,text=text,anchor=CENTER,fill='red')
        self.text_timer=time.time()
        if not sticky:
            self.grid.after(1000, self.__removetext, self.text_tkid)
    def delete_from_grid(self):
        self.grid.delete(self.tkid)
        if self.text_tkid:
            self.grid.delete(self.text_tkid)
    def __removetext(self, textid):
        self.grid.delete(textid)
        if textid==self.text_tkid:
            self.text_tkid=None
    def move(self, world=None):
        super(VisibleRobot,self).move(world)
        x=self.x*self.grid.squaresize
        y=self.y*self.grid.squaresize
        self.grid.coords(self.tkid, x,y,x+self.grid.squaresize, y+self.grid.squaresize)
        if self.text_tkid:
            # also move the popup text
            self.grid.coords(self.text_tkid, self.x*self.grid.squaresize,self.y*self.grid.squaresize)
    def died(self, killer, world):
        self.popuptext("ARGH I died")
        if killer:
            killer=killer.serializable()
        self.observer.death(killer=killer)
        self.grid.after(800, lambda: self.grid.delete(self.tkid))
    def collision(self, other):
        self.popuptext("Bam!")
        other.popuptext("ouch")
    def emote(self,text):
        self.popuptext(text, False)

class RobotGrid(Canvas):
    def __init__(self, parent, width, height, squaresize=20):
        self.squaresize=squaresize
        self.width=width
        self.height=height
        pixwidth=width*self.squaresize
        pixheight=height*self.squaresize
        Canvas.__init__(self, parent, width=pixwidth, height=pixheight, background='#e0e0e0')
        self.xview_moveto(0)
        self.yview_moveto(0)
        for x in range(width):
            self.create_line(x*self.squaresize,0,x*self.squaresize,pixheight, fill='#d0d0d0')
        for y in range(height):
            self.create_line(0,y*self.squaresize,pixwidth,y*self.squaresize,fill='#d0d0d0')
    def draw_wall(self, wall, color='navy'):
        x=wall.x*self.squaresize
        y=wall.y*self.squaresize
        self.create_rectangle(x,y,x+self.squaresize,y+self.squaresize,fill=color,outline=color)


class GameEngine(object):
    def __init__(self, gui, world):
        self.gui=gui
        self.grid=gui.grid
        self.world=world
        self.build_walls()
        self.gui.buttonhandler=self
        self.survivor=None
        self.open_for_signups=True
        self.iteration=0
    def button_clicked(self, button):
        if button=="add_bot" and self.open_for_signups:
            for i in range(5):
                name="local_bot_%d" % self.gui.listbox.size()
                gameobserver=remote.LocalGameObserver(name)
                robot=self.signup_robot(name, gameobserver)
                gameobserver.robot=robot
        elif button=="start_round":
            self.open_for_signups=False
            if self.survivor:
                self.survivor.delete_from_grid()
            self.gui.enable_buttons(False)
            self.start_round()
    def start_round(self):
        self.gui.statuslabel.config(text="new round!")
        print("WORLD:")
        for line in self.world.dump():
            print(line.tostring())
        print("NUMBER OF ROBOTS: %d" % len(self.world.robots))
        txtid=self.grid.create_text(20,20,text="GO!",font=("Courier",120,"bold"),anchor=NW,fill='purple')
        self.grid.after(1500,lambda:self.grid.delete(txtid))
        self.grid.after(2000,self.update)
        self.grid.after(2000,self.notify_start)
        self.iteration=0
    def notify_start(self):
        for robot in self.world.robots:
            robot.observer.start()
    def notify_worldupdate(self):
        self.iteration+=1
        for robot in self.world.robots:
            robotdata=robot.serializable()
            robot.observer.world_update(self.iteration, self.world, robotdata)
    def notify_winner(self, winner):
        winner.observer.victory()
    def update(self):
        for robot in self.world.robots:
            robot.move(self.world)
        self.notify_worldupdate()
        self.gui.statuslabel.config(text="survivors: %d" % len(self.world.robots))
        if len(self.world.robots)<1:
            print("[server] No results.")
            self.round_ends()
        elif len(self.world.robots)==1:
            self.survivor=self.world.robots[0]
            self.world.remove(self.survivor)
            self.survivor.popuptext("I WIN! HURRAH!", True)
            print("[server] %s wins!" % self.survivor.name)
            self.gui.statuslabel.config(text="winner: %s" % self.survivor.name)
            self.notify_winner(self.survivor)
            self.round_ends()
        else:
            self.gui.tk.after(40, self.update)
    def round_ends(self):
        self.gui.listbox.delete(0,END)
        self.gui.enable_buttons(True)
        self.open_for_signups=True
    def build_walls(self):
        wall_offset=4
        wall_size=10
        for x in range(wall_size):
            wall=robot.Wall((x+wall_offset,wall_offset))
            self.world.add_wall(wall)
            self.grid.draw_wall(wall)
            wall=robot.Wall((x+wall_offset,wall_size+wall_offset+1))
            self.world.add_wall(wall)
            self.grid.draw_wall(wall)
            wall=robot.Wall((wall_offset,x+wall_offset+1))
            self.world.add_wall(wall)
            self.grid.draw_wall(wall)
            wall=robot.Wall((wall_size+wall_offset+2,x+wall_offset+1))
            self.world.add_wall(wall)
            self.grid.draw_wall(wall)
    def signup_robot(self, name, observer=None):
        if not self.open_for_signups:
            raise RuntimeError("signups are closed, try again later")
        for r in self.world.robots:
            if r.name==name:
                raise ValueError("that name is already taken")
        colorint=random.randint(0,0xFFFFFF)
        color='#%06x' % colorint
        inversecolor='black'
        self.gui.listbox.insert(END,name)
        self.gui.listbox.itemconfig(END,bg=color, fg=inversecolor)
        while True:
            x=random.randint(0,self.grid.width-1)
            y=random.randint(int(self.grid.height*0),self.grid.height-1)
            if not self.world.collides(x,y):
                break
        r=VisibleRobot(name,(x,y),(0,0), self.grid, color=color)
        self.world.add_robot(r)
        r.observer=observer
        observer._pyroOneway.add("world_update")
        r.popuptext(name)
        return remote.RemoteBot(r, self)
    def remove_robot(self, robot):
        robot.delete_from_grid()
        self.world.remove(robot)
        # listnames=list(self.gui.listbox.get(0,END))
        # listnames.remove(robot.name)
        # self.gui.listbox.delete(0,END)
        # self.gui.listbox.insert(END,*listnames)

class GUI(object):
    def __init__(self, width, height):
        self.tk=Tk()
        self.tk.wm_title("bot destruction derby")
        lframe=Frame(self.tk, borderwidth=3, relief="raised", padx=2, pady=2, background='#808080')
        self.grid=RobotGrid(lframe, width, height, squaresize=16)
        rframe=Frame(self.tk, padx=2, pady=2)
        rlabel=Label(rframe, text="Signups:")
        rlabel.pack(fill=X)
        self.listbox=Listbox(rframe, width=15, height=20, font=(None,8))
        self.listbox.pack()
        self.addrobotbutton=Button(rframe, text="Add 5 local bots", command=lambda: self.buttonhandler.button_clicked("add_bot"))
        self.addrobotbutton.pack()
        self.startbutton=Button(rframe, text="Start round!", command=lambda: self.buttonhandler.button_clicked("start_round"))
        self.startbutton.pack()
        self.statuslabel=Label(rframe, width=20)
        self.statuslabel.pack(side=BOTTOM)
        self.grid.pack()
        lframe.pack(side=LEFT)
        rframe.pack(side=RIGHT, fill=BOTH)
        self.buttonhandler=None
    def enable_buttons(self, enabled=True):
        if enabled:
            self.addrobotbutton.config(state=NORMAL)
            self.startbutton.config(state=NORMAL)
        else:
            self.addrobotbutton.config(state=DISABLED)
            self.startbutton.config(state=DISABLED)

class PyroDaemonThread(threadutil.Thread):
    def __init__(self, engine):
        threadutil.Thread.__init__(self)
        self.pyroserver=remote.GameServer(engine)
        self.pyrodaemon=Pyro4.Daemon()
        self.ns=Pyro4.locateNS()
        self.setDaemon(True)
    def run(self):
        with self.pyrodaemon:
            with self.ns:
                uri=self.pyrodaemon.register(self.pyroserver)
                self.ns.register("example.robotserver", uri)
                print("Pyro server registered on %s" % self.pyrodaemon.locationStr)
                self.pyrodaemon.requestLoop()

def main():
    width=25
    height=25
    gui=GUI(width,height)
    world=robot.World(width, height)
    engine=GameEngine(gui, world)
    try:
        PyroDaemonThread(engine).start()
    except Pyro4.errors.NamingError:
        print("Can't find the Pyro Nameserver. Running without remote connections.")
    gui.tk.mainloop()

if __name__=="__main__":
    main()
