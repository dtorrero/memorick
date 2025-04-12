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
   git clone https://github.com/yourusername/memorick.git
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
- Leaderboards for each difficulty level

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

## Development Notes
- The game uses Pygame 2.5.2 for rendering and input handling
- SQLite is used for persistent storage without requiring external database setup
- The code is structured for easy modifications and extensions
