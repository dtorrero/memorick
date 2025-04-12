"""
Memory Game Statistics Server

A simple Flask server that handles game statistics
for the Memory Card Game.
"""
import os
import sys
import sqlite3
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template

# Add parent directory to path to allow importing shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.models import GameStats

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server/server_stats.db")

def init_db():
    """Initialize the database if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create game_stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            duration_seconds REAL NOT NULL,
            moves INTEGER NOT NULL,
            matches INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            completed BOOLEAN NOT NULL,
            sync_time REAL NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

@app.route('/')
def index():
    """Serve a simple dashboard page."""
    return """
    <html>
        <head>
            <title>Memory Game Statistics Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #2c3e50; }
                .stats { margin: 20px 0; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .footer { margin-top: 30px; color: #7f8c8d; font-size: 12px; }
            </style>
        </head>
        <body>
            <h1>Memory Game Statistics Server</h1>
            <p>This server collects and provides statistics for the Memory Card Game.</p>
            
            <div class="stats">
                <h2>API Endpoints:</h2>
                <ul>
                    <li>/api/stats/save - POST: Save new statistics</li>
                    <li>/api/stats/leaderboard/:difficulty - GET: Get leaderboard for a difficulty</li>
                    <li>/api/stats/player/:name - GET: Get statistics for a specific player</li>
                </ul>
            </div>
            
            <div class="footer">
                Memory Game Statistics Server - Running on Flask
            </div>
        </body>
    </html>
    """

@app.route('/api/stats/save', methods=['POST'])
def save_stats():
    """Save game statistics from the client."""
    try:
        data = request.json
        print(f"Received save request with data: {data}")
        
        # Validate required fields
        required_fields = ['player_name', 'difficulty', 'start_time', 
                          'end_time', 'moves', 'matches', 'completed']
        
        for field in required_fields:
            if field not in data:
                print(f"Missing required field: {field}")
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Calculate derived fields if not provided
        if 'duration_seconds' not in data:
            data['duration_seconds'] = data['end_time'] - data['start_time']
        
        if 'errors' not in data:
            data['errors'] = max(0, data['moves'] - data['matches'])
        
        # Add sync time
        sync_time = time.time()
        
        # Log client ID if provided
        client_id = data.get('client_id', 'unknown')
        print(f"Saving game stats from client: {client_id}")
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO game_stats (
                player_name, difficulty, start_time, end_time, 
                duration_seconds, moves, matches, errors, completed, sync_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['player_name'], data['difficulty'], data['start_time'], 
            data['end_time'], data['duration_seconds'], data['moves'], 
            data['matches'], data['errors'], data['completed'], sync_time
        ))
        
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        print(f"Successfully saved stats with ID: {record_id}")
        return jsonify({
            "success": True, 
            "message": "Statistics saved successfully",
            "id": record_id
        })
    
    except Exception as e:
        print(f"Error saving stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/leaderboard/<difficulty>', methods=['GET'])
def get_leaderboard(difficulty):
    """Get leaderboard for a specific difficulty."""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # For 'all' difficulty, don't filter by difficulty
        if difficulty.lower() == 'all':
            cursor.execute('''
                SELECT id, player_name, difficulty, duration_seconds, errors
                FROM game_stats
                WHERE completed = 1
                ORDER BY duration_seconds ASC, errors ASC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT id, player_name, difficulty, duration_seconds, errors
                FROM game_stats
                WHERE difficulty = ? AND completed = 1
                ORDER BY duration_seconds ASC, errors ASC
                LIMIT ?
            ''', (difficulty, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Format times for display
        for result in results:
            minutes = int(result['duration_seconds'] // 60)
            seconds = result['duration_seconds'] % 60
            result['formatted_time'] = f"{minutes:02d}:{seconds:05.2f}"
        
        return jsonify({"leaderboard": results})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/player/<name>', methods=['GET'])
def get_player_stats(name):
    """Get statistics for a specific player."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, player_name, difficulty, start_time, end_time, 
                   duration_seconds, moves, matches, errors, completed
            FROM game_stats
            WHERE player_name = ?
            ORDER BY start_time DESC
        ''', (name,))
        
        results = [dict(row) for row in cursor.fetchall()]
        
        # Calculate aggregate stats
        difficulty_stats = {}
        total_games = len(results)
        total_completed = sum(1 for r in results if r['completed'])
        
        for difficulty in ['Easy', 'Medium', 'Hard']:
            diff_games = [r for r in results if r['difficulty'] == difficulty]
            diff_completed = [r for r in diff_games if r['completed']]
            
            if diff_completed:
                best_time = min(r['duration_seconds'] for r in diff_completed)
                avg_time = sum(r['duration_seconds'] for r in diff_completed) / len(diff_completed)
            else:
                best_time = None
                avg_time = None
            
            difficulty_stats[difficulty] = {
                'total_games': len(diff_games),
                'completed_games': len(diff_completed),
                'best_time': best_time,
                'avg_time': avg_time
            }
        
        conn.close()
        
        return jsonify({
            "player": name,
            "total_games": total_games,
            "completed_games": total_completed,
            "difficulty_stats": difficulty_stats,
            "recent_games": results[:10]  # Only return 10 most recent
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Initialize the database on startup
    init_db()
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Start the server
    app.run(host='0.0.0.0', port=port, debug=True)
    print(f"Server running on http://localhost:{port}") 