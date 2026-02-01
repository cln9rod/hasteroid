import random
import pygame
from circleshape import CircleShape
from constants import ASTEROID_MIN_RADIUS, LINE_WIDTH
from core.pool import PooledSprite

class Asteroid(CircleShape, PooledSprite):
    containers = ()
    
    def __init__(self, x: float, y: float, radius: float):
        CircleShape.__init__(self, x, y, radius)
        self.radius = radius
        self._alive = True
        self._scanned = False
        self._full_scanned = False
        self.debris_data = None
        self.norad_id = None
    
    def reset(self, x: float, y: float, radius: float = None, **kwargs) -> "Asteroid":
        self.position.x = x
        self.position.y = y
        self.velocity.x = 0
        self.velocity.y = 0
        if radius is not None:
            self.radius = radius
        self._alive = True
        self._scanned = False
        self._full_scanned = False
        self.debris_data = kwargs.get("debris_data")
        self.norad_id = kwargs.get("norad_id")
        
        for container in Asteroid.containers:
            container.add(self)
        return self
    
    @classmethod
    def acquire(cls, x: float, y: float, radius: float, **kwargs) -> "Asteroid":
        if cls._pool:
            asteroid = cls._pool.acquire()
            asteroid.reset(x, y, radius, **kwargs)
            return asteroid
        else:
            return cls(x, y, radius)
    
    def draw(self, screen) -> None:
        if not self._alive:
            return
        if self._full_scanned:
            color = (0, 255, 0)
        elif self._scanned:
            color = (0, 200, 255)
        else:
            color = "white"
        pygame.draw.circle(screen, color, self.position, self.radius, LINE_WIDTH)
        if self._scanned:
            pygame.draw.circle(screen, color, self.position, 3)
    
    def update(self, dt: float) -> None:
        if self._alive:
            self.position += self.velocity * dt
    
    def split(self) -> list:
        self._alive = False
        if self.radius <= ASTEROID_MIN_RADIUS:
            if self._pool:
                self.release()
            else:
                self.kill()
            return []
        
        pos_x, pos_y = self.position.x, self.position.y
        old_velocity = self.velocity.copy()
        new_radius = self.radius - ASTEROID_MIN_RADIUS
        angle = random.uniform(20, 50)
        saved_debris = self.debris_data
        saved_norad = self.norad_id
        
        if self._pool:
            self.release()
        else:
            self.kill()
        
        children = []
        for angle_offset in (angle, -angle):
            child = Asteroid.acquire(pos_x, pos_y, new_radius, 
                                    debris_data=saved_debris, 
                                    norad_id=saved_norad)
            child.velocity = old_velocity.rotate(angle_offset) * 1.2
            children.append(child)
        return children
    
    def release(self) -> None:
        self._alive = False
        self.kill()
        if self._pool:
            self._pool.release(self)