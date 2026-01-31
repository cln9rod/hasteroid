"""
Object Pool for entity reuse.
Eliminates GC spikes from constant asteroid creation/destruction.
"""
from typing import Callable, Generic, TypeVar, Optional
from collections import deque

__all__ = ["ObjectPool", "PooledSprite"]

T = TypeVar("T")


class ObjectPool(Generic[T]):
    """
    Generic object pool with lazy growth.
    
    Usage:
        pool = ObjectPool(lambda: Asteroid(0, 0, 20), initial=50)
        asteroid = pool.acquire()
        asteroid.reset(x, y, radius)  # Reinitialize
        ...
        pool.release(asteroid)  # Return to pool instead of kill()
    """
    
    __slots__ = ("_factory", "_pool", "_active", "_max_size")
    
    def __init__(
        self, 
        factory: Callable[[], T], 
        initial: int = 50,
        max_size: int = 500
    ):
        """
        Args:
            factory: Callable that creates a new instance
            initial: Pre-allocate this many objects
            max_size: Cap to prevent memory blowup
        """
        self._factory = factory
        self._pool: deque[T] = deque(maxlen=max_size)
        self._active: set[int] = set()
        self._max_size = max_size
        
        # Pre-warm pool
        for _ in range(initial):
            obj = factory()
            self._pool.append(obj)
    
    def acquire(self) -> T:
        """Get an object from pool or create new if empty."""
        if self._pool:
            obj = self._pool.pop()
        else:
            obj = self._factory()
        
        self._active.add(id(obj))
        return obj
    
    def release(self, obj: T) -> None:
        """Return object to pool for reuse."""
        oid = id(obj)
        if oid in self._active:
            self._active.discard(oid)
            
            # Reset sprite state if it's a pygame sprite
            if hasattr(obj, "groups"):
                for group in list(obj.groups()):
                    group.remove(obj)
            
            if len(self._pool) < self._max_size:
                self._pool.append(obj)
    
    def release_all(self, objects) -> None:
        """Batch release multiple objects."""
        for obj in objects:
            self.release(obj)
    
    @property
    def available(self) -> int:
        """Objects ready in pool."""
        return len(self._pool)
    
    @property  
    def active(self) -> int:
        """Objects currently in use."""
        return len(self._active)
    
    @property
    def total(self) -> int:
        """Total managed objects."""
        return self.available + self.active


class PooledSprite:
    """
    Mixin for sprites that use object pooling.
    Adds reset() method and pool reference.
    """
    
    _pool: Optional["ObjectPool"] = None
    
    @classmethod
    def set_pool(cls, pool: "ObjectPool") -> None:
        """Assign the pool for this sprite class."""
        cls._pool = pool
    
    def reset(self, x: float, y: float, **kwargs) -> "PooledSprite":
        """
        Reinitialize sprite for reuse. Override in subclass.
        Must return self for chaining.
        """
        self.position.x = x
        self.position.y = y
        self.velocity.x = 0
        self.velocity.y = 0
        return self
    
    def release(self) -> None:
        """Return to pool instead of kill()."""
        if self._pool:
            # Remove from all groups first
            if hasattr(self, "kill"):
                self.kill()
            self._pool.release(self)
        elif hasattr(self, "kill"):
            self.kill()


# Convenience function for batch operations
def acquire_many(pool: ObjectPool, count: int) -> list:
    """Acquire multiple objects at once."""
    return [pool.acquire() for _ in range(count)]
