from circleshape import CircleShape
from constants import (
    PLAYER_RADIUS,
    LINE_WIDTH,
    PLAYER_TURN_SPEED,
    PLAYER_SPEED,
    PLAYER_SHOOT_SPEED,
    PLAYER_SHOOT_COOLDOWN_SECONDS,
    SCAN_RANGE,
    SCAN_TIME_QUICK,
    SCAN_TIME_FULL,
)
from shot import Shot
import pygame


class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.rotation = 0
        self.shoot_timer = 0
        
        # Scan state
        self.scan_timer = 0.0
        self.scan_target = None
        self.last_scan_result = None  # ("quick" | "full", asteroid)

    def draw(self, screen):
        pygame.draw.polygon(screen, "white", self.triangle(), LINE_WIDTH)
        
        # Draw scan beam if scanning
        if self.scan_target and self.scan_timer > 0:
            self._draw_scan_beam(screen)

    def _draw_scan_beam(self, screen):
        """Draw scan line with progress indicator."""
        target_pos = self.scan_target.position
        
        # Beam color based on progress
        progress = min(self.scan_timer / SCAN_TIME_FULL, 1.0)
        if self.scan_timer >= SCAN_TIME_FULL:
            color = (0, 255, 0)  # Green = full scan
        elif self.scan_timer >= SCAN_TIME_QUICK:
            color = (0, 200, 255)  # Cyan = quick scan ready
        else:
            color = (100, 100, 100)  # Gray = scanning
        
        # Draw beam
        pygame.draw.line(screen, color, self.position, target_pos, 1)
        
        # Draw scan ring around target
        ring_radius = self.scan_target.radius + 5 + (progress * 10)
        pygame.draw.circle(screen, color, target_pos, int(ring_radius), 1)

    def triangle(self):
        forward = pygame.Vector2(0, 1).rotate(self.rotation)
        right = pygame.Vector2(0, 1).rotate(self.rotation + 90) * self.radius / 1.5
        a = self.position + forward * self.radius
        b = self.position - forward * self.radius - right
        c = self.position - forward * self.radius + right
        return [a, b, c]
    
    def rotate(self, dt):
        self.rotation += PLAYER_TURN_SPEED * dt    
        
    def update(self, dt):
        self.shoot_timer -= dt
        self.last_scan_result = None
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            self.rotate(-dt)
        if keys[pygame.K_d]:
            self.rotate(dt)
        if keys[pygame.K_w]:
            self.move(dt)
        if keys[pygame.K_s]:
            self.move(-dt)
        if keys[pygame.K_SPACE]:
            if self.shoot_timer <= 0:
                self.shoot()
                self.shoot_timer = PLAYER_SHOOT_COOLDOWN_SECONDS
        
        # Scan mechanic (E key)
        if keys[pygame.K_e]:
            self._update_scan(dt)
        else:
            self._end_scan()

    def _update_scan(self, dt):
        """Update scan progress."""
        if self.scan_target:
            # Check target still in range
            dist = self.position.distance_to(self.scan_target.position)
            if dist > SCAN_RANGE or not self.scan_target._alive:
                self._end_scan()
                return
            
            self.scan_timer += dt
            
            # Check for scan completion
            if self.scan_timer >= SCAN_TIME_FULL and not getattr(self.scan_target, '_full_scanned', False):
                self.scan_target._full_scanned = True
                self.scan_target._scanned = True
                self.last_scan_result = ("full", self.scan_target)
            elif self.scan_timer >= SCAN_TIME_QUICK and not getattr(self.scan_target, '_scanned', False):
                self.scan_target._scanned = True
                self.last_scan_result = ("quick", self.scan_target)

    def _end_scan(self):
        """Reset scan state."""
        self.scan_timer = 0.0
        self.scan_target = None

    def set_scan_target(self, asteroid):
        """Set new scan target (called from main loop)."""
        if asteroid != self.scan_target:
            self.scan_target = asteroid
            self.scan_timer = 0.0

    def move(self, dt):
        unit_vector = pygame.Vector2(0, 1)
        rotated_vector = unit_vector.rotate(self.rotation)
        rotated_with_speed_vector = rotated_vector * PLAYER_SPEED * dt
        self.position += rotated_with_speed_vector

    def shoot(self):
        # Use pool if available
        shot = Shot.acquire(self.position.x, self.position.y)
        velocity = pygame.Vector2(0, 1)
        velocity = velocity.rotate(self.rotation)
        velocity = velocity * PLAYER_SHOOT_SPEED
        shot.velocity = velocity