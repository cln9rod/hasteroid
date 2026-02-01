"""
AstroTag - Main game loop with CelesTrak debris integration.
Uses spatial hashing for O(n) average collision checks.
"""
import sys
import pygame

from constants import (
    SCREEN_HEIGHT, SCREEN_WIDTH, ASTEROID_MAX_RADIUS,
    SCAN_RANGE, SCAN_POINTS_QUICK, SCAN_POINTS_FULL, DESTROY_POINTS
)
from core import SpatialHash, ObjectPool
from crypto import GameSession
from celestrak import DebrisFetcher
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
    font = pygame.font.Font(None, 36)
    
    # Initialize debris fetcher (use mock=False for real API)
    print("[AstroTag] Initializing CelesTrak fetcher...")
    debris_fetcher = DebrisFetcher(use_mock=True)
    print(f"[AstroTag] Loaded {debris_fetcher.count} debris objects")
    
    # Sprite groups
    updatable = pygame.sprite.Group()
    drawable = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots = pygame.sprite.Group()
    
    Player.containers = (updatable, drawable)
    AsteroidField.containers = (updatable,)
    
    # Spatial hash
    spatial = SpatialHash(cell_size=ASTEROID_MAX_RADIUS * 2 + 32)
    
    # Object pools
    Asteroid.containers = ()
    Shot.containers = ()
    
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
    
    Asteroid.containers = (asteroids, updatable, drawable)
    Shot.containers = (updatable, drawable, shots)
    
    Asteroid.set_pool(asteroid_pool)
    Shot.set_pool(shot_pool)
    
    # Create entities (pass debris fetcher to field)
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    asteroid_field = AsteroidField(debris_fetcher)
    
    # Game state
    session = GameSession()
    
    dt = 0
    running = True
    
    while running:
        log_state()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        dt = clock.tick(60) / 1000
        updatable.update(dt)
        
        # Scan targeting
        keys = pygame.key.get_pressed()
        if keys[pygame.K_e]:
            nearest = _find_nearest_asteroid(player, asteroids, SCAN_RANGE)
            if nearest:
                player.set_scan_target(nearest)
        
        # Handle scan completion
        if player.last_scan_result:
            scan_type, asteroid = player.last_scan_result
            if scan_type == "full":
                session.add_score(SCAN_POINTS_FULL)
                session.record_scan("full", asteroid.norad_id)
                log_event("scan_full", norad_id=asteroid.norad_id, 
                         debris_name=asteroid.debris_data.get("name") if asteroid.debris_data else None)
            elif scan_type == "quick":
                session.add_score(SCAN_POINTS_QUICK)
                session.record_scan("quick", asteroid.norad_id)
                log_event("scan_quick", norad_id=asteroid.norad_id)
        
        # Optimized collision detection
        spatial.clear()
        for asteroid in asteroids:
            spatial.insert(asteroid)
        for shot in shots:
            spatial.insert(shot)
        spatial.insert(player)
        
        shots_to_remove = []
        asteroids_to_split = []
        
        for shot in shots:
            for asteroid in spatial.query(shot):
                if not isinstance(asteroid, Asteroid):
                    continue
                if shot.collides_with(asteroid):
                    log_event("asteroid_shot", norad_id=asteroid.norad_id)
                    shots_to_remove.append(shot)
                    asteroids_to_split.append(asteroid)
                    session.add_score(DESTROY_POINTS)
                    session.record_destroy(asteroid.norad_id)
                    break
        
        for asteroid in spatial.query(player):
            if not isinstance(asteroid, Asteroid):
                continue
            if asteroid.collides_with(player):
                session.record_death()
                packet = session.create_packet()
                log_event("player_hit", final_score=session.score)
                print(f"\n=== GAME OVER ===")
                print(f"Score: {session.score}")
                print(f"Scans: {session.scans_quick + session.scans_full}")
                print(f"Signed packet: {packet.to_json()}")
                running = False
                break
        
        for shot in shots_to_remove:
            shot.release()
        for asteroid in asteroids_to_split:
            asteroid.split()
        
        # Render
        screen.fill("black")
        for sprite in drawable:
            sprite.draw(screen)
        
        _draw_hud(screen, font, session)
        
        if keys[pygame.K_F1]:
            _draw_debug_hud(screen, clock, spatial, asteroid_pool, shot_pool)
        
        # F2: Show debris info for nearest scanned asteroid
        if keys[pygame.K_F2]:
            _draw_debris_info(screen, player, asteroids)
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()


def _find_nearest_asteroid(player, asteroids, max_range):
    nearest = None
    nearest_dist = max_range
    
    for asteroid in asteroids:
        if not asteroid._alive:
            continue
        dist = player.position.distance_to(asteroid.position)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = asteroid
    
    return nearest


def _draw_hud(screen, font, session):
    score_text = font.render(f"SCORE: {session.score}", True, (255, 255, 255))
    score_rect = score_text.get_rect(midtop=(SCREEN_WIDTH // 2, 10))
    screen.blit(score_text, score_rect)
    
    small_font = pygame.font.Font(None, 24)
    total_scans = session.scans_quick + session.scans_full
    stats = [
        f"Scans: {total_scans} ({session.scans_full} full)",
        f"Destroys: {session.destroys}",
        f"Session: {session.session_id}",
    ]
    y = 10
    for stat in stats:
        surf = small_font.render(stat, True, (150, 150, 150))
        rect = surf.get_rect(topright=(SCREEN_WIDTH - 10, y))
        screen.blit(surf, rect)
        y += 20
    
    hint = small_font.render("WASD: move | SPACE: shoot | E: scan | F1: debug | F2: debris", True, (80, 80, 80))
    hint_rect = hint.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 10))
    screen.blit(hint, hint_rect)


def _draw_debug_hud(screen, clock, spatial, asteroid_pool, shot_pool):
    font = pygame.font.Font(None, 24)
    lines = [
        f"FPS: {clock.get_fps():.1f}",
        f"Asteroids: {asteroid_pool.active} (pool: {asteroid_pool.available})",
        f"Shots: {shot_pool.active} (pool: {shot_pool.available})",
        f"Spatial cells: {spatial.cell_count}",
    ]
    y = 50
    for line in lines:
        surf = font.render(line, True, (0, 255, 0))
        screen.blit(surf, (10, y))
        y += 20


def _draw_debris_info(screen, player, asteroids):
    """Show real debris info for nearest scanned asteroid."""
    font = pygame.font.Font(None, 20)
    
    # Find nearest scanned asteroid
    nearest = None
    nearest_dist = 300
    for asteroid in asteroids:
        if not asteroid._scanned or not asteroid.debris_data:
            continue
        dist = player.position.distance_to(asteroid.position)
        if dist < nearest_dist:
            nearest_dist = dist
            nearest = asteroid
    
    if not nearest:
        return
    
    # Draw info panel
    data = nearest.debris_data
    lines = [
        f"NORAD: {data.get('norad_id', 'N/A')}",
        f"Name: {data.get('name', 'UNKNOWN')}",
        f"Type: {data.get('object_type', 'N/A')}",
        f"Country: {data.get('country', 'N/A')}",
        f"Launch: {data.get('launch_date', 'N/A')}",
    ]
    
    y = SCREEN_HEIGHT // 2 - 60
    for line in lines:
        surf = font.render(line, True, (0, 255, 0))
        screen.blit(surf, (10, y))
        y += 22


if __name__ == "__main__":
    main()