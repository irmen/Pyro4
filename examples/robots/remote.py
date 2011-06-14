from __future__ import print_function
import random
import Pyro4

class GameServer(object):
    def __init__(self, engine):
        self.engine=engine
    def register(self, name, observer):
        robot=self.engine.signup_robot(name, observer)
        self._pyroDaemon.register(robot)    # make the robot a pyro object
        return robot

class RemoteBot(object):
    def __init__(self, robot, engine):
        self.robot=robot
        self.engine=engine
    def get_data(self):
        return self.robot.serializable()
    def change_direction(self, direction):
        self.robot.dx,self.robot.dy = direction
    def emote(self, text):
        self.robot.emote(text)
    def terminate(self):
        self.engine.remove_robot(self.robot)

class LocalGameObserver(object):
    def __init__(self, name):
        self.name=name
        self.robot=None
        self._pyroOneway=set()  # remote observers have this
    def world_update(self, iteration, world, robotdata):
        # change directions randomly
        if random.random()>0.8:
            if random.random()>=0.5:
                dx,dy=random.randint(-1,1),0
            else:
                dx,dy=0,random.randint(-1,1)
            self.robot.change_direction((dx,dy))
    def start(self):
        self.robot.emote("Here we go!")
    def victory(self):
        print("[%s] I WON!!!" % self.name)
    def death(self, killer):
        if killer:
            print("[%s] I DIED (%s did it)" % (self.name, killer.name))
        else:
            print("[%s] I DIED" % self.name)

class GameObserver(object):
    def world_update(self, iteration, world, robotdata):
        pass
    def start(self):
        print("Battle starts!")
    def victory(self):
        print("I WON!!!")
    def death(self, killer):
        print("I DIED")
        if killer:
            print("%s KILLED ME :(" % killer.name)
