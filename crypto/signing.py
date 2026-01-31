"""
Score signing for anti-cheat.
Uses HMAC-SHA256 to sign game session data.
"""
import hmac
import hashlib
import time
import uuid
import json
from dataclasses import dataclass, field, asdict
from typing import List

__all__ = ["GameSession", "ScorePacket", "ActionLog"]


@dataclass
class ActionLog:
    """Records player actions for validation."""
    actions: List[dict] = field(default_factory=list)
    
    def record(self, action_type: str, **details):
        """Record an action with timestamp."""
        self.actions.append({
            "t": round(time.time(), 3),
            "type": action_type,
            **details
        })
    
    def get_hash(self) -> str:
        """Hash of all actions - backend can replay to verify."""
        data = json.dumps(self.actions, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def clear(self):
        self.actions.clear()


class GameSession:
    """
    Manages a game session with signed score submission.
    
    Usage:
        session = GameSession(secret_key)  # Key from server at session start
        session.record_action("asteroid_shot", points=10)
        session.add_score(10)
        ...
        packet = session.create_packet()
        # Send packet to backend
    """
    
    def __init__(self, secret_key: str = None):
        """
        Args:
            secret_key: Shared secret from server. If None, generates local key
                        (for testing only - not secure for production)
        """
        self.session_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self._key = secret_key or self._generate_test_key()
        
        # Game state
        self.score = 0
        self.scans_quick = 0
        self.scans_full = 0
        self.destroys = 0
        self.actions = ActionLog()
    
    def _generate_test_key(self) -> str:
        """Generate a test key (NOT for production)."""
        return hashlib.sha256(f"test-{self.session_id}".encode()).hexdigest()
    
    def add_score(self, points: int):
        """Add points to score."""
        self.score += points
    
    def record_destroy(self, norad_id=None):
        """Record asteroid destruction."""
        self.destroys += 1
        self.actions.record("destroy", norad_id=norad_id)
    
    def record_scan(self, scan_type: str, norad_id=None):
        """Record scan completion."""
        if scan_type == "quick":
            self.scans_quick += 1
        elif scan_type == "full":
            self.scans_full += 1
        self.actions.record("scan", scan_type=scan_type, norad_id=norad_id)
    
    def record_death(self):
        """Record player death."""
        self.actions.record("death")
    
    def create_packet(self) -> "ScorePacket":
        """Create signed score packet for submission."""
        timestamp = int(time.time())
        duration = int(timestamp - self.start_time)
        actions_hash = self.actions.get_hash()
        
        # Build signature payload
        payload = f"{self.score}:{self.session_id}:{timestamp}:{actions_hash}"
        signature = hmac.new(
            self._key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return ScorePacket(
            session_id=self.session_id,
            score=self.score,
            scans_quick=self.scans_quick,
            scans_full=self.scans_full,
            destroys=self.destroys,
            duration=duration,
            timestamp=timestamp,
            actions_hash=actions_hash,
            signature=signature
        )


@dataclass
class ScorePacket:
    """Signed score data for backend submission."""
    session_id: str
    score: int
    scans_quick: int
    scans_full: int
    destroys: int
    duration: int          # Seconds played
    timestamp: int         # Unix timestamp
    actions_hash: str      # Hash of action log
    signature: str         # HMAC signature
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @staticmethod
    def verify(packet_dict: dict, secret_key: str) -> bool:
        """
        Verify packet signature (for backend use).
        
        Returns True if signature is valid.
        """
        payload = (
            f"{packet_dict['score']}:{packet_dict['session_id']}:"
            f"{packet_dict['timestamp']}:{packet_dict['actions_hash']}"
        )
        expected_sig = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_sig, packet_dict['signature'])


# Validation helpers for backend
def validate_score_rate(packet: ScorePacket, max_score_per_second: int = 50) -> bool:
    """Check if score is achievable in the given time."""
    if packet.duration <= 0:
        return False
    rate = packet.score / packet.duration
    return rate <= max_score_per_second


def validate_action_counts(packet: ScorePacket) -> bool:
    """Check score matches action counts."""
    # These should match constants.py values
    DESTROY_PTS = 10
    SCAN_QUICK_PTS = 5
    SCAN_FULL_PTS = 25
    
    expected_score = (
        packet.destroys * DESTROY_PTS +
        packet.scans_quick * SCAN_QUICK_PTS +
        packet.scans_full * SCAN_FULL_PTS
    )
    return packet.score == expected_score
