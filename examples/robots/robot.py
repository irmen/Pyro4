from __future__ import print_function
import sys
import array

class Wall(object):
    """an obstructing static wall"""
    def __init__(self, position):
        self.x,self.y = position
    def serializable(self):
        return self

class Robot(object):
    """represents a robot moving on a grid."""
    def __init__(self, name, grid_dimensions, position, direction=(0,0), strength=5):
        self.name = name
        self.x, self.y = position
        self.dx, self.dy = direction
        self.gridw, self.gridh = grid_dimensions
        self.strength = strength
    def __str__(self):
        return "ROBOT '%s'; pos(%d,%d); dir(%d,%d); strength %d" %(self.name, self.x, self.y, self.dx, self.dy, self.strength)
    def serializable(self):
        if type(self) is Robot:
            return self
        else:
            return Robot(self.name,(self.gridw,self.gridh),(self.x,self.y),(self.dx,self.dy),self.strength)
    def move(self, world=None):
        # minmax to avoid moving off the sides
        x=min(self.gridw-1, max(0,self.x+self.dx))
        y=min(self.gridh-1, max(0,self.y+self.dy))
        if x==self.x and y==self.y:
            return
        if world and self.__process_collision(x,y,world):
            return
        self.x,self.y = x,y
    def __process_collision(self, newx, newy, world):
        other=world.collides(newx,newy)
        if not other:
            return False  # we didn't hit anything
        self.dx,self.dy = 0,0   # come to a standstill when we hit something
        if isinstance(other,Wall):
            self.strength-=1  # hit wall, decrease our strength
            if self.strength<=0:
                print("[server] %s killed himself!" % self.name)
                world.remove(self)
                self.died(None,world)
        else:
            other.strength-=1  # hit other robot, decrease other robot's strength
            self.collision(other)
            if other.strength<=0:
                world.remove(other)
                other.died(self, world)
                print("[server] %s killed %s!" % (self.name, other.name))
        return True
    def killed(self, victim, world):
        """you can override this to react on kills"""
        pass
    def collision(self, other):
        """you can override this to react on collisions between bots"""
        pass
    def emote(self, text):
        """you can override this"""
        print("[server] %s says: '%s'" % (self.name, text))

class World(object):
    """the world the robots move in (Cartesian grid)"""
    def __init__(self, width, height):
        self.width=width
        self.height=height
        self.all=[]
        self.robots=[]
    def add_wall(self, wall):
        self.all.append(wall)
    def add_robot(self, bot):
        self.all.append(bot)
        self.robots.append(bot)
    def collides(self, x, y):
        for obj in self.all:
            if obj.x==x and obj.y==y:
                return obj
        return None
    def remove(self, obj):
        self.all.remove(obj)
        self.robots.remove(obj)
    def dump(self):
        line=' '*self.width
        if sys.version_info>=(3,0):
            line=bytes(line, "ASCII")
        grid=[array.array('b', line) for y in range(self.height)]
        for obj in self.all:
            grid[obj.y][obj.x]=ord('R') if isinstance(obj, Robot) else ord('#')
        return grid
    def __getstate__(self):
        all=[o.serializable() for o in self.all]
        robots=[r.serializable() for r in self.robots]
        return (self.width,self.height,all,robots)
    def __setstate__(self, args):
        self.width,self.height,self.all,self.robots=args
