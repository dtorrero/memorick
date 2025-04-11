import pygame
import sys
import time
import gc  # Import garbage collector module at the top level
import math
from classes import Card, Board, Player, Game

# Memory optimization - limit pygame features we don't need
pygame.display.init()
pygame.font.init()
# Don't initialize audio if not needed
# pygame.mixer.init()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (0, 100, 255)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
YELLOW = (255, 255, 0)
CARD_BACK_COLOR = (50, 50, 200)
CARD_FRONT_COLOR = (220, 220, 255)
CARD_MATCHED_COLOR = (200, 255, 200)

# Fonts
FONT_SMALL = pygame.font.SysFont('Arial', 20)
FONT_MEDIUM = pygame.font.SysFont('Arial', 30)
FONT_LARGE = pygame.font.SysFont('Arial', 40)
FONT_CARD = pygame.font.SysFont('Arial', 36, bold=True)

# Game settings
FPS = 60
CARD_MARGIN = 10
ANIMATION_SPEED = 5  # Frames per animation step


class GameGUI:
    """Graphical user interface for the memory card game."""
    
    def __init__(self):
        """Initialize the game GUI."""
        self.game = None
        self.clock = pygame.time.Clock()
        self.screen = None
        self.width = 800
        self.height = 600
        self.card_width = 80
        self.card_height = 100
        self.board_margin_top = 120
        self.board_margin_left = 0
        self.message = ""
        self.message_timer = 0
        self.flipping_cards = []  # [(card, start_time, is_flipping_up)]
        
        # Animation states
        self.cards_to_flip_back = []
        self.match_animation_active = False
        self.match_animation_start = 0
        self.match_animation_cards = []
        
        # Shake animation for mismatched cards
        self.shake_animation_active = False
        self.shake_animation_start = 0
        self.shake_animation_cards = []
        self.shake_amplitude = 5  # Pixels to shake
        self.shake_duration = 0.5  # Seconds
        
        # Memory management
        self.last_gc_time = 0
        self.text_cache = {}  # Cache for rendered text
    
    def setup_window(self):
        """Set up the game window."""
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Memory Card Game")
    
    def show_start_screen(self):
        """Show the game start screen and get player settings."""
        self.screen.fill(WHITE)
        
        # Title
        title = FONT_LARGE.render("MEMORY CARD GAME", True, BLUE)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 80))
        
        # Instructions
        instructions = [
            "Find matching pairs of cards",
            "Select difficulty level:"
        ]
        
        for i, line in enumerate(instructions):
            text = FONT_SMALL.render(line, True, BLACK)
            self.screen.blit(text, (self.width // 2 - text.get_width() // 2, 150 + i * 30))
        
        # Create difficulty buttons
        button_width = 200
        button_height = 60
        button_margin = 20
        button_y_start = 250
        
        # Define button areas
        easy_rect = pygame.Rect(self.width // 2 - button_width // 2, button_y_start, button_width, button_height)
        medium_rect = pygame.Rect(self.width // 2 - button_width // 2, button_y_start + button_height + button_margin, button_width, button_height)
        hard_rect = pygame.Rect(self.width // 2 - button_width // 2, button_y_start + (button_height + button_margin) * 2, button_width, button_height)
        
        # Main loop for start screen
        difficulty = None
        waiting = True
        
        while waiting:
            # Get mouse position for hover effects
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = False
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        difficulty = 1
                        waiting = False
                    elif event.key == pygame.K_2:
                        difficulty = 2
                        waiting = False
                    elif event.key == pygame.K_3:
                        difficulty = 3
                        waiting = False
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        mouse_clicked = True
            
            # Draw buttons with hover effects
            # Easy Button
            button_color = BLUE if easy_rect.collidepoint(mouse_pos) else (100, 100, 255)
            if mouse_clicked and easy_rect.collidepoint(mouse_pos):
                difficulty = 1
                waiting = False
            pygame.draw.rect(self.screen, button_color, easy_rect, 0, 10)
            pygame.draw.rect(self.screen, WHITE, easy_rect, 2, 10)
            text = FONT_MEDIUM.render("Easy", True, WHITE)
            self.screen.blit(text, (easy_rect.centerx - text.get_width() // 2, easy_rect.centery - text.get_height() // 2))
            
            # Medium Button
            button_color = BLUE if medium_rect.collidepoint(mouse_pos) else (100, 100, 255)
            if mouse_clicked and medium_rect.collidepoint(mouse_pos):
                difficulty = 2
                waiting = False
            pygame.draw.rect(self.screen, button_color, medium_rect, 0, 10)
            pygame.draw.rect(self.screen, WHITE, medium_rect, 2, 10)
            text = FONT_MEDIUM.render("Medium", True, WHITE)
            self.screen.blit(text, (medium_rect.centerx - text.get_width() // 2, medium_rect.centery - text.get_height() // 2))
            
            # Hard Button
            button_color = BLUE if hard_rect.collidepoint(mouse_pos) else (100, 100, 255)
            if mouse_clicked and hard_rect.collidepoint(mouse_pos):
                difficulty = 3
                waiting = False
            pygame.draw.rect(self.screen, button_color, hard_rect, 0, 10)
            pygame.draw.rect(self.screen, WHITE, hard_rect, 2, 10)
            text = FONT_MEDIUM.render("Hard", True, WHITE)
            self.screen.blit(text, (hard_rect.centerx - text.get_width() // 2, hard_rect.centery - text.get_height() // 2))
            
            pygame.display.flip()
            self.clock.tick(FPS)
        
        # Set up game based on difficulty
        if difficulty == 1:
            rows, cols = 4, 4  # Easy: 4x4 grid
        elif difficulty == 2:
            rows, cols = 6, 6  # Medium: 6x6 grid
        else:
            rows, cols = 10, 10  # Hard: 10x10 grid
        
        # Adjust card size based on grid
        max_card_width = (self.width - CARD_MARGIN * (cols + 1)) // cols
        max_card_height = (self.height - self.board_margin_top - CARD_MARGIN * (rows + 1)) // rows
        
        # Keep aspect ratio and ensure minimum size for hard difficulty
        if rows == 10:  # Hard difficulty needs smaller cards
            self.card_width = min(max_card_width, max_card_height * 0.8, 60)  # Limit max size for 10x10
            self.board_margin_top = 100  # Reduce top margin to give more space
        else:
            self.card_width = min(max_card_width, max_card_height * 0.8)
            
        self.card_height = self.card_width * 1.25
        
        # Center the board
        self.board_margin_left = (self.width - (cols * self.card_width + (cols - 1) * CARD_MARGIN)) // 2
        
        return rows, cols
    
    def get_card_rect(self, row, col):
        """Get the rectangle for a card at the given position."""
        x = self.board_margin_left + col * (self.card_width + CARD_MARGIN)
        y = self.board_margin_top + row * (self.card_height + CARD_MARGIN)
        return pygame.Rect(x, y, self.card_width, self.card_height)
    
    def get_card_at_pos(self, pos):
        """Get the card at the given screen position."""
        for row in range(self.game.board.rows):
            for col in range(self.game.board.cols):
                rect = self.get_card_rect(row, col)
                if rect.collidepoint(pos):
                    return row, col
        return None
    
    def draw_card(self, card, rect, flip_progress=None):
        """Draw a card on the screen."""
        if flip_progress is not None:
            # Calculate card width during flip animation (simulate 3D by changing width)
            adjusted_width = abs(self.card_width * (0.5 - flip_progress) * 2)
            adjusted_rect = pygame.Rect(
                rect.centerx - adjusted_width / 2,
                rect.y,
                adjusted_width,
                rect.height
            )
            
            # Determine if showing front or back during animation
            showing_front = flip_progress >= 0.5
            
            if showing_front:
                # Front of card (second half of animation)
                pygame.draw.rect(self.screen, CARD_FRONT_COLOR, adjusted_rect, 0, 5)
                pygame.draw.rect(self.screen, BLUE, adjusted_rect, 2, 5)
                
                # Only show text if the card is wide enough to be readable
                if adjusted_width > self.card_width * 0.3:
                    if card.is_matched:
                        color = GREEN
                    else:
                        color = BLACK
                    text = FONT_CARD.render(str(card.value), True, color)
                    self.screen.blit(text, (adjusted_rect.centerx - text.get_width() // 2, 
                                          adjusted_rect.centery - text.get_height() // 2))
            else:
                # Back of card (first half of animation)
                pygame.draw.rect(self.screen, CARD_BACK_COLOR, adjusted_rect, 0, 5)
                pygame.draw.rect(self.screen, BLUE, adjusted_rect, 2, 5)
                
                # Card back design (simple pattern)
                if adjusted_width > self.card_width * 0.3:
                    for i in range(3):
                        for j in range(4):
                            x = adjusted_rect.left + adjusted_width * (i + 1) / 4
                            y = adjusted_rect.top + adjusted_rect.height * (j + 1) / 5
                            pygame.draw.circle(self.screen, WHITE, (x, y), 3)
        else:
            # No animation, just draw the card
            if card.is_matched:
                # Matched cards
                pygame.draw.rect(self.screen, CARD_MATCHED_COLOR, rect, 0, 5)
                pygame.draw.rect(self.screen, GREEN, rect, 2, 5)
                text = FONT_CARD.render(str(card.value), True, GREEN)
                self.screen.blit(text, (rect.centerx - text.get_width() // 2, 
                                      rect.centery - text.get_height() // 2))
            elif card.is_face_up:
                # Face up cards
                pygame.draw.rect(self.screen, CARD_FRONT_COLOR, rect, 0, 5)
                pygame.draw.rect(self.screen, BLUE, rect, 2, 5)
                text = FONT_CARD.render(str(card.value), True, BLACK)
                self.screen.blit(text, (rect.centerx - text.get_width() // 2, 
                                      rect.centery - text.get_height() // 2))
            else:
                # Face down cards
                pygame.draw.rect(self.screen, CARD_BACK_COLOR, rect, 0, 5)
                pygame.draw.rect(self.screen, BLUE, rect, 2, 5)
                
                # Card back design (simple pattern)
                for i in range(3):
                    for j in range(4):
                        x = rect.left + rect.width * (i + 1) / 4
                        y = rect.top + rect.height * (j + 1) / 5
                        pygame.draw.circle(self.screen, WHITE, (x, y), 3)
    
    def update_animations(self):
        """Update all animations."""
        current_time = pygame.time.get_ticks()
        
        # Update card flip animations - clear the list when done instead of creating a new one
        i = 0
        while i < len(self.flipping_cards):
            card, start_time, is_flipping_up = self.flipping_cards[i]
            elapsed = (current_time - start_time) / 1000.0
            duration = 0.3  # seconds
            
            if elapsed < duration:
                i += 1  # Keep this animation
            else:
                # Remove completed animation
                self.flipping_cards.pop(i)
        
        # Check for match animation
        if self.match_animation_active:
            elapsed = (current_time - self.match_animation_start) / 1000.0
            if elapsed > 0.5:  # Duration of match animation
                self.match_animation_active = False
                self.match_animation_cards = []  # Clear reference to cards
        
        # Check for shake animation
        if self.shake_animation_active:
            elapsed = (current_time - self.shake_animation_start) / 1000.0
            if elapsed > self.shake_duration:
                self.shake_animation_active = False
                self.shake_animation_cards = []
    
    def draw_board(self):
        """Draw the game board and all cards."""
        for row in range(self.game.board.rows):
            for col in range(self.game.board.cols):
                card = self.game.board.get_card(row, col)
                rect = self.get_card_rect(row, col)
                
                # Apply shake animation to mismatched cards
                if self.shake_animation_active and card in self.shake_animation_cards:
                    elapsed = (pygame.time.get_ticks() - self.shake_animation_start) / 1000.0
                    frequency = 15  # Higher = faster shake
                    progress = min(1.0, elapsed / self.shake_duration)
                    
                    # Decreasing amplitude as animation progresses
                    current_amplitude = self.shake_amplitude * (1 - progress)
                    
                    # Calculate horizontal offset based on sine wave
                    offset_x = current_amplitude * math.sin(elapsed * frequency * math.pi)
                    
                    # Adjust rectangle for drawing
                    shake_rect = rect.copy()
                    shake_rect.x += offset_x
                    
                    # Draw the card with shake effect
                    self.draw_card(card, shake_rect)
                    continue
                
                # Check if this card is being animated
                animated = False
                for anim_card, start_time, is_flipping_up in self.flipping_cards:
                    if anim_card.card_id == card.card_id:
                        elapsed = (pygame.time.get_ticks() - start_time) / 1000.0
                        duration = 0.3  # seconds
                        progress = elapsed / duration
                        if not is_flipping_up:
                            progress = 1 - progress
                        self.draw_card(card, rect, progress)
                        animated = True
                        break
                
                # If not animated, draw normally
                if not animated:
                    # Check if this card is in match animation
                    if self.match_animation_active and card in self.match_animation_cards:
                        # Make matched cards pulse
                        elapsed = (pygame.time.get_ticks() - self.match_animation_start) / 1000.0
                        pulse = 1.0 + 0.2 * abs(elapsed * 4 % 2 - 1)
                        pulse_rect = pygame.Rect(
                            rect.centerx - rect.width * pulse / 2,
                            rect.centery - rect.height * pulse / 2,
                            rect.width * pulse,
                            rect.height * pulse
                        )
                        self.draw_card(card, pulse_rect)
                    else:
                        self.draw_card(card, rect)
    
    def render_text(self, font, text, color, force_refresh=False):
        """Render and cache text to avoid recreating text surfaces."""
        cache_key = (font, text, color)
        if force_refresh or cache_key not in self.text_cache:
            self.text_cache[cache_key] = font.render(text, True, color)
        return self.text_cache[cache_key]
    
    def draw_ui(self):
        """Draw the user interface elements."""
        # Remove player stats info from UI during gameplay
        
        # Only show game message
        if self.message and pygame.time.get_ticks() < self.message_timer:
            message_text = self.render_text(FONT_MEDIUM, self.message, BLUE)
            self.screen.blit(message_text, (self.width // 2 - message_text.get_width() // 2, 50))
    
    def show_message(self, message, duration=2000):
        """Show a message for a duration in milliseconds."""
        self.message = message
        self.message_timer = pygame.time.get_ticks() + duration
    
    def show_game_over(self):
        """Show the game over screen."""
        # Create a reusable overlay surface
        if not hasattr(self, 'overlay_surface'):
            self.overlay_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.overlay_surface.fill((0, 0, 0, 180))  # Semi-transparent black
        
        self.screen.blit(self.overlay_surface, (0, 0))
        
        # Game over text
        game_over_text = FONT_LARGE.render("CONGRATULATIONS!", True, YELLOW)
        self.screen.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2, 160))
        
        # Calculate time taken
        time_taken = self.game.scoreboard.current_game_stats["end_time"] - self.game.scoreboard.current_game_stats["start_time"]
        
        # Calculate errors (mismatches)
        total_matches = self.game.player.matches
        total_attempts = self.game.player.moves
        errors = max(0, total_attempts - total_matches)
        
        # Show only time and errors as requested
        errors_text = self.render_text(FONT_MEDIUM, f"Errors: {errors}", WHITE)
        time_text = self.render_text(FONT_MEDIUM, f"Time: {time_taken:.1f} seconds", WHITE)
        
        # Center the stats
        self.screen.blit(errors_text, (self.width // 2 - errors_text.get_width() // 2, 240))
        self.screen.blit(time_text, (self.width // 2 - time_text.get_width() // 2, 280))
        
        # Play again button
        play_again_rect = pygame.Rect(self.width // 2 - 100, 350, 200, 50)
        pygame.draw.rect(self.screen, BLUE, play_again_rect, 0, 10)
        pygame.draw.rect(self.screen, WHITE, play_again_rect, 2, 10)
        
        play_again_text = FONT_MEDIUM.render("Play Again", True, WHITE)
        self.screen.blit(play_again_text, (play_again_rect.centerx - play_again_text.get_width() // 2, 
                                         play_again_rect.centery - play_again_text.get_height() // 2))
        
        # Main menu button
        menu_rect = pygame.Rect(self.width // 2 - 100, 420, 200, 50)
        pygame.draw.rect(self.screen, GREEN, menu_rect, 0, 10)
        pygame.draw.rect(self.screen, WHITE, menu_rect, 2, 10)
        
        menu_text = FONT_MEDIUM.render("Main Menu", True, WHITE)
        self.screen.blit(menu_text, (menu_rect.centerx - menu_text.get_width() // 2, 
                                    menu_rect.centery - menu_text.get_height() // 2))
        
        pygame.display.flip()
        
        # Wait for player input
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if play_again_rect.collidepoint(event.pos):
                        # Return True to indicate to play again with same settings
                        waiting = False
                        return True
                    elif menu_rect.collidepoint(event.pos):
                        # Return False to go back to main menu
                        waiting = False
                        return False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        waiting = False
                        return False
            
            self.clock.tick(FPS)
        
        return False
    
    def flip_card_animation(self, row, col):
        """Start a flip animation for a card."""
        card = self.game.board.get_card(row, col)
        if card:
            is_flipping_up = not card.is_face_up
            self.flipping_cards.append((card, pygame.time.get_ticks(), is_flipping_up))
            
            # Actually flip the card in the game after a small delay
            pygame.time.set_timer(pygame.USEREVENT, 150, 1)  # One-time event
    
    def check_game_over(self):
        """Check if the game is over and trigger the game over event if needed."""
        if self.game and self.game.board.is_game_over():
            # End the game and schedule the game over screen
            self.game.game_active = False
            self.game.scoreboard.end_game()
            pygame.time.set_timer(pygame.USEREVENT + 1, 1500, 1)
            
            # Clear any existing message when game ends
            self.message = ""
            self.message_timer = 0
            
            return True
        return False
    
    def run(self):
        """Run the game loop."""
        self.setup_window()
        running = True
        
        # Pre-create often used surfaces to avoid recreation
        self.overlay_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.overlay_surface.fill((0, 0, 0, 180))
        
        # Memory monitoring
        memory_usage = []
        self.last_gc_time = pygame.time.get_ticks()
        
        while running:
            # Show start screen and get difficulty settings
            rows, cols = self.show_start_screen()
            
            # Create a new game with selected difficulty
            self.game = Game(rows=rows, cols=cols)
            self.game.start_game()
            
            # For 10x10 grid, adjust the UI to make room
            if rows == 10:
                self.board_margin_top = 80  # Minimize top margin
                # Make sure cards are small enough
                self.card_width = min(self.card_width, 50)
                self.card_height = self.card_width * 1.25
                # Reduce card margins for tighter packing
                global CARD_MARGIN
                CARD_MARGIN = 5
            
            # Game session variables
            game_active = True
            waiting_for_flip_back = False
            flip_back_time = 0
            
            # Main game loop for current game session
            while game_active:
                current_time = pygame.time.get_ticks()
                
                # Memory management - clean up text cache if it gets too large
                if len(self.text_cache) > 100:
                    # Keep only the most recent 20 items
                    cache_keys = list(self.text_cache.keys())
                    for key in cache_keys[:-20]:
                        del self.text_cache[key]
                
                # Process events - limit the number of events processed per frame
                for event in pygame.event.get()[:10]:  # Limit to 10 events per frame
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if not waiting_for_flip_back and self.game.game_active:
                            pos = pygame.mouse.get_pos()
                            card_pos = self.get_card_at_pos(pos)
                            
                            if card_pos:
                                row, col = card_pos
                                card = self.game.board.get_card(row, col)
                                
                                if card and not card.is_matched and not card.is_face_up:
                                    # Start flip animation
                                    self.flip_card_animation(row, col)
                    
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            # Go back to main menu
                            game_active = False
                    
                    elif event.type == pygame.USEREVENT:
                        # This is our delayed flip event
                        pos = pygame.mouse.get_pos()
                        card_pos = self.get_card_at_pos(pos)
                        
                        if card_pos:
                            row, col = card_pos
                            result = self.game.flip_card(row, col)
                            if "Match found" in result:
                                self.show_message(f"Match found! +10 points", 1500)
                                
                                # Start match animation
                                self.match_animation_active = True
                                self.match_animation_start = pygame.time.get_ticks()
                                self.match_animation_cards = self.game.board.flipped_cards.copy()
                                
                                if "Game Over" in result:
                                    # Game is over, show end screen after a delay
                                    pygame.time.set_timer(pygame.USEREVENT + 1, 1500, 1)
                                    
                                    # Clear any message when game ends
                                    self.message = ""
                                    self.message_timer = 0
                            
                            # Check if we need to flip cards back after a delay
                            if len(self.game.board.flipped_cards) == 2 and not "Match found" in result:
                                waiting_for_flip_back = True
                                flip_back_time = pygame.time.get_ticks() + 1500  # 1.5 seconds
                                
                                # Start shake animation instead of showing a message
                                self.shake_animation_active = True
                                self.shake_animation_start = pygame.time.get_ticks()
                                self.shake_animation_cards = self.game.board.flipped_cards.copy()
                    
                    elif event.type == pygame.USEREVENT + 1:
                        # Game over event - show congratulation screen
                        result = self.show_game_over()
                        
                        if result:
                            # Play again with same difficulty
                            game_active = False  # End this game session
                            
                            # Create a new game with the same settings
                            self.game = Game(rows=rows, cols=cols)
                            self.game.start_game()
                            
                            # Reset game session variables
                            game_active = True
                            waiting_for_flip_back = False
                            flip_back_time = 0
                        else:
                            # Return to main menu
                            game_active = False
                    
                    elif event.type == pygame.USEREVENT + 2:
                        # Reset unmatched cards event
                        self.game.board.reset_unmatched()
                
                # Check if it's time to flip cards back
                if waiting_for_flip_back and current_time >= flip_back_time:
                    waiting_for_flip_back = False
                    
                    # Start flip animations for the cards
                    for card in self.game.board.flipped_cards:
                        row, col = self.game.board.get_card_position(card.card_id)
                        self.flipping_cards.append((card, pygame.time.get_ticks(), False))
                    
                    # Actually reset the cards in the game model after animation finishes
                    pygame.time.set_timer(pygame.USEREVENT + 2, 300, 1)  # One-time event
                
                # Extra check for game over, in case the event system missed it
                if self.game.game_active and self.game.board.is_game_over():
                    self.check_game_over()
                
                # Update screen
                self.screen.fill(WHITE)
                self.update_animations()
                self.draw_ui()
                self.draw_board()
                pygame.display.flip()
                
                # Cap the frame rate
                self.clock.tick(FPS)
                
                # Explicitly call garbage collection periodically (every 30 seconds)
                if current_time - self.last_gc_time > 30000:  # 30 seconds
                    gc.collect()
                    self.last_gc_time = current_time
                    
                    # Try to get process memory info for monitoring (optional)
                    try:
                        import os, psutil
                        process = psutil.Process(os.getpid())
                        mem_info = process.memory_info()
                        memory_usage.append(mem_info.rss / 1024 / 1024)  # MB
                        
                        # Log memory usage (for debugging)
                        if len(memory_usage) > 10:
                            memory_usage.pop(0)
                        
                        # If memory usage is growing too rapidly, clear caches
                        if len(memory_usage) > 3 and memory_usage[-1] > memory_usage[0] * 1.5:
                            self.text_cache.clear()
                            
                    except (ImportError, AttributeError):
                        # psutil not available, skip monitoring
                        pass
        
        # Clean up explicitly when exiting
        self.text_cache.clear()
        self.overlay_surface = None
        self.match_animation_cards = None
        self.flipping_cards = None
        gc.collect()  # Final garbage collection
        pygame.quit()


def main():
    """Start the memory card game."""
    game_gui = GameGUI()
    game_gui.run()


if __name__ == "__main__":
    main()
