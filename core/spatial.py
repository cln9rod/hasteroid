"""
Spatial Hash Grid for efficient collision detection.
Reduces O(n²) to O(n) average case by only checking nearby cells.
"""
from collections import defaultdict
from typing import Iterator, List, Tuple

__all__ = ["SpatialHash"]


class SpatialHash:
    """
    Grid-based spatial partitioning for broad-phase collision.
    
    Cell size should be >= largest entity radius * 2 for correctness.
    Default 128px works for asteroids up to 64px radius.
    """
    
    __slots__ = ("cell_size", "_grid", "_entity_cells")
    
    def __init__(self, cell_size: int = 128):
        self.cell_size = cell_size
        self._grid: dict[Tuple[int, int], List] = defaultdict(list)
        self._entity_cells: dict[int, Tuple[int, int]] = {}  # entity id -> cell
    
    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coords to grid cell."""
        return (int(x // self.cell_size), int(y // self.cell_size))
    
    def _get_cells_for_entity(self, entity) -> List[Tuple[int, int]]:
        """Get all cells an entity overlaps (handles entities spanning cells)."""
        radius = getattr(entity, "radius", 0)
        pos = entity.position
        
        min_cell = self._get_cell(pos.x - radius, pos.y - radius)
        max_cell = self._get_cell(pos.x + radius, pos.y + radius)
        
        cells = []
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                cells.append((cx, cy))
        return cells
    
    def clear(self) -> None:
        """Clear all entities. Call once per frame before re-inserting."""
        self._grid.clear()
        self._entity_cells.clear()
    
    def insert(self, entity) -> None:
        """Insert entity into all cells it overlaps."""
        cells = self._get_cells_for_entity(entity)
        for cell in cells:
            self._grid[cell].append(entity)
        self._entity_cells[id(entity)] = cells[0]  # Primary cell for reference
    
    def query(self, entity) -> Iterator:
        """
        Yield all entities in same/adjacent cells (potential collisions).
        Caller must still do narrow-phase check (actual collision test).
        """
        seen = set()
        seen.add(id(entity))
        
        cells = self._get_cells_for_entity(entity)
        
        for cell in cells:
            # Check this cell and 8 neighbors
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor = (cell[0] + dx, cell[1] + dy)
                    for other in self._grid.get(neighbor, ()):
                        oid = id(other)
                        if oid not in seen:
                            seen.add(oid)
                            yield other
    
    def query_point(self, x: float, y: float, radius: float = 0) -> Iterator:
        """Query entities near a specific point."""
        cell = self._get_cell(x, y)
        seen = set()
        
        # Check cell and neighbors
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor = (cell[0] + dx, cell[1] + dy)
                for entity in self._grid.get(neighbor, ()):
                    eid = id(entity)
                    if eid not in seen:
                        seen.add(eid)
                        yield entity
    
    def query_rect(self, x1: float, y1: float, x2: float, y2: float) -> Iterator:
        """Query all entities within a rectangle."""
        min_cell = self._get_cell(x1, y1)
        max_cell = self._get_cell(x2, y2)
        seen = set()
        
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                for entity in self._grid.get((cx, cy), ()):
                    eid = id(entity)
                    if eid not in seen:
                        seen.add(eid)
                        yield entity
    
    @property
    def entity_count(self) -> int:
        """Total entities currently in grid."""
        return len(self._entity_cells)
    
    @property
    def cell_count(self) -> int:
        """Active cells (for debugging)."""
        return len(self._grid)
