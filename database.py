import sqlite3
import os
import datetime
from typing import Dict, List, Optional, Tuple, Any


class GameDatabase:
    """
    Class to handle SQLite database operations for storing and retrieving
    game statistics for the Memory Card game.
    """
    
    def __init__(self, db_file="memory_game.db"):
        """
        Initialize the database connection.
        
        Args:
            db_file: Path to the SQLite database file
        """
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.initialize_db()
    
    def initialize_db(self) -> None:
        """Create the database and tables if they don't exist."""
        try:
            # Create database directory if it doesn't exist
            db_dir = os.path.dirname(self.db_file)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # Connect to database (creates it if it doesn't exist)
            self.conn = sqlite3.connect(self.db_file)
            self.cursor = self.conn.cursor()
            
            # Create game_stats table if it doesn't exist
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    duration_seconds REAL NOT NULL,
                    moves INTEGER NOT NULL,
                    matches INTEGER NOT NULL,
                    errors INTEGER NOT NULL,
                    completed BOOLEAN NOT NULL
                )
            ''')
            
            self.conn.commit()
            print("Database initialized successfully.")
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def save_game_stats(self, 
                       player_name: str,
                       difficulty: str,
                       start_time: float,
                       end_time: float,
                       moves: int,
                       matches: int,
                       completed: bool = True) -> int:
        """
        Save game statistics to the database.
        
        Args:
            player_name: Name of the player
            difficulty: Game difficulty (Easy, Medium, Hard)
            start_time: Game start time (UNIX timestamp)
            end_time: Game end time (UNIX timestamp)
            moves: Number of moves taken
            matches: Number of matches found
            completed: Whether the game was completed or abandoned
            
        Returns:
            ID of the inserted record
        """
        try:
            if not self.conn:
                self.initialize_db()
            
            # Calculate derived stats
            duration_seconds = end_time - start_time
            errors = max(0, moves - matches)
            
            # Convert timestamps to datetime format for SQLite
            start_datetime = datetime.datetime.fromtimestamp(start_time)
            end_datetime = datetime.datetime.fromtimestamp(end_time)
            
            self.cursor.execute('''
                INSERT INTO game_stats 
                (player_name, difficulty, start_time, end_time, duration_seconds, 
                 moves, matches, errors, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                player_name, difficulty, start_datetime, end_datetime, 
                duration_seconds, moves, matches, errors, completed
            ))
            
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error saving game stats: {e}")
            return -1
    
    def get_player_stats(self, player_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all game statistics for a specific player.
        
        Args:
            player_name: Name of the player
            
        Returns:
            List of dictionaries containing player's game stats
        """
        try:
            if not self.conn:
                self.initialize_db()
            
            self.cursor.execute('''
                SELECT id, player_name, difficulty, start_time, end_time, 
                       duration_seconds, moves, matches, errors, completed
                FROM game_stats 
                WHERE player_name = ?
                ORDER BY start_time DESC
            ''', (player_name,))
            
            columns = [col[0] for col in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error retrieving player stats: {e}")
            return []
    
    def get_leaderboard(self, difficulty: Optional[str] = None, 
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the leaderboard (best games by time) for a given difficulty.
        
        Args:
            difficulty: Game difficulty (Easy, Medium, Hard) or None for all
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing top game stats
        """
        try:
            if not self.conn:
                self.initialize_db()
            
            query = '''
                SELECT id, player_name, difficulty, start_time, end_time, 
                       duration_seconds, moves, matches, errors
                FROM game_stats 
                WHERE completed = 1
            '''
            
            params = []
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            
            query += " ORDER BY duration_seconds ASC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            
            columns = [col[0] for col in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error retrieving leaderboard: {e}")
            return []
    
    def get_player_best_time(self, player_name: str, 
                           difficulty: Optional[str] = None) -> Optional[float]:
        """
        Get a player's best completion time.
        
        Args:
            player_name: Name of the player
            difficulty: Game difficulty (Easy, Medium, Hard) or None for all
            
        Returns:
            Best completion time in seconds or None if no completed games
        """
        try:
            if not self.conn:
                self.initialize_db()
            
            query = '''
                SELECT MIN(duration_seconds) as best_time
                FROM game_stats 
                WHERE player_name = ? AND completed = 1
            '''
            
            params = [player_name]
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            
            return result[0] if result and result[0] is not None else None
        except sqlite3.Error as e:
            print(f"Error retrieving player's best time: {e}")
            return None
    
    def get_game_count(self) -> int:
        """
        Get the total number of games recorded in the database.
        
        Returns:
            Total number of games
        """
        try:
            if not self.conn:
                self.initialize_db()
            
            self.cursor.execute("SELECT COUNT(*) FROM game_stats")
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error getting game count: {e}")
            return 0
    
    def get_recent_games(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent games.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing recent game stats
        """
        try:
            if not self.conn:
                self.initialize_db()
            
            self.cursor.execute('''
                SELECT id, player_name, difficulty, start_time, end_time, 
                       duration_seconds, moves, matches, errors, completed
                FROM game_stats 
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [col[0] for col in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error retrieving recent games: {e}")
            return []


# Singleton instance for use throughout the application
db = GameDatabase()

def get_database() -> GameDatabase:
    """Get the database instance."""
    return db 