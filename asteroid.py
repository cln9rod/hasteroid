"""
Asteroid entity with object pooling support.
Note: Renamed from asteorid.py (typo fix)
"""
import random
import pygame
from circleshape import CircleShape
from constants import ASTEROID_MIN_RADIUS, LINE_WIDTH
from core.pool import PooledSprite

__all__ = ["Asteroid"]


class Asteroid(CircleShape, PooledSprite):
    """
    Asteroid with pooling support.
    Use Asteroid.acquire() instead of Asteroid() when pool is set.
    """
    
    containers = ()  # Set by main.py
    
    def __init__(self, x: float, y: float, radius: float):
        CircleShape.__init__(self, x, y, radius)
        self.radius = radius
        self._alive = True
        
        # Future: debris metadata
        self.debris_data = None
        self.norad_id = None
    
    def reset(self, x: float, y: float, radius: float = None, **kwargs) -> "Asteroid":
        """Reinitialize for pool reuse."""
        self.position.x = x
        self.position.y = y
        self.velocity.x = 0
        self.velocity.y = 0
        if radius is not None:
            self.radius = radius
        self._alive = True
        self.debris_data = kwargs.get("debris_data")
        self.norad_id = kwargs.get("norad_id")
        
        # Re-add to sprite groups (explicit class reference)
        for container in Asteroid.containers:
            container.add(self)
        
        return self
    
    @classmethod
    def acquire(cls, x: float, y: float, radius: float, **kwargs) -> "Asteroid":
        """Get from pool or create new."""
        if cls._pool:
            asteroid = cls._pool.acquire()
            asteroid.reset(x, y, radius, **kwargs)
            return asteroid
        else:
            return cls(x, y, radius)
    
    def draw(self, screen) -> None:
        if self._alive:
            pygame.draw.circle(screen, "white", self.position, self.radius, LINE_WIDTH)
    
    def update(self, dt: float) -> None:
        if self._alive:
            self.position += self.velocity * dt
    
    def split(self) -> list:
        """
        Split into smaller asteroids. Returns list of new asteroids.
        Uses pool if available.
        """
        self._alive = False
        
        if self.radius <= ASTEROID_MIN_RADIUS:
            if self._pool:
                self.release()
            else:
                self.kill()
            return []
        
        # Save state BEFORE releasing (pool might reuse this object)
        pos_x, pos_y = self.position.x, self.position.y
        old_velocity = self.velocity.copy()
        new_radius = self.radius - ASTEROID_MIN_RADIUS
        angle = random.uniform(20, 50)
        
        # Now safe to release
        if self._pool:
            self.release()
        else:
            self.kill()
        
        # Spawn two smaller asteroids
        children = []
        for angle_offset in (angle, -angle):
            child = Asteroid.acquire(pos_x, pos_y, new_radius)
            child.velocity = old_velocity.rotate(angle_offset) * 1.2
            children.append(child)
        
        return children
    
    def release(self) -> None:
        """Return to pool."""
        self._alive = False
        self.kill()  # Remove from groups
        if self._pool:
            self._pool.release(self)