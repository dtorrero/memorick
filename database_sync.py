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
        
        # Ensure URL ends with a trailing slash for consistency
        if server_url and not server_url.endswith('/'):
            server_url += '/'
            
        self.server_url = server_url
        print(f"Initializing sync database with server URL: {self.server_url}")
        
        # Don't use a sync queue since we'll only write directly when a game ends
        self.online = False   # Assume offline until we verify connection
        self.using_cached_data = False  # Flag to indicate if we're using cached data
        
        # Check server connection
        self.check_server_connection()
        
        # We don't need a sync tracking table anymore, but we'll keep the local table
        # structure for backwards compatibility
        self.initialize_sync_table()
        
        # Check for server reset if we're online
        if self.online:
            self.detect_server_reset()
        
        # Remove background sync thread since we no longer need automatic syncing
        # We only want to write to the server when a game ends
    
    def check_server_connection(self):
        """Check if the server is available."""
        try:
            print(f"Checking server connection to: {self.server_url}")
            # Ensure we're connecting to the base URL
            url = self.server_url
            if not url.endswith('/'):
                url += '/'
                
            response = requests.get(url, timeout=5)
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
        Save game statistics locally and directly to the server (no queuing).
        """
        # First save to local DB using the original method
        local_id = super().save_game_stats(
            player_name, difficulty, start_time, end_time, 
            moves, matches, completed)
        
        # If we're online, immediately try to save to the server
        if self.online or self.check_server_connection():
            try:
                # Prepare the data for the server
                stats_data = {
                    "client_id": CLIENT_ID,
                    "player_name": player_name,
                    "difficulty": difficulty,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration_seconds": end_time - start_time,
                    "moves": moves,
                    "matches": matches,
                    "errors": max(0, moves - matches),
                    "completed": completed
                }
                
                # Send directly to server
                base_url = self.server_url.rstrip('/')
                url = f"{base_url}/api/stats/save"
                print(f"Directly saving game stats to server: {url}")
                
                response = requests.post(
                    url,
                    json=stats_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    print(f"Successfully saved game stats to server for player {player_name}")
                else:
                    print(f"Failed to save game stats to server: {response.status_code}")
            except Exception as e:
                print(f"Error saving game stats to server: {e}")
        
        # Return the local ID (we don't track sync status anymore)
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
            # Construct API endpoint correctly, ensuring no double slashes
            base_url = self.server_url.rstrip('/')
            url = f"{base_url}/api/stats/save"
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
        # Reset cached data flag
        self.using_cached_data = False
        
        # Check server connection without syncing local data
        if not self.online:
            self.check_server_connection()
        
        if not self.online:
            print("Cannot get remote leaderboard: Server is offline")
            # If we have cached data, mark it and return it with a flag
            self.cursor.execute(f'''
                SELECT COUNT(*) FROM game_stats 
                WHERE difficulty = ? OR ? IS NULL
            ''', (difficulty, difficulty))
            
            count = self.cursor.fetchone()[0]
            if count > 0:
                print("Using cached leaderboard data (server offline)")
                self.using_cached_data = True
                # Get local data as fallback, with special flag
                local_data = super().get_leaderboard(difficulty, limit)
                # Add a flag to indicate this is cached data
                for item in local_data:
                    item["cached"] = True
                return local_data
            return []  # No cached data
        
        try:
            # Try to get remote leaderboard with cache busting parameter
            difficulty_param = difficulty if difficulty else "all"
            
            # Construct API endpoint correctly, ensuring no double slashes
            base_url = self.server_url.rstrip('/')
            url = f"{base_url}/api/stats/leaderboard/{difficulty_param}"
            
            # Add cache busting parameter to prevent browser/request caching
            cache_buster = int(time.time() * 1000)  # Use milliseconds for more uniqueness
            
            print(f"!!! Fetching fresh leaderboard from: {url}?t={cache_buster}")
            
            # Disable all caching mechanisms
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            response = requests.get(
                url, 
                params={
                    "limit": limit,
                    "t": cache_buster  # Cache busting parameter
                }, 
                headers=headers,
                timeout=5
            )
            
            print(f"!!! Leaderboard response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                leaderboard = data.get("leaderboard", [])
                
                # If server returned empty data but we have local records,
                # this might indicate a server reset
                if not leaderboard:
                    self.cursor.execute(f'''
                        SELECT COUNT(*) FROM game_stats 
                        WHERE difficulty = ? OR ? IS NULL
                    ''', (difficulty, difficulty))
                    
                    local_count = self.cursor.fetchone()[0]
                    if local_count > 0:
                        print("Warning: Server returned empty data but local cache exists")
                        print("This may indicate a server reset")
                        # We'll return the empty server data, but could offer reset option
                
                return leaderboard
            else:
                print(f"Error getting remote leaderboard: {response.status_code}")
                # If server error, use cached data as fallback
                print("Using cached leaderboard data (server error)")
                self.using_cached_data = True
                local_data = super().get_leaderboard(difficulty, limit)
                # Add a flag to indicate this is cached data
                for item in local_data:
                    item["cached"] = True
                return local_data
                
        except Exception as e:
            print(f"Failed to get remote leaderboard: {e}")
            # If exception, use cached data as fallback
            print("Using cached leaderboard data (exception)")
            self.using_cached_data = True
            local_data = super().get_leaderboard(difficulty, limit)
            # Add a flag to indicate this is cached data
            for item in local_data:
                item["cached"] = True
            return local_data
    
    def get_player_remote_stats(self, player_name: str) -> Dict[str, Any]:
        """
        Get a player's statistics from the remote server.
        Returns empty stats if server is unreachable, to maintain isolation.
        """
        # Reset cached data flag
        self.using_cached_data = False
        
        # Check server connection without syncing local data
        if not self.online:
            self.check_server_connection()
        
        if not self.online:
            print("Cannot get remote player stats: Server is offline")
            # If we have cached data, mark it and return it with a flag
            self.cursor.execute('''
                SELECT COUNT(*) FROM game_stats WHERE player_name = ?
            ''', (player_name,))
            
            count = self.cursor.fetchone()[0]
            if count > 0:
                print(f"Using cached player stats for {player_name} (server offline)")
                self.using_cached_data = True
                # Get local data as fallback, with special flag
                local_stats = super().get_player_stats(player_name)
                return {
                    "player": player_name, 
                    "stats": local_stats,
                    "cached": True
                }
            return {"player": player_name, "stats": []}  # No cached data
        
        try:
            # Add cache busting parameter to prevent browser/request caching
            cache_buster = int(time.time() * 1000)  # Use milliseconds for more uniqueness
            
            # Construct API endpoint correctly, ensuring no double slashes
            base_url = self.server_url.rstrip('/')
            url = f"{base_url}/api/stats/player/{player_name}"
            
            print(f"!!! Fetching fresh player stats from: {url}?t={cache_buster}")
            
            # Disable all caching mechanisms
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            response = requests.get(
                url, 
                params={"t": cache_buster},  # Cache busting parameter
                headers=headers,
                timeout=5
            )
            
            print(f"!!! Player stats response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # If server returned empty stats but we have local records,
                # this might indicate a server reset
                if not data.get("stats", []):
                    self.cursor.execute('''
                        SELECT COUNT(*) FROM game_stats WHERE player_name = ?
                    ''', (player_name,))
                    
                    local_count = self.cursor.fetchone()[0]
                    if local_count > 0:
                        print(f"Warning: Server returned empty data for {player_name} but local cache exists")
                        print("This may indicate a server reset")
                        # We'll return the server data, but could offer reset option
                
                return data
            else:
                print(f"Error getting remote player stats: {response.status_code}")
                # If server error, use cached data as fallback
                print(f"Using cached stats for {player_name} (server error)")
                self.using_cached_data = True
                local_stats = super().get_player_stats(player_name)
                return {
                    "player": player_name,
                    "stats": local_stats,
                    "cached": True
                }
                
        except Exception as e:
            print(f"Failed to get remote player stats: {e}")
            # If exception, use cached data as fallback
            print(f"Using cached stats for {player_name} (exception)")
            self.using_cached_data = True
            local_stats = super().get_player_stats(player_name)
            return {
                "player": player_name,
                "stats": local_stats,
                "cached": True
            }
    
    def force_sync_all(self):
        """
        This method has been deprecated.
        
        In the new design, we don't sync local data to the server,
        data is only sent directly to the server when a game ends.
        
        This method now only checks the server connection.
        """
        if not self.online:
            self.check_server_connection()
            
        if self.online:
            print("Server connection is online")
            return True
        else:
            print("Server connection is offline")
            return False
    
    def detect_server_reset(self):
        """
        Detect if the server database has been reset or has significantly fewer records
        than our local cache, which might indicate a server wipe.
        """
        try:
            # Count records in local DB
            self.cursor.execute("SELECT COUNT(*) FROM game_stats")
            local_count = self.cursor.fetchone()[0]
            
            # If we have no local data, no need to check
            if local_count == 0:
                return False
            
            # Get server record count for comparison
            base_url = self.server_url.rstrip('/')
            url = f"{base_url}/api/stats/count"
            
            try:
                # Try to get record count from server
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    try:
                        server_data = response.json()
                        server_count = server_data.get("count", 0)
                        
                        # If server has significantly fewer records than local DB
                        if server_count < local_count * 0.5 and server_count < 10:
                            print(f"Server reset detected! Server: {server_count}, Local: {local_count}")
                            return True
                    except:
                        # If we can't parse server response, assume no reset
                        return False
            except:
                # If server endpoint doesn't exist or other error, ignore
                return False
                
            return False
        except Exception as e:
            print(f"Error detecting server reset: {e}")
            return False
    
    def prompt_reset_local_cache(self):
        """
        Reset the local cache of remote data (useful after server reset).
        Returns True if the cache was successfully reset.
        """
        try:
            # Clear all data from game_stats table but keep the table structure
            self.cursor.execute("DELETE FROM game_stats")
            
            # Also clear any sync tracking data
            if self.table_exists("sync_status"):
                self.cursor.execute("DELETE FROM sync_status")
                
            self.conn.commit()
            print("Local cache of remote data has been reset")
            return True
        except Exception as e:
            print(f"Error resetting local cache: {e}")
            return False
    
    def table_exists(self, table_name):
        """Check if a table exists in the database."""
        self.cursor.execute(f"""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='{table_name}'
        """)
        return self.cursor.fetchone() is not None


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