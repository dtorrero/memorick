"""
Shared data models for both the game client and server.
This ensures consistency in data structures across components.
"""
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class GameStats:
    """Game statistics data model."""
    player_name: str
    difficulty: str
    start_time: float
    end_time: float
    duration_seconds: float
    moves: int
    matches: int
    errors: int
    completed: bool
    id: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data):
        """Create a GameStats object from a dictionary."""
        return cls(
            player_name=data.get('player_name', ''),
            difficulty=data.get('difficulty', ''),
            start_time=data.get('start_time', 0.0),
            end_time=data.get('end_time', 0.0),
            duration_seconds=data.get('duration_seconds', 0.0),
            moves=data.get('moves', 0),
            matches=data.get('matches', 0),
            errors=data.get('errors', 0),
            completed=data.get('completed', False),
            id=data.get('id')
        )
    
    def to_dict(self):
        """Convert the GameStats object to a dictionary."""
        return {
            'player_name': self.player_name,
            'difficulty': self.difficulty,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': self.duration_seconds,
            'moves': self.moves,
            'matches': self.matches,
            'errors': self.errors,
            'completed': self.completed,
            'id': self.id
        }
    
    @classmethod
    def create_from_game_end(cls, player_name, difficulty, start_time, end_time, moves, matches, completed=True):
        """Create a GameStats object from game end data."""
        duration = end_time - start_time
        errors = max(0, moves - matches)
        
        return cls(
            player_name=player_name,
            difficulty=difficulty,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            moves=moves,
            matches=matches,
            errors=errors,
            completed=completed
        ) 