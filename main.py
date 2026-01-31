"""
AstroTag - Main game loop with optimized collision detection.
Uses spatial hashing for O(n) average collision checks.
"""
import sys
import pygame

from constants import SCREEN_HEIGHT, SCREEN_WIDTH, ASTEROID_MAX_RADIUS
from core import SpatialHash, ObjectPool
from player import Player
from asteroid import Asteroid
from asteroidfield import AsteroidField
from shot import Shot
from logger import log_state, log_event


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("AstroTag")
    clock = pygame.time.Clock()
    
    # Sprite groups
    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    
    # Set sprite containers FIRST (before pools prewarm)
    Asteroid.containers = (asteroids, updatable, drawable)
    Player.containers = (updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers = (updatable, drawable, shots)
    
    # Spatial hash: cell size >= 2 * max entity radius
    spatial = SpatialHash(cell_size=ASTEROID_MAX_RADIUS * 2 + 32)
    
    # Object pools - preallocate to avoid runtime allocation
    asteroid_pool = ObjectPool(
        factory=lambda: Asteroid(0, 0, 20),
        initial=100,
        max_size=500
    )
    shot_pool = ObjectPool(
        factory=lambda: Shot(0, 0),
        initial=50,
        max_size=200
    )
    
    # Assign pools to classes
    Asteroid.set_pool(asteroid_pool)
    Shot.set_pool(shot_pool)
    
    # Create entities
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    asteroid_field = AsteroidField()
    
    dt = 0
    running = True
    
    # Performance tracking
    frame_count = 0
    collision_checks = 0
    
    while running:
        log_state()
        
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Update all entities
        dt = clock.tick(60) / 1000
        updatable.update(dt)
        
        # --- Optimized collision detection ---
        # Rebuild spatial hash (entities moved)
        spatial.clear()
        
        # Insert all collidables
        for asteroid in asteroids:
            spatial.insert(asteroid)
        for shot in shots:
            spatial.insert(shot)
        spatial.insert(player)
        
        # Check shot-asteroid collisions (O(n) average)
        collision_checks = 0
        shots_to_remove = []
        asteroids_to_split = []
        
        for shot in shots:
            # Only check nearby asteroids
            for asteroid in spatial.query(shot):
                if not isinstance(asteroid, Asteroid):
                    continue
                collision_checks += 1
                if shot.collides_with(asteroid):
                    log_event("asteroid_shot", norad_id=asteroid.norad_id)
                    shots_to_remove.append(shot)
                    asteroids_to_split.append(asteroid)
                    break  # Shot can only hit one asteroid
        
        # Check player-asteroid collision
        for asteroid in spatial.query(player):
            if not isinstance(asteroid, Asteroid):
                continue
            collision_checks += 1
            if asteroid.collides_with(player):
                log_event("player_hit")
                print("Game over!")
                running = False
                break
        
        # Process collisions (deferred to avoid mutation during iteration)
        for shot in shots_to_remove:
            shot.release()
        for asteroid in asteroids_to_split:
            asteroid.split()
        
        # --- Render ---
        screen.fill("black")
        for sprite in drawable:
            sprite.draw(screen)
        
        # Debug HUD (optional)
        if pygame.key.get_pressed()[pygame.K_F1]:
            _draw_debug_hud(screen, clock, spatial, asteroid_pool, shot_pool, collision_checks)
        
        pygame.display.flip()
        frame_count += 1
    
    pygame.quit()
    sys.exit()


def _draw_debug_hud(screen, clock, spatial, asteroid_pool, shot_pool, checks):
    """Performance overlay - press F1 to toggle."""
    font = pygame.font.Font(None, 24)
    lines = [
        f"FPS: {clock.get_fps():.1f}",
        f"Asteroids: {asteroid_pool.active} (pool: {asteroid_pool.available})",
        f"Shots: {shot_pool.active} (pool: {shot_pool.available})",
        f"Spatial cells: {spatial.cell_count}",
        f"Collision checks: {checks}",
    ]
    y = 10
    for line in lines:
        surf = font.render(line, True, (0, 255, 0))
        screen.blit(surf, (10, y))
        y += 20


if __name__ == "__main__":
    main()