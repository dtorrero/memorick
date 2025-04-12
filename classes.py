import random
import time
from typing import List, Tuple, Optional


class Card:
    """
    A class representing a memory card in the memory card game.
    Each card has a value, can be face up or face down, and can be matched or unmatched.
    """
    
    def __init__(self, value, card_id=None):
        """
        Initialize a new card.
        
        Args:
            value: The value/content of the card (what the player sees when it's face up)
            card_id: Optional unique identifier for the card
        """
        self.value = value
        self.card_id = card_id
        self.is_face_up = False
        self.is_matched = False
    
    def flip(self):
        """Flip the card over (change its face up status)."""
        self.is_face_up = not self.is_face_up
    
    def match(self):
        """Mark the card as matched."""
        self.is_matched = True
    
    def reset(self):
        """Reset the card to its initial state (face down and unmatched)."""
        self.is_face_up = False
        self.is_matched = False
    
    def __str__(self):
        """Return a string representation of the card."""
        status = "matched" if self.is_matched else "face up" if self.is_face_up else "face down"
        return f"Card({self.value}, {status})"
    
    def __repr__(self):
        """Return a detailed string representation of the card."""
        return f"Card(value={self.value}, card_id={self.card_id}, is_face_up={self.is_face_up}, is_matched={self.is_matched})"


class Board:
    """
    A class representing the game board for the memory card game.
    This manages the collection of cards, game setup, and game state.
    """
    
    def __init__(self, card_values, rows=4, cols=4):
        """
        Initialize a new game board.
        
        Args:
            card_values: List of values to create pairs from
            rows: Number of rows in the grid
            cols: Number of columns in the grid
        """
        self.rows = rows
        self.cols = cols
        self.cards = []
        self.flipped_cards = []
        self.moves = 0
        self.matches = 0
        
        # Ensure we have the right number of card values
        total_cards = rows * cols
        if total_cards % 2 != 0:
            raise ValueError("Total number of cards must be even")
        
        pairs_needed = total_cards // 2
        
        # Make sure we have enough card values
        if len(card_values) < pairs_needed:
            raise ValueError(f"Not enough card values. Need at least {pairs_needed} values.")
        
        # Use only the number of card values we need
        selected_values = card_values[:pairs_needed]
        
        # Create pairs of cards
        card_list = []
        for i, value in enumerate(selected_values):
            card_list.append(Card(value, card_id=i*2))
            card_list.append(Card(value, card_id=i*2+1))
        
        # Shuffle the cards
        random.shuffle(card_list)
        
        # Place cards on the board
        self.cards = card_list
    
    def get_card(self, row, col) -> Optional[Card]:
        """
        Get the card at the specified position.
        
        Args:
            row: Row index
            col: Column index
            
        Returns:
            Card at the specified position or None if position is invalid
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            index = row * self.cols + col
            if 0 <= index < len(self.cards):
                return self.cards[index]
        return None
    
    def get_card_position(self, card_id) -> Tuple[int, int]:
        """
        Get the position of a card by its ID.
        
        Args:
            card_id: The ID of the card to find
            
        Returns:
            Tuple of (row, col) or (-1, -1) if not found
        """
        for i, card in enumerate(self.cards):
            if card.card_id == card_id:
                return divmod(i, self.cols)
        return (-1, -1)
    
    def flip_card(self, row, col) -> bool:
        """
        Flip a card at the specified position.
        
        Args:
            row: Row index
            col: Column index
            
        Returns:
            True if flip was successful, False otherwise
        """
        card = self.get_card(row, col)
        if card and not card.is_matched and not card.is_face_up:
            card.flip()
            self.flipped_cards.append(card)
            
            # If we have flipped two cards, check for a match
            if len(self.flipped_cards) == 2:
                self.moves += 1
                if self.flipped_cards[0].value == self.flipped_cards[1].value:
                    # We have a match
                    self.flipped_cards[0].match()
                    self.flipped_cards[1].match()
                    self.matches += 1
                    self.flipped_cards = []
                    return True
            return True
        return False
    
    def reset_unmatched(self) -> None:
        """Reset all unmatched cards to face down."""
        for card in self.cards:
            if not card.is_matched and card.is_face_up:
                card.flip()
        self.flipped_cards = []
    
    def reset_game(self) -> None:
        """Reset the entire game board."""
        random.shuffle(self.cards)
        for card in self.cards:
            card.reset()
        self.flipped_cards = []
        self.moves = 0
        self.matches = 0
    
    def is_game_over(self) -> bool:
        """Check if all pairs have been matched."""
        return self.matches == len(self.cards) // 2
    
    def __str__(self) -> str:
        """Return a string representation of the board."""
        result = []
        for row in range(self.rows):
            row_cards = []
            for col in range(self.cols):
                card = self.get_card(row, col)
                if card:
                    if card.is_matched:
                        row_cards.append("M")
                    elif card.is_face_up:
                        row_cards.append(str(card.value))
                    else:
                        row_cards.append("#")
                else:
                    row_cards.append("?")
            result.append(" ".join(row_cards))
        return "\n".join(result)


class Player:
    """
    A class representing a player in the memory card game.
    Tracks player information and score.
    """
    
    def __init__(self, name="Player"):
        """
        Initialize a new player.
        
        Args:
            name: The player's name
        """
        self.name = name
        self.score = 0
        self.moves = 0
        self.matches = 0
        self.best_time = float('inf')
    
    def add_match(self):
        """
        Add a match to the player's score.
        
        Returns:
            The updated score
        """
        self.matches += 1
        self.score += 10  # Base points for a match
        return self.score
    
    def add_move(self):
        """Increment the player's move counter."""
        self.moves += 1
    
    def update_best_time(self, time_seconds):
        """
        Update the player's best time if the current time is better.
        
        Args:
            time_seconds: The time in seconds for the current game
        """
        if time_seconds < self.best_time:
            self.best_time = time_seconds
    
    def reset_stats(self):
        """Reset the player's stats for a new game."""
        self.moves = 0
        self.matches = 0
    
    def __str__(self):
        """Return a string representation of the player."""
        return f"{self.name}: Score={self.score}, Matches={self.matches}, Moves={self.moves}"


class ScoreBoard:
    """
    A class for tracking and displaying scores in the memory card game.
    """
    
    def __init__(self):
        """Initialize a new scoreboard."""
        self.high_scores = []
        self.current_game_stats = {
            "player": None,
            "start_time": 0,
            "end_time": 0,
            "moves": 0,
            "matches": 0
        }
    
    def start_game(self, player):
        """
        Start tracking a new game.
        
        Args:
            player: The Player object
        """
        self.current_game_stats["player"] = player
        self.current_game_stats["start_time"] = time.time()
        self.current_game_stats["moves"] = 0
        self.current_game_stats["matches"] = 0
    
    def end_game(self):
        """
        End the current game and calculate statistics.
        
        Returns:
            Dictionary with game statistics
        """
        self.current_game_stats["end_time"] = time.time()
        game_time = self.current_game_stats["end_time"] - self.current_game_stats["start_time"]
        
        player = self.current_game_stats["player"]
        if player:
            player.update_best_time(game_time)
        
        game_stats = {
            "player": player.name if player else "Unknown",
            "score": player.score if player else 0,
            "moves": player.moves,
            "matches": player.matches,
            "time": game_time
        }
        
        self.high_scores.append(game_stats)
        self.high_scores.sort(key=lambda x: x["score"], reverse=True)
        self.high_scores = self.high_scores[:10]  # Keep only top 10
        
        return game_stats
    
    def get_high_scores(self, limit=10):
        """
        Get the top high scores.
        
        Args:
            limit: Maximum number of scores to return
            
        Returns:
            List of high score dictionaries
        """
        return self.high_scores[:limit]
    
    def __str__(self):
        """Return a string representation of the high scores."""
        if not self.high_scores:
            return "No high scores yet!"
        
        result = ["===== HIGH SCORES ====="]
        for i, score in enumerate(self.high_scores):
            result.append(f"{i+1}. {score['player']}: {score['score']} (Moves: {score['moves']}, Time: {score['time']:.1f}s)")
        
        return "\n".join(result)


class Game:
    """
    Main game class that orchestrates the memory card game.
    """
    
    def __init__(self, card_values=None, rows=4, cols=4, player_name="Player"):
        """
        Initialize a new memory card game.
        
        Args:
            card_values: List of values for the cards (defaults to numbers)
            rows: Number of rows in the board
            cols: Number of columns in the board
            player_name: Name of the player
        """
        # Default card values if none provided
        if card_values is None:
            # Create enough unique values for the board size
            pairs_needed = (rows * cols) // 2
            
            # For a large grid, use a combination of numbers and letters
            if pairs_needed > 26:
                numbers = list(range(1, 26))
                letters = [chr(ord('A') + i) for i in range(26)]
                symbols = ['@', '#', '$', '%', '&', '*', '+', '=', '!', '?']
                card_values = numbers + letters + symbols
                # Add numbered letters if we need even more values
                if pairs_needed > len(card_values):
                    extra_values = [f"{letter}{num}" for letter in ['A', 'B', 'C'] for num in range(1, 10)]
                    card_values.extend(extra_values[:pairs_needed - len(card_values)])
            else:
                card_values = list(range(1, pairs_needed + 1))
        
        self.board = Board(card_values, rows, cols)
        self.player = Player(player_name)
        self.scoreboard = ScoreBoard()
        self.game_active = False
        self.last_flip_time = 0
        self.reveal_duration = 1.0  # seconds to show unmatched cards
    
    def start_game(self):
        """Start a new game."""
        self.board.reset_game()
        self.player.reset_stats()
        self.game_active = True
        self.scoreboard.start_game(self.player)
        return "Game started! Flip cards to find matches."
    
    def flip_card(self, row, col):
        """
        Flip a card and process the game logic.
        
        Args:
            row: Row index
            col: Column index
            
        Returns:
            String describing what happened
        """
        if not self.game_active:
            return "Game not active. Start a new game first."
        
        # Check if we need to reset unmatched cards first
        if len(self.board.flipped_cards) == 2:
            self.board.reset_unmatched()
        
        result = self.board.flip_card(row, col)
        
        if not result:
            return "Invalid move. Try again."
        
        # Get the card that was just flipped
        card = self.board.get_card(row, col)
        
        # If this completes a pair of flipped cards
        if len(self.board.flipped_cards) == 2:
            self.player.add_move()
            
            # Check if it's a match
            if self.board.flipped_cards[0].value == self.board.flipped_cards[1].value:
                self.player.add_match()
                message = f"Match found! {card.value}"
                
                # Check if the game is over
                if self.board.is_game_over():
                    self.game_active = False
                    game_stats = self.scoreboard.end_game()
                    return f"Match found! {card.value}\nGame Over! You completed the game in {self.player.moves} moves and {game_stats['time']:.1f} seconds."
                
                return message
            else:
                self.last_flip_time = time.time()
                return f"No match. Cards will flip back in {self.reveal_duration} seconds."
        
        return f"Card flipped: {card.value}"
    
    def update(self):
        """
        Update game state - should be called regularly in a game loop.
        
        Returns:
            True if an update occurred, False otherwise
        """
        if self.game_active and len(self.board.flipped_cards) == 2:
            # If there are two unmatched cards flipped and time has passed
            if time.time() - self.last_flip_time > self.reveal_duration:
                if self.board.flipped_cards[0].value != self.board.flipped_cards[1].value:
                    self.board.reset_unmatched()
                    return True
        return False
    
    def get_board_state(self):
        """
        Get the current state of the board as a 2D array.
        
        Returns:
            2D array representing the board state
        """
        board_state = []
        for row in range(self.board.rows):
            row_state = []
            for col in range(self.board.cols):
                card = self.board.get_card(row, col)
                if card:
                    if card.is_matched:
                        row_state.append("M")  # Matched
                    elif card.is_face_up:
                        row_state.append(str(card.value))  # Face up, showing value
                    else:
                        row_state.append("?")  # Face down
                else:
                    row_state.append(" ")  # Empty
            board_state.append(row_state)
        return board_state
    
    def __str__(self):
        """Return a string representation of the game state."""
        game_status = "Active" if self.game_active else "Inactive"
        return f"Game Status: {game_status}\n{self.player}\n{self.board}"
    
    def check_match(self, row1, col1, row2, col2):
        """
        Check if two cards match and process the result.
        
        Args:
            row1: Row index of first card
            col1: Column index of first card
            row2: Row index of second card
            col2: Column index of second card
            
        Returns:
            String describing what happened
        """
        if not self.game_active:
            return "Game not active. Start a new game first."
        
        card1 = self.board.get_card(row1, col1)
        card2 = self.board.get_card(row2, col2)
        
        if not card1 or not card2:
            return "Invalid card position"
        
        if not card1.is_face_up or not card2.is_face_up:
            return "Cards must be face up to check match"
        
        if card1.card_id == card2.card_id:
            return "Same card selected twice"
        
        # Record the move
        self.player.add_move()
        
        # Check if it's a match
        if card1.value == card2.value:
            card1.match()
            card2.match()
            self.player.add_match()
            
            # Check if the game is over
            if self.board.is_game_over():
                self.game_active = False
                game_stats = self.scoreboard.end_game()
                return f"Match found! {card1.value}\nGame Over! You completed the game in {self.player.moves} moves and {game_stats['time']:.1f} seconds."
            
            return f"Match found! {card1.value}"
        else:
            # No match found
            return "No match found"
