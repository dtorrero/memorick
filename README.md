# Memory Card Game

A Python-based memory card game with multiple difficulty levels, animations, player statistics tracking, and a persistent database for storing game results.

## Installation

### Requirements
- Python 3.11 (recommended)
- Python 3.13 is **not compatible** with PyGame
- Git (for cloning the repository)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/dtorrero/memorick
   cd memorick
   ```

2. **Create a virtual environment**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the game**
   ```bash
   python main.py
   ```

## How to Play

### Game Objective
Match pairs of cards with the same value by flipping them over two at a time. The game is completed when all pairs have been matched.

### Game Flow
1. **Start Screen**: Enter your name when prompted
2. **Main Menu**: Choose a difficulty level (Easy, Medium, Hard)
3. **Gameplay**: Click on cards to flip them and find matching pairs
4. **End Screen**: View your performance statistics when all pairs are matched
5. **Statistics**: Access detailed statistics and leaderboards from the main menu

### Controls
- **Mouse**: Click cards to flip them, and click buttons to navigate
- **ESC key**: Return to the main menu
- **Enter key**: Confirm selections and text input

### Difficulty Levels
- **Easy**: 4x4 grid (8 pairs)
- **Medium**: 6x6 grid (18 pairs)
- **Hard**: 10x10 grid (50 pairs)

### Game Features
- Real-time error counter and timer display
- Name personalization throughout the game
- Card flip animations and visual feedback
- Persistent statistics tracking
- Leaderboards for each difficulty level (sorted by completion time, with errors as a tiebreaker)

## Technical Architecture

### File Structure
- **main.py**: Main game file containing the GUI and game loop
- **classes.py**: Core game classes and logic
- **database.py**: Database functionality for storing and retrieving game statistics

### Key Classes

#### In classes.py:
- **Card**: Represents a single card with value, face-up/down state, and matching logic
- **Board**: Manages the collection of cards, card positions, and game state
- **Player**: Tracks player information, scores, and match statistics
- **Game**: Orchestrates game logic, connecting players and the board
- **ScoreBoard**: Manages game timing and statistics

#### In main.py:
- **GameGUI**: Handles rendering, user input, animations, and overall game flow

#### In database.py:
- **GameDatabase**: Manages SQLite operations for storing and retrieving game statistics

### Game Flow Architecture

1. **Initialization**:
   - GameGUI initializes the game window and settings
   - Player enters their name
   - Database connection is established

2. **Game Setup**:
   - Player selects difficulty level
   - Board is created with appropriate number of cards
   - Cards are randomly arranged in pairs

3. **Game Loop**:
   - Player clicks to flip cards
   - Game checks for matches
   - Real-time statistics are updated and displayed
   - Animations are rendered for card flips and matches

4. **Game Completion**:
   - All pairs are matched
   - Statistics are saved to the database
   - End screen shows performance metrics
   - Player can choose to play again or return to the menu

5. **Statistics Screen**:
   - Leaderboards display top players by time for each difficulty
   - Player's personal statistics are shown
   - Tabs allow navigation between difficulty levels

### Database Schema
The game uses an SQLite database (memory_game.db) with a single table:
- **game_stats**: Stores completed game information with fields for player name, difficulty, duration, moves, matches, errors, and completion status

The leaderboards rank players by completion time (fastest first), with errors as a secondary sorting criterion when times are equal.

### Database Modes
The game supports two database modes:
- **Local Database Only**: Game statistics are stored only on your device and are not shared with others
- **Remote Server**: Game statistics are stored on a remote server, allowing you to compete with other players. You can specify a custom server URL to connect to a shared leaderboard.

Both modes maintain separate databases, ensuring that your local stats remain private when desired, while still allowing for competitive play through the remote server option.

## Development Notes
- The game uses Pygame 2.5.2 for rendering and input handling
- SQLite is used for persistent storage without requiring external database setup
- The code is structured for easy modifications and extensions

## Docker Support

The project includes Docker support for both the client and server components.

### Running the Server with Docker

1. **Build and run the server container**:
   ```bash
   docker-compose up server
   ```

   This will start the statistics server on port 5000. The server data is stored in a Docker volume for persistence.

2. **Access the server**:
   - Dashboard: http://localhost:5000
   - API endpoints: http://localhost:5000/api/stats/...

### Running the Client with Docker

Running the client in Docker requires X11 forwarding to display the graphical interface.

#### On Linux:

1. **Allow X server connections**:
   ```bash
   xhost +local:docker
   ```

2. **Edit docker-compose.yml** to uncomment the client service.

3. **Run the client**:
   ```bash
   docker-compose up client
   ```

#### On Windows/macOS:

Due to the graphical nature of the client, it's recommended to run the client natively on Windows and macOS. However, you can still use Docker for the server component.

### Building Images Separately

If needed, you can build the Docker images separately:

```bash
# Build the server image
docker build -t memory-game-server -f Dockerfile.server .

# Build the client image
docker build -t memory-game-client -f Dockerfile.client .
```

Then run them individually:

```bash
# Run the server
docker run -p 5000:5000 memory-game-server

# Run the client (Linux only, with X11 forwarding)
docker run -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix memory-game-client
```

## Concurrency and Reliability

The game implements robust mechanisms to ensure data integrity and reliability when multiple players use the system simultaneously:

### Retry System for Data Persistence

The client includes an intelligent retry system for saving game statistics to the server:

- **Automatic Retries**: Failed save operations automatically retry up to 5 times
- **Exponential Backoff**: Each retry uses an increasing delay (1s, 2s, 4s, 8s, 16s) to avoid overwhelming the server
- **Smart Error Handling**: Only retries on server errors (5xx) or rate limiting (429), not on client errors (most 4xx)
- **Increasing Timeouts**: Each retry attempt gets a progressively longer timeout, from 10s to 30s
- **Random Jitter**: Added randomization to delay times to prevent multiple clients retrying simultaneously

### Duplicate Prevention

The server implements comprehensive duplicate detection to prevent the same game record from being saved multiple times:

- **Multi-Field Matching**: Uses client ID, local record ID, player name, and precise timestamps to identify duplicates
- **Conflict Responses**: Returns HTTP 409 (Conflict) when duplicates are detected, along with the existing record ID
- **Database Indices**: Optimized database schema with indices for efficient duplicate detection
- **Transparent Handling**: Players don't see any difference in behavior when retries or duplicate detection occur

### Benefits

These mechanisms provide several key advantages:

- **Data Integrity**: Ensures game statistics are reliably saved even during high server load
- **Consistent Experience**: Players always see their completed games in the leaderboards
- **Server Protection**: Prevents server overload during concurrent game completions
- **Transparent Operation**: All reliability mechanisms work silently in the background

The system is designed to handle 10+ concurrent players without data loss or duplicate entries, even when using SQLite as the database backend.
