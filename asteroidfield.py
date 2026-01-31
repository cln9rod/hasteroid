"""Asteroid spawner with pool integration."""
import pygame
import random
from asteroid import Asteroid
from constants import (
    ASTEROID_MAX_RADIUS,
    ASTEROID_MIN_RADIUS,
    ASTEROID_KINDS,
    ASTEROID_SPAWN_RATE_SECONDS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)


class AsteroidField(pygame.sprite.Sprite):
    """Spawns asteroids from screen edges at intervals."""
    
    edges = [
        # [direction_vector, position_lambda]
        [
            pygame.Vector2(1, 0),  # Moving right
            lambda y: pygame.Vector2(-ASTEROID_MAX_RADIUS, y * SCREEN_HEIGHT),
        ],
        [
            pygame.Vector2(-1, 0),  # Moving left
            lambda y: pygame.Vector2(SCREEN_WIDTH + ASTEROID_MAX_RADIUS, y * SCREEN_HEIGHT),
        ],
        [
            pygame.Vector2(0, 1),  # Moving down
            lambda x: pygame.Vector2(x * SCREEN_WIDTH, -ASTEROID_MAX_RADIUS),
        ],
        [
            pygame.Vector2(0, -1),  # Moving up
            lambda x: pygame.Vector2(x * SCREEN_WIDTH, SCREEN_HEIGHT + ASTEROID_MAX_RADIUS),
        ],
    ]

    def __init__(self):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.spawn_timer = 0.0

    def spawn(self, radius: float, position: pygame.Vector2, velocity: pygame.Vector2):
        """Spawn asteroid using pool if available."""
        asteroid = Asteroid.acquire(position.x, position.y, radius)
        asteroid.velocity = velocity

    def update(self, dt: float):
        self.spawn_timer += dt
        
        if self.spawn_timer > ASTEROID_SPAWN_RATE_SECONDS:
            self.spawn_timer = 0

            # Random edge spawn
            edge = random.choice(self.edges)
            speed = random.randint(40, 100)
            velocity = edge[0] * speed
            velocity = velocity.rotate(random.randint(-30, 30))
            position = edge[1](random.uniform(0, 1))
            kind = random.randint(1, ASTEROID_KINDS)
            
            self.spawn(ASTEROID_MIN_RADIUS * kind, position, velocity)
