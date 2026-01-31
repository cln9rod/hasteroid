"""
Benchmark: Compare O(n²) vs Spatial Hash collision performance.
Run: python benchmark.py

Tests REALISTIC game scenario: shots checking against asteroids
(not all entities vs all entities)
"""
import time
import random
from dataclasses import dataclass
from core.spatial import SpatialHash


@dataclass
class MockEntity:
    x: float
    y: float
    radius: float = 20.0
    entity_type: str = "asteroid"
    
    @property
    def position(self):
        return self


def benchmark_naive(asteroids: list, shots: list, player, iterations: int) -> tuple:
    """O(n*m) brute force: every shot checks every asteroid."""
    total_checks = 0
    start = time.perf_counter()
    
    for _ in range(iterations):
        # Shot vs asteroid
        for shot in shots:
            for asteroid in asteroids:
                total_checks += 1
                dx = shot.x - asteroid.x
                dy = shot.y - asteroid.y
                dist_sq = dx*dx + dy*dy
                threshold = (shot.radius + asteroid.radius) ** 2
                _ = dist_sq <= threshold
        
        # Player vs asteroid
        for asteroid in asteroids:
            total_checks += 1
            dx = player.x - asteroid.x
            dy = player.y - asteroid.y
            dist_sq = dx*dx + dy*dy
    
    elapsed = time.perf_counter() - start
    return elapsed, total_checks // iterations


def benchmark_spatial(asteroids: list, shots: list, player, iterations: int) -> tuple:
    """Spatial hash: shots only check nearby asteroids."""
    spatial = SpatialHash(cell_size=128)
    total_checks = 0
    start = time.perf_counter()
    
    for _ in range(iterations):
        # Rebuild spatial hash
        spatial.clear()
        for a in asteroids:
            spatial.insert(a)
        
        # Shot vs nearby asteroids only
        for shot in shots:
            for other in spatial.query(shot):
                if other.entity_type != "asteroid":
                    continue
                total_checks += 1
                dx = shot.x - other.x
                dy = shot.y - other.y
                dist_sq = dx*dx + dy*dy
                threshold = (shot.radius + other.radius) ** 2
                _ = dist_sq <= threshold
        
        # Player vs nearby asteroids
        for other in spatial.query(player):
            if other.entity_type != "asteroid":
                continue
            total_checks += 1
            dx = player.x - other.x
            dy = player.y - other.y
    
    elapsed = time.perf_counter() - start
    return elapsed, total_checks // iterations


def main():
    print("Collision Detection Benchmark (Game-Realistic)")
    print("=" * 60)
    print("Scenario: N asteroids, 20 shots, 1 player")
    print("Checking: shots->asteroids + player->asteroids")
    print()
    
    iterations = 500
    
    for asteroid_count in [50, 100, 250, 500]:
        asteroids = [
            MockEntity(
                x=random.uniform(0, 1280),
                y=random.uniform(0, 720),
                radius=random.uniform(20, 60),
                entity_type="asteroid"
            )
            for _ in range(asteroid_count)
        ]
        
        shots = [
            MockEntity(
                x=random.uniform(0, 1280),
                y=random.uniform(0, 720),
                radius=5,
                entity_type="shot"
            )
            for _ in range(20)  # Typical shot count
        ]
        
        player = MockEntity(x=640, y=360, radius=20, entity_type="player")
        
        naive_time, naive_checks = benchmark_naive(asteroids, shots, player, iterations)
        spatial_time, spatial_checks = benchmark_spatial(asteroids, shots, player, iterations)
        
        speedup = naive_time / spatial_time if spatial_time > 0 else 0
        check_reduction = (1 - spatial_checks / naive_checks) * 100 if naive_checks > 0 else 0
        
        print(f"Asteroids: {asteroid_count}")
        print(f"  Naive:   {naive_time*1000:.1f}ms  ({naive_checks} checks/frame)")
        print(f"  Spatial: {spatial_time*1000:.1f}ms  ({spatial_checks} checks/frame)")
        print(f"  Speedup: {speedup:.1f}x  |  Check reduction: {check_reduction:.0f}%")
        print()


if __name__ == "__main__":
    main()
