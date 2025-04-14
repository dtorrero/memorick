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
import random

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
        
        # Make sure the source column exists for tracking data origins
        self._ensure_source_column_exists()
        
        # Clean the database to remove duplicates
        self.clean_database()
        
        # We don't need a sync tracking table anymore, but we'll keep the local table
        # structure for backwards compatibility
        self.initialize_sync_table()
        
        # Check for server reset if we're online
        if self.online:
            self.detect_server_reset()
            
            # Get fresh server data immediately on initialization
            self._refresh_server_data()
        
        # Remove background sync thread since we no longer need automatic syncing
        # We only want to write to the server when a game ends
    
    def _ensure_source_column_exists(self):
        """Make sure the game_stats table has a source column to track data origin."""
        try:
            # Check if source column exists
            self.cursor.execute("PRAGMA table_info(game_stats)")
            columns = self.cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'source' not in column_names:
                print("Adding 'source' column to game_stats table...")
                self.cursor.execute('''
                    ALTER TABLE game_stats
                    ADD COLUMN source TEXT DEFAULT 'local'
                ''')
                self.conn.commit()
                print("Added 'source' column successfully")
                
            # Also ensure server_id column exists to track IDs from the server
            if 'server_id' not in column_names:
                print("Adding 'server_id' column to game_stats table...")
                self.cursor.execute('''
                    ALTER TABLE game_stats
                    ADD COLUMN server_id INTEGER
                ''')
                self.conn.commit()
                print("Added 'server_id' column successfully")
                
        except sqlite3.Error as e:
            print(f"Error ensuring columns exist: {e}")
    
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
        Always marks local records with source='local' for proper tracking.
        """
        # First save to local DB with explicit source tag
        try:
            errors = max(0, moves - matches)
            duration = end_time - start_time
            
            self.cursor.execute('''
                INSERT INTO game_stats (
                    player_name, difficulty, start_time, end_time, 
                    duration_seconds, moves, matches, errors, completed, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'local')
            ''', (player_name, difficulty, start_time, end_time, 
                 duration, moves, matches, errors, completed))
            
            local_id = self.cursor.lastrowid
            self.conn.commit()
            
        except sqlite3.Error as e:
            print(f"Error saving game stats to local DB: {e}")
            return -1

        # If we're online, try to save to the server with retry logic
        if self.online or self.check_server_connection():
            # Prepare the data for the server (outside the retry loop to avoid recomputing)
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
                "completed": completed,
                "local_id": local_id  # Include local_id to help prevent duplicates
            }
            
            # Retry parameters
            max_retries = 5
            base_delay = 1  # Initial delay in seconds
            
            for attempt in range(1, max_retries + 1):
                try:
                    # Construct server URL
                    base_url = self.server_url.rstrip('/')
                    url = f"{base_url}/api/stats/save"
                    
                    if attempt > 1:
                        print(f"Retry attempt {attempt}/{max_retries} for saving game stats")
                    else:
                        print(f"Directly saving game stats to server: {url}")
                    
                    # Send data to server
                    response = requests.post(
                        url,
                        json=stats_data,
                        timeout=10 + (attempt * 5)  # Increasing timeout with each retry
                    )
                    
                    # Handle server response
                    if response.status_code == 200:
                        print(f"Successfully saved game stats to server for player {player_name}")
                        # No need to refresh data automatically, it will be refreshed when 
                        # the stats page is opened
                        return local_id
                    
                    # Special handling for specific error codes
                    elif response.status_code == 409:  # Conflict - stat may already exist
                        print(f"Game stat already exists on server (conflict response)")
                        return local_id
                    else:
                        print(f"Attempt {attempt}: Failed to save game stats to server: {response.status_code}")
                        # Only retry on 5xx server errors or specific 4xx errors that might be temporary
                        if response.status_code < 500 and response.status_code != 429:  # Not a server error or rate limit
                            print(f"Non-retriable error code {response.status_code}, abandoning retry")
                            break
                
                except requests.exceptions.RequestException as e:
                    print(f"Attempt {attempt}: Network error saving game stats: {e}")
                
                # Don't sleep after the last attempt
                if attempt < max_retries:
                    # Exponential backoff with jitter to avoid thundering herd
                    delay = base_delay * (2 ** (attempt - 1)) * (0.5 + random.random())
                    print(f"Waiting {delay:.2f}s before retry...")
                    time.sleep(delay)
            
            print(f"Failed to save game stats to server after {max_retries} attempts")
        
        # Return the local ID regardless of server save success
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
    
    def get_leaderboard(self, difficulty: Optional[str] = None, 
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        Override the original get_leaderboard method to handle both local and remote data.
        In remote mode, only return server-sourced data if available, falling back to 
        local data only when necessary.
        
        Args:
            difficulty: Game difficulty (Easy, Medium, Hard) or None for all
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries containing top game stats
        """
        # When online, directly call the remote method which already handles fallback
        if self.online or self.check_server_connection():
            return self.get_remote_leaderboard(difficulty, limit)
        
        # When completely offline and not in remote mode, use the traditional method
        try:
            if not self.conn:
                self.initialize_db()
            
            # Use explicit SQL ordering to ensure correct results
            query = '''
                SELECT id, player_name, difficulty, start_time, end_time, 
                       duration_seconds, errors, source
                FROM game_stats 
                WHERE completed = 1
            '''
            
            params = []
            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)
            
            # For local data, explicitly filter to only include local source
            query += " AND source = 'local'"
                
            # Explicitly order first by time ascending, then by errors ascending
            query += " ORDER BY duration_seconds ASC, errors ASC LIMIT ?"
            params.append(limit)
            
            # Debug the actual query being executed
            print(f"OFFLINE MODE: Executing local-only leaderboard query: {query} with params {params}")
            
            self.cursor.execute(query, params)
            results = [dict(zip([col[0] for col in self.cursor.description], row)) 
                      for row in self.cursor.fetchall()]
            
            return results
        except sqlite3.Error as e:
            print(f"Error retrieving leaderboard: {e}")
            return []

    def get_remote_leaderboard(self, difficulty: Optional[str] = None, 
                              limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get leaderboard data from the remote server.
        Returns empty list if server is unreachable, to maintain isolation between
        local and remote data.
        """
        # Reset cached data flag
        self.using_cached_data = False
        
        # Always check server connection
        self.check_server_connection()
        
        if not self.online:
            print("Cannot get remote leaderboard: Server is offline")
            # Use cached data only as fallback with clear indicator
            print("Using local-only leaderboard data (server offline)")
            self.using_cached_data = True
            
            # Get local data with source filter
            try:
                query = '''
                    SELECT id, player_name, difficulty, start_time, end_time, 
                           duration_seconds, errors, source
                    FROM game_stats 
                    WHERE completed = 1
                '''
                
                params = []
                if difficulty:
                    query += " AND difficulty = ?"
                    params.append(difficulty)
                
                # Only show local data in offline mode
                query += " AND source = 'local'"
                
                query += " ORDER BY duration_seconds ASC, errors ASC LIMIT ?"
                params.append(limit)
                
                print(f"OFFLINE FALLBACK: Executing local-only query: {query}")
                
                self.cursor.execute(query, params)
                local_data = [dict(zip([col[0] for col in self.cursor.description], row)) 
                             for row in self.cursor.fetchall()]
                
                # Add very clear cached indicator
                for item in local_data:
                    item["cached"] = True
                    item["warning"] = "LOCAL DATA ONLY - Not synced with server"
                
                return local_data
            except Exception as e:
                print(f"Error getting local fallback data: {e}")
                return []
        
        try:
            # Try to get remote leaderboard with cache busting parameter
            difficulty_param = difficulty if difficulty else "all"
            
            # Construct API endpoint correctly, ensuring no double slashes
            base_url = self.server_url.rstrip('/')
            url = f"{base_url}/api/stats/leaderboard/{difficulty_param}"
            
            # Add cache busting parameter to prevent browser/request caching
            cache_buster = int(time.time() * 1000)  # Use milliseconds for more uniqueness
            
            print(f"Fetching fresh leaderboard from: {url}?t={cache_buster}")
            
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
            
            print(f"Leaderboard response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                leaderboard = data.get("leaderboard", [])
                
                # No longer update local cache from server data automatically
                # This prevents data duplication
                # self._update_local_cache_from_server(leaderboard)
                
                # Use the actual server data directly
                return leaderboard
            else:
                print(f"Error getting remote leaderboard: {response.status_code}")
                # Fallback to cached data with warning, using only local source
                print("Using local-only leaderboard data (server error)")
                self.using_cached_data = True
                
                try:
                    query = '''
                        SELECT id, player_name, difficulty, start_time, end_time, 
                               duration_seconds, errors, source
                        FROM game_stats 
                        WHERE completed = 1
                    '''
                    
                    params = []
                    if difficulty:
                        query += " AND difficulty = ?"
                        params.append(difficulty)
                    
                    # Only show local data when server unavailable
                    query += " AND source = 'local'"
                    
                    query += " ORDER BY duration_seconds ASC, errors ASC LIMIT ?"
                    params.append(limit)
                    
                    self.cursor.execute(query, params)
                    local_data = [dict(zip([col[0] for col in self.cursor.description], row)) 
                                 for row in self.cursor.fetchall()]
                    
                    # Add very clear cached indicator
                    for item in local_data:
                        item["cached"] = True
                        item["warning"] = f"LOCAL DATA ONLY - Server error {response.status_code}"
                    
                    return local_data
                except Exception as inner_e:
                    print(f"Error getting local fallback data: {inner_e}")
                    return []
                
        except Exception as e:
            print(f"Failed to get remote leaderboard: {e}")
            # Fallback to cached data with warning
            print("Using local-only leaderboard data (exception)")
            self.using_cached_data = True
            
            try:
                query = '''
                    SELECT id, player_name, difficulty, start_time, end_time, 
                           duration_seconds, errors, source
                    FROM game_stats 
                    WHERE completed = 1
                '''
                
                params = []
                if difficulty:
                    query += " AND difficulty = ?"
                    params.append(difficulty)
                
                # Only show local data when server unavailable
                query += " AND source = 'local'"
                
                query += " ORDER BY duration_seconds ASC, errors ASC LIMIT ?"
                params.append(limit)
                
                self.cursor.execute(query, params)
                local_data = [dict(zip([col[0] for col in self.cursor.description], row)) 
                             for row in self.cursor.fetchall()]
                
                # Add very clear cached indicator
                for item in local_data:
                    item["cached"] = True
                    item["warning"] = f"LOCAL DATA ONLY - Connection error"
                
                return local_data
            except Exception as inner_e:
                print(f"Error getting local fallback data: {inner_e}")
                return []
    
    def _refresh_server_data(self):
        """
        Refresh all server data at once to ensure client is in sync.
        This fetches all leaderboard data for all difficulty levels.
        """
        # First check server connection to avoid unnecessary requests
        if not self.online and not self.check_server_connection():
            print("Server is offline - skipping data refresh")
            return False
            
        try:
            print("Refreshing all server data...")
            # Fetch data for all difficulty levels
            difficulties = ["Easy", "Medium", "Hard"]
            
            for difficulty in difficulties:
                # Use a higher limit to ensure we get all relevant records
                difficulty_param = difficulty if difficulty else "all"
                
                # Construct API endpoint correctly, ensuring no double slashes
                base_url = self.server_url.rstrip('/')
                url = f"{base_url}/api/stats/leaderboard/{difficulty_param}"
                
                # Add cache busting parameter
                cache_buster = int(time.time() * 1000)
                
                print(f"Refreshing {difficulty} leaderboard from server...")
                
                # Strong cache-busting headers
                headers = {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
                
                response = requests.get(
                    url, 
                    params={
                        "limit": 100,  # High limit to get most data
                        "t": cache_buster
                    }, 
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    leaderboard = data.get("leaderboard", [])
                    print(f"Retrieved {len(leaderboard)} {difficulty} records from server")
                    
                    # Update local cache from server data
                    self._update_local_cache_from_server(leaderboard, difficulty)
                else:
                    print(f"Failed to refresh {difficulty} data: {response.status_code}")
            
            return True
            
        except Exception as e:
            print(f"Error refreshing server data: {e}")
            return False
            
    def _update_local_cache_from_server(self, server_data: List[Dict[str, Any]], difficulty: str = None) -> None:
        """
        Update local cache with latest server data.
        This helps keep the local cache in sync with server data.
        
        Args:
            server_data: List of records from the server
            difficulty: The difficulty level for these records (for targeted clearing)
        """
        if not server_data:
            return
            
        try:
            # Begin transaction
            self.conn.isolation_level = 'EXCLUSIVE'
            self.conn.execute('BEGIN TRANSACTION')
            
            try:
                # Clear existing server-sourced records for this difficulty
                if difficulty:
                    print(f"Clearing server-sourced records for difficulty: {difficulty}")
                    self.cursor.execute(
                        "DELETE FROM game_stats WHERE source = 'server' AND difficulty = ?", 
                        (difficulty,)
                    )
                else:
                    # If no difficulty specified, clear all server records
                    print("Clearing all server-sourced records")
                    self.cursor.execute("DELETE FROM game_stats WHERE source = 'server'")
                
                # Then insert new records from server
                inserted_count = 0
                server_id_map = {}
                
                # First collect all IDs to avoid duplicates
                for item in server_data:
                    if 'id' in item:
                        server_id_map[item['id']] = item
                
                print(f"Processing {len(server_id_map)} unique server records")
                
                # Then insert records, using server IDs to avoid duplicates
                for server_id, item in server_id_map.items():
                    # Skip if missing required fields
                    if not all(k in item for k in ['player_name', 'difficulty', 'duration_seconds']):
                        continue
                        
                    # Extract fields from server data
                    player_name = item.get('player_name', 'Unknown')
                    record_difficulty = item.get('difficulty', 'Medium') 
                    duration = item.get('duration_seconds', 0)
                    errors = item.get('errors', 0)
                    
                    # Only insert if it matches our target difficulty (if specified)
                    if difficulty and record_difficulty != difficulty:
                        continue
                    
                    # Calculate synthetic start/end times
                    end_time = time.time()
                    start_time = end_time - duration
                    
                    # Calculate moves and matches based on errors
                    # This is an approximation since we don't know actual values
                    matches = item.get('matches', 8)  # Use actual matches if available
                    moves = matches + errors
                    
                    # Insert as server-sourced record, including the server ID
                    self.cursor.execute('''
                        INSERT INTO game_stats 
                        (player_name, difficulty, start_time, end_time, 
                         duration_seconds, moves, matches, errors, completed, source, server_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'server', ?)
                    ''', (player_name, record_difficulty, start_time, end_time, 
                         duration, moves, matches, errors, server_id))
                    
                    inserted_count += 1
                
                # Commit changes
                self.conn.commit()
                print(f"Updated local cache with {inserted_count} server records for {difficulty or 'all'} difficulty")
                
            except Exception as inner_e:
                # Rollback in case of error during processing
                self.conn.rollback()
                print(f"Error during server data processing, rolling back: {inner_e}")
                raise inner_e
                
        except Exception as e:
            print(f"Error updating local cache from server: {e}")
            # Make sure transaction is ended
            try:
                self.conn.rollback()
            except:
                pass
        finally:
            # Reset isolation level
            self.conn.isolation_level = None
    
    def _deduplicate_stats(self, stats_list):
        """
        Helper method to deduplicate stats by their unique game signatures.
        
        Args:
            stats_list: List of stats dictionaries to deduplicate
            
        Returns:
            List of deduplicated stats
        """
        # Only debug log if there are lots of stats (likely only during startup)
        if len(stats_list) > 5:
            print(f"Deduplicating {len(stats_list)} stats")
        
        # Deduplicate based on unique game signature using server ID if available
        unique_stats = {}
        for stat in stats_list:
            # If we have a server ID, use that as the primary key
            if "id" in stat:
                key = f"id_{stat['id']}"
            # Otherwise create a unique key from game properties
            else:
                # Use all available properties to create a truly unique key
                key_elements = [
                    f"p_{stat['player_name']}",
                    f"d_{stat['difficulty']}",
                    f"t_{float(stat['duration_seconds']):.2f}",
                    f"e_{stat.get('errors', 0)}"
                ]
                key = "_".join(key_elements)
            
            # If this key is already in use, decide which record to keep
            if key in unique_stats:
                # Prefer server data over local data
                if stat.get('source') == 'server' and unique_stats[key].get('source') == 'local':
                    unique_stats[key] = stat
            else:
                unique_stats[key] = stat
        
        # Create the final deduplicated list
        deduplicated_stats = list(unique_stats.values())
        
        orig_count = len(stats_list)
        dedup_count = len(deduplicated_stats)
        
        # Print details about what was removed only if significant deduplication happened
        if orig_count > dedup_count and orig_count > 5:
            print(f"Deduplicated stats: {orig_count} → {dedup_count} ({orig_count - dedup_count} removed)")
            
        # Return the deduplicated list
        return deduplicated_stats
        
    def get_player_stats(self, player_name: str) -> list:
        """
        Override the parent method to get player stats, ensuring no duplicates between 
        local and server records.
        
        Args:
            player_name: Name of the player
            
        Returns:
            List of dictionaries containing player's game stats with duplicates removed
        """
        try:
            if not self.conn:
                self.initialize_db()
            
            # Get all stats for this player, both local and server sourced
            self.cursor.execute('''
                SELECT id, player_name, difficulty, start_time, end_time, 
                       duration_seconds, moves, matches, errors, completed, source
                FROM game_stats 
                WHERE player_name = ?
                ORDER BY start_time DESC
            ''', (player_name,))
            
            all_stats = self.cursor.fetchall()
            
            # Convert to list of dictionaries
            columns = [col[0] for col in self.cursor.description]
            stats_dicts = [dict(zip(columns, row)) for row in all_stats]
            
            # Deduplicate the stats
            deduplicated_stats = self._deduplicate_stats(stats_dicts)
            
            return deduplicated_stats
            
        except sqlite3.Error as e:
            print(f"Error retrieving player stats: {e}")
            return []
    
    def get_player_remote_stats(self, player_name):
        """
        Get player stats from the remote server with fallback to local data.
        
        Args:
            player_name: The name of the player
            
        Returns:
            Dictionary containing player stats with consistent format:
            {
                "player": player_name,
                "stats": [...],  # Primary stats list (server if available, local if not)
                "local_stats": [...],  # Local-only stats when server available
                "has_local_data": bool,  # Whether local-only data exists
                "using_cached": bool,  # Whether we're using cached/offline data
                "error": str or None  # Error message if any
            }
        """
        try:
            if not self.online:
                return self._get_local_only_stats(player_name, "Server unavailable")
            
            base_url = self.server_url.rstrip('/')
            # Add cache-busting parameter to avoid stale data
            cache_buster = int(time.time())
            url = f"{base_url}/api/player/{player_name}?t={cache_buster}"
            
            try:
                response = requests.get(url, timeout=5)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                print(f"Connection error while getting remote player stats: {e}")
                self.using_cached_data = True
                return self._get_local_only_stats(player_name, f"Connection error: {e}")
            
            if response.status_code == 200:
                try:
                    server_data = response.json()
                except ValueError as e:
                    print(f"Error parsing server response: {e}")
                    return self._get_local_only_stats(player_name, f"Invalid server response: {e}")
                
                # Get local-only data (source='local') for this player
                query = '''
                    SELECT id, player_name, difficulty, start_time, end_time, 
                           duration_seconds, moves, matches, errors, completed, source
                    FROM game_stats 
                    WHERE player_name = ? AND source = 'local'
                '''
                
                self.cursor.execute(query, (player_name,))
                local_records = self.cursor.fetchall()
                
                local_stats = []
                for record in local_records:
                    stat_dict = {
                        "id": record[0],
                        "player_name": record[1],
                        "difficulty": record[2],
                        "start_time": record[3],
                        "end_time": record[4],
                        "duration_seconds": record[5],
                        "moves": record[6],
                        "matches": record[7],
                        "errors": record[8],
                        "completed": bool(record[9]),
                        "source": record[10],
                        "local": True
                    }
                    local_stats.append(stat_dict)
                
                # Mark server stats
                server_stats = server_data.get("stats", [])
                for stat in server_stats:
                    stat["server"] = True
                    stat["source"] = "server"  # Add source tag for deduplication
                
                # Deduplicate server stats
                deduplicated_server_stats = self._deduplicate_stats(server_stats)
                
                # Create combined data structure with consistent format
                return {
                    "player": player_name,
                    "stats": deduplicated_server_stats,  # Use server data as primary 
                    "local_stats": local_stats,  # Include local stats separately
                    "has_local_data": len(local_stats) > 0,
                    "using_cached": False,
                    "error": None
                }
            else:
                print(f"Error getting remote player stats: {response.status_code}")
                return self._get_local_only_stats(player_name, f"Server error: {response.status_code}")
                
        except Exception as e:
            print(f"Failed to get remote player stats: {e}")
            return self._get_local_only_stats(player_name, f"Error: {e}")
            
    def _get_local_only_stats(self, player_name, error_message):
        """
        Helper method to get local-only stats with consistent return format.
        
        Args:
            player_name: The name of the player
            error_message: Error message to include
            
        Returns:
            Dictionary with local stats in the same format as remote stats
        """
        self.using_cached_data = True
        print(f"Using local-only stats for {player_name} ({error_message})")
        
        # Only get local data
        query = '''
            SELECT id, player_name, difficulty, start_time, end_time, 
                   duration_seconds, moves, matches, errors, completed, source
            FROM game_stats 
            WHERE player_name = ? AND source = 'local'
        '''
        
        self.cursor.execute(query, (player_name,))
        records = self.cursor.fetchall()
        
        stats = []
        for record in records:
            stat_dict = {
                "id": record[0],
                "player_name": record[1],
                "difficulty": record[2],
                "start_time": record[3],
                "end_time": record[4],
                "duration_seconds": record[5],
                "moves": record[6],
                "matches": record[7],
                "errors": record[8],
                "completed": bool(record[9]),
                "source": record[10],
                "local": True,
                "cached": True
            }
            stats.append(stat_dict)
        
        # Deduplicate local stats
        deduplicated_stats = self._deduplicate_stats(stats)
        
        return {
            "player": player_name,
            "stats": deduplicated_stats,
            "local_stats": [],  # Empty since all stats are already in the main list
            "has_local_data": True,  # All data is local
            "using_cached": True,
            "error": error_message
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

    def clean_database(self):
        """
        Clean the database by removing all duplicates and ensuring proper schema.
        This is a utility function that can be called to fix duplicate records.
        """
        print("Cleaning database and removing duplicates...")
        try:
            # First ensure we have the proper columns
            self._ensure_source_column_exists()
            
            # Begin transaction
            self.conn.isolation_level = 'EXCLUSIVE'
            self.conn.execute('BEGIN TRANSACTION')
            
            try:
                # Get all stats
                self.cursor.execute('''
                    SELECT id, player_name, difficulty, duration_seconds, errors, 
                           completed, source, server_id
                    FROM game_stats
                ''')
                
                all_records = self.cursor.fetchall()
                print(f"Found {len(all_records)} total records")
                
                # Create a mapping of unique game signatures to record IDs
                # Prefer server records over local ones
                unique_records = {}
                local_ids_to_delete = []
                
                for record in all_records:
                    record_id = record[0]
                    player_name = record[1]
                    difficulty = record[2]
                    duration = record[3]
                    errors = record[4]
                    completed = record[5]
                    source = record[6]
                    server_id = record[7]
                    
                    # Create a unique key for this record
                    key = f"{player_name}_{difficulty}_{duration:.2f}_{errors}_{completed}"
                    
                    if server_id is not None:
                        # If we have a server ID, use that as a definitive key
                        server_key = f"server_{server_id}"
                        if server_key in unique_records:
                            # This is a true duplicate of a server record
                            local_ids_to_delete.append(record_id)
                        else:
                            unique_records[server_key] = record_id
                    elif key in unique_records:
                        # This is a duplicate based on game properties
                        local_ids_to_delete.append(record_id)
                    else:
                        unique_records[key] = record_id
                
                # Delete duplicate records
                if local_ids_to_delete:
                    placeholders = ','.join(['?'] * len(local_ids_to_delete))
                    self.cursor.execute(f'''
                        DELETE FROM game_stats
                        WHERE id IN ({placeholders})
                    ''', local_ids_to_delete)
                    
                    print(f"Deleted {len(local_ids_to_delete)} duplicate records")
                else:
                    print("No duplicates found")
                
                # Commit all changes
                self.conn.commit()
                print("Database cleaning completed successfully")
                
            except Exception as e:
                self.conn.rollback()
                print(f"Error during database cleaning: {e}")
        finally:
            # Reset isolation level
            self.conn.isolation_level = None


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