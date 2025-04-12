"""
Enhanced database manager with server synchronization capabilities.
Use this as an alternative to the original database.py when server integration is needed.
"""
import sqlite3
import os
import datetime
import time
import uuid
import threading
import requests
from typing import Dict, List, Optional, Tuple, Any
import sys

# Add parent directory to path to allow importing shared modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from shared.models import GameStats

# Import original database implementation to extend it
from database import GameDatabase as OriginalGameDatabase

# Server configuration
SERVER_URL = "http://localhost:5000"
# Generate a unique client ID if none exists
CLIENT_ID_FILE = ".client_id"
if os.path.exists(CLIENT_ID_FILE):
    with open(CLIENT_ID_FILE, "r") as f:
        CLIENT_ID = f.read().strip()
else:
    CLIENT_ID = str(uuid.uuid4())
    with open(CLIENT_ID_FILE, "w") as f:
        f.write(CLIENT_ID)


class SyncGameDatabase(OriginalGameDatabase):
    """
    Enhanced database manager that extends the original with server synchronization.
    This class handles syncing local data to the remote server, but keeps local and remote
    data properly isolated from each other.
    """
    
    def __init__(self, db_file="memory_game.db", server_url=SERVER_URL):
        """Initialize the database connection with sync capabilities."""
        # Use a different database file for remote mode to ensure isolation
        remote_db_file = "remote_" + db_file
        super().__init__(remote_db_file)
        
        # Ensure server_url has the correct format with http:// prefix
        if server_url and not server_url.startswith(('http://', 'https://')):
            server_url = 'http://' + server_url
        
        self.server_url = server_url
        print(f"Initializing sync database with server URL: {self.server_url}")
        
        self.sync_queue = []  # Queue for stats to be synced
        self.online = False   # Assume offline until we verify connection
        
        # Check server connection
        self.check_server_connection()
        
        # Initialize sync tracking table
        self.initialize_sync_table()
        
        # Start background thread for sync if online
        if self.online:
            self.sync_thread = threading.Thread(target=self.background_sync, daemon=True)
            self.sync_thread.start()
    
    def check_server_connection(self):
        """Check if the server is available."""
        try:
            print(f"Checking server connection to: {self.server_url}")
            response = requests.get(f"{self.server_url}/", timeout=5)
            self.online = response.status_code == 200
            print(f"Server connection: {'Online' if self.online else 'Offline'} (Status code: {response.status_code})")
            return self.online
        except requests.exceptions.ConnectionError as e:
            self.online = False
            print(f"Server connection failed (ConnectionError): {e}")
            return False
        except requests.exceptions.Timeout as e:
            self.online = False
            print(f"Server connection timeout: {e}")
            return False
        except Exception as e:
            self.online = False
            print(f"Server connection error: {e}")
            return False
    
    def initialize_sync_table(self):
        """Initialize the sync tracking table."""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    local_id INTEGER PRIMARY KEY,
                    game_stats_id INTEGER,
                    synced BOOLEAN DEFAULT 0,
                    last_sync_attempt REAL,
                    FOREIGN KEY (game_stats_id) REFERENCES game_stats(id)
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing sync table: {e}")
    
    def save_game_stats(self, 
                       player_name: str,
                       difficulty: str,
                       start_time: float,
                       end_time: float,
                       moves: int,
                       matches: int,
                       completed: bool = True) -> int:
        """
        Save game statistics locally and queue for server sync.
        """
        # First save to local DB using the original method
        local_id = super().save_game_stats(
            player_name, difficulty, start_time, end_time, 
            moves, matches, completed)
        
        if local_id > 0:
            # Add to sync tracking
            try:
                self.cursor.execute('''
                    INSERT INTO sync_status (game_stats_id, synced, last_sync_attempt)
                    VALUES (?, 0, ?)
                ''', (local_id, time.time()))
                self.conn.commit()
                
                # Queue for immediate sync if online
                if self.online:
                    self.sync_queue.append(local_id)
                    # Try immediate sync in background
                    threading.Thread(
                        target=self.sync_game_stat,
                        args=(local_id,),
                        daemon=True
                    ).start()
            except sqlite3.Error as e:
                print(f"Error tracking sync status: {e}")
            
        return local_id
    
    def sync_game_stat(self, game_stats_id: int) -> bool:
        """
        Sync a specific game stat to the server.
        Returns True if sync was successful.
        """
        try:
            # Get the stat from local DB
            self.cursor.execute('''
                SELECT player_name, difficulty, start_time, end_time, 
                       duration_seconds, moves, matches, errors, completed
                FROM game_stats
                WHERE id = ?
            ''', (game_stats_id,))
            
            row = self.cursor.fetchone()
            if not row:
                print(f"Game stat ID {game_stats_id} not found in local DB")
                return False
            
            # Prepare data for server
            stats_data = {
                "client_id": CLIENT_ID,
                "player_name": row[0],
                "difficulty": row[1],
                "start_time": row[2],
                "end_time": row[3],
                "duration_seconds": row[4],
                "moves": row[5],
                "matches": row[6],
                "errors": row[7],
                "completed": bool(row[8])
            }
            
            # Debug info
            print(f"Attempting to sync to server: {self.server_url}")
            print(f"Sync data: {stats_data}")
            
            # Send to server
            url = f"{self.server_url}/api/stats/save"
            print(f"Sending data to: {url}")
            
            response = requests.post(
                url,
                json=stats_data,
                timeout=10  # Increase timeout for slower connections
            )
            
            print(f"Server response: Status {response.status_code}")
            print(f"Response content: {response.text}")
            
            # Update sync status
            if response.status_code == 200:
                self.cursor.execute('''
                    UPDATE sync_status
                    SET synced = 1, last_sync_attempt = ?
                    WHERE game_stats_id = ?
                ''', (time.time(), game_stats_id))
                self.conn.commit()
                print(f"Successfully synced game stat ID {game_stats_id}")
                return True
            else:
                print(f"Failed to sync game stat ID {game_stats_id}: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error syncing game stat: {e}")
            return False
    
    def background_sync(self):
        """Background thread that periodically syncs data to the server."""
        while True:
            try:
                # Check if we're online
                if not self.check_server_connection():
                    # Sleep longer if offline
                    time.sleep(30)
                    continue
                
                # Get items to sync
                self.cursor.execute('''
                    SELECT game_stats_id
                    FROM sync_status
                    WHERE synced = 0
                    LIMIT 10
                ''')
                
                items = self.cursor.fetchall()
                
                if items:
                    print(f"Found {len(items)} items to sync")
                    
                    for item in items:
                        game_stats_id = item[0]
                        success = self.sync_game_stat(game_stats_id)
                        
                        # If failed, don't hammer the server
                        if not success:
                            time.sleep(2)
                
                # Sleep between sync attempts
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Error in sync thread: {e}")
                time.sleep(120)  # Wait longer after an error
    
    def get_remote_leaderboard(self, difficulty: Optional[str] = None, 
                              limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get leaderboard data from the remote server.
        Returns empty list if server is unreachable, to maintain isolation between
        local and remote data.
        """
        if not self.online and not self.check_server_connection():
            print("Cannot get remote leaderboard: Server is offline")
            return []  # Return empty list instead of local data
        
        try:
            # Try to get remote leaderboard
            difficulty_param = difficulty if difficulty else "all"
            url = f"{self.server_url}/api/stats/leaderboard/{difficulty_param}"
            response = requests.get(url, params={"limit": limit}, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("leaderboard", [])
            else:
                print(f"Error getting remote leaderboard: {response.status_code}")
                return []  # Return empty list instead of local data
                
        except Exception as e:
            print(f"Failed to get remote leaderboard: {e}")
            return []  # Return empty list instead of local data
    
    def get_player_remote_stats(self, player_name: str) -> Dict[str, Any]:
        """
        Get a player's statistics from the remote server.
        Returns empty stats if server is unreachable, to maintain isolation.
        """
        if not self.online and not self.check_server_connection():
            print("Cannot get remote player stats: Server is offline")
            return {"player": player_name, "stats": []}  # Empty stats instead of local data
        
        try:
            url = f"{self.server_url}/api/stats/player/{player_name}"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting remote player stats: {response.status_code}")
                return {"player": player_name, "stats": []}  # Empty stats instead of local data
                
        except Exception as e:
            print(f"Failed to get remote player stats: {e}")
            return {"player": player_name, "stats": []}  # Empty stats instead of local data
    
    def force_sync_all(self):
        """
        Force immediate synchronization of all pending game stats.
        Returns the number of successfully synced items.
        """
        if not self.online and not self.check_server_connection():
            print("Cannot force sync: Server is offline")
            return 0
            
        try:
            # Get all unsynced items
            self.cursor.execute('''
                SELECT game_stats_id
                FROM sync_status
                WHERE synced = 0
            ''')
            
            items = self.cursor.fetchall()
            if not items:
                print("No items pending synchronization")
                return 0
                
            print(f"Force syncing {len(items)} items...")
            
            synced_count = 0
            for item in items:
                game_stats_id = item[0]
                if self.sync_game_stat(game_stats_id):
                    synced_count += 1
                # Small delay to avoid overwhelming the server
                time.sleep(0.5)
                
            print(f"Forced sync complete. Successfully synced {synced_count}/{len(items)} items")
            return synced_count
            
        except Exception as e:
            print(f"Error during force sync: {e}")
            return 0


# Singleton instance for use throughout the application
sync_db = SyncGameDatabase()

def get_sync_database(server_url=None) -> SyncGameDatabase:
    """
    Get the syncing database instance.
    
    Args:
        server_url: Optional URL of the server to use.
                   If provided, creates a new instance with this URL.
    """
    global sync_db
    
    # If a custom server URL is provided, create a new instance
    if server_url and server_url != sync_db.server_url:
        print(f"Creating new sync database instance with server URL: {server_url}")
        sync_db = SyncGameDatabase(server_url=server_url)
        
    return sync_db 