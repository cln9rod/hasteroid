"""Shot/projectile entity with object pooling."""
import pygame
from circleshape import CircleShape
from constants import SHOT_RADIUS, LINE_WIDTH
from core.pool import PooledSprite

__all__ = ["Shot"]


class Shot(CircleShape, PooledSprite):
    """Player projectile with pooling support."""
    
    containers = ()
    
    def __init__(self, x: float, y: float):
        CircleShape.__init__(self, x, y, SHOT_RADIUS)
        self._alive = True
        self._lifetime = 0.0
        self.max_lifetime = 2.0  # Auto-despawn after 2s
    
    def reset(self, x: float, y: float, **kwargs) -> "Shot":
        """Reinitialize for pool reuse."""
        self.position.x = x
        self.position.y = y
        self.velocity.x = 0
        self.velocity.y = 0
        self._alive = True
        self._lifetime = 0.0
        
        # Re-add to containers
        for container in self.containers:
            container.add(self)
        
        return self
    
    @classmethod
    def acquire(cls, x: float, y: float) -> "Shot":
        """Get from pool or create new."""
        if cls._pool:
            shot = cls._pool.acquire()
            shot.reset(x, y)
            return shot
        else:
            return cls(x, y)
    
    def draw(self, screen) -> None:
        if self._alive:
            pygame.draw.circle(screen, "white", self.position, self.radius, LINE_WIDTH)
    
    def update(self, dt: float) -> None:
        if not self._alive:
            return
            
        self.position += self.velocity * dt
        self._lifetime += dt
        
        # Auto-release after lifetime expires
        if self._lifetime >= self.max_lifetime:
            self.release()
    
    def release(self) -> None:
        """Return to pool."""
        self._alive = False
        self.kill()
        if self._pool:
            self._pool.release(self)
