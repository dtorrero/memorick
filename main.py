import pygame
import sys
import time
import gc  # Import garbage collector module at the top level
import math
from classes import Card, Board, Player, Game
from database import get_database

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
        self.player_name = ""
    
    def setup_window(self):
        """Set up the game window."""
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Memory Card Game")
    
    def get_player_name(self):
        """Get the player name before starting the game."""
        self.screen.fill(WHITE)
        input_text = ""
        input_active = True
        input_rect = pygame.Rect(self.width // 2 - 140, 250, 280, 50)
        cursor_visible = True
        cursor_timer = 0
        cursor_blink_time = 500  # milliseconds
        
        # Draw welcome title
        title = FONT_LARGE.render("Welcome to Memory Game", True, BLUE)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 100))

        # Draw subtitle
        subtitle = FONT_MEDIUM.render("Enter Your Name", True, BLACK)
        self.screen.blit(subtitle, (self.width // 2 - subtitle.get_width() // 2, 180))
        
        # Create an OK button
        ok_button_rect = pygame.Rect(self.width // 2 - 50, 320, 100, 40)

        while True:
            current_time = pygame.time.get_ticks()
            
            # Handle cursor blinking
            if current_time - cursor_timer > cursor_blink_time:
                cursor_visible = not cursor_visible
                cursor_timer = current_time
                
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # Handle mouse clicks for the OK button
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if ok_button_rect.collidepoint(event.pos) and input_text.strip():
                        return input_text.strip()
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and input_text.strip():
                        return input_text.strip()
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        # Allow the user to exit
                        pygame.quit()
                        sys.exit()
                    else:
                        # Allow letters, numbers and spaces, with a max length of 15
                        if len(input_text) < 15 and (event.unicode.isalnum() or event.unicode == " "):
                            # Don't allow spaces at the beginning or consecutive spaces
                            if event.unicode != " " or (input_text and input_text[-1] != " "):
                                input_text += event.unicode
            
            # Redraw the screen
            self.screen.fill(WHITE)
            
            # Draw titles
            self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 100))
            self.screen.blit(subtitle, (self.width // 2 - subtitle.get_width() // 2, 180))
            
            # Draw input box - change color based on activity
            box_color = BLUE if input_active else GRAY
            pygame.draw.rect(self.screen, box_color, input_rect, 2, 10)
            
            # Draw input text
            text_surface = FONT_MEDIUM.render(input_text, True, BLACK)
            
            # Center the text in the input box
            text_x = input_rect.centerx - text_surface.get_width() // 2
            text_y = input_rect.centery - text_surface.get_height() // 2
            
            # Clear background before drawing text
            self.screen.fill(WHITE, input_rect.inflate(-4, -4))
            self.screen.blit(text_surface, (text_x, text_y))
            
            # Draw cursor
            if cursor_visible and input_active:
                cursor_x = text_x + text_surface.get_width()
                cursor_y = text_y
                pygame.draw.line(self.screen, BLACK, 
                                (cursor_x, cursor_y), 
                                (cursor_x, cursor_y + text_surface.get_height()), 2)
            
            # Draw OK button
            button_color = GREEN if input_text.strip() else GRAY
            pygame.draw.rect(self.screen, button_color, ok_button_rect, 0, 10)
            pygame.draw.rect(self.screen, WHITE, ok_button_rect, 2, 10)
            
            # Draw button text
            ok_text = FONT_MEDIUM.render("OK", True, WHITE)
            self.screen.blit(ok_text, (ok_button_rect.centerx - ok_text.get_width() // 2, 
                              ok_button_rect.centery - ok_text.get_height() // 2))

            # Draw instruction
            if not input_text.strip():
                instruction = FONT_SMALL.render("Please enter your name to continue", True, RED)
            else:
                instruction = FONT_SMALL.render("Press ENTER or click OK to continue", True, GRAY)
            self.screen.blit(instruction, (self.width // 2 - instruction.get_width() // 2, 380))

            pygame.display.flip()
            self.clock.tick(FPS)
    
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
        
        # Add stats button
        stats_rect = pygame.Rect(self.width // 2 - button_width // 2, button_y_start + (button_height + button_margin) * 3, button_width, button_height)
        
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
            
            # Stats Button
            button_color = GREEN if stats_rect.collidepoint(mouse_pos) else (100, 200, 100)
            pygame.draw.rect(self.screen, button_color, stats_rect, 0, 10)
            pygame.draw.rect(self.screen, WHITE, stats_rect, 2, 10)
            text = FONT_MEDIUM.render("Statistics", True, WHITE)
            self.screen.blit(text, (stats_rect.centerx - text.get_width() // 2, stats_rect.centery - text.get_height() // 2))
            
            if mouse_clicked and stats_rect.collidepoint(mouse_pos):
                self.show_stats_screen()
                # Redraw the start screen after coming back from stats
                self.screen.fill(WHITE)
                self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 80))
                for i, line in enumerate(instructions):
                    text = FONT_SMALL.render(line, True, BLACK)
                    self.screen.blit(text, (self.width // 2 - text.get_width() // 2, 150 + i * 30))
            
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
    
    def format_time(self, seconds):
        """Format time in minutes:seconds."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def draw_ui(self):
        """Draw the user interface elements."""
        # Game message
        if self.message and pygame.time.get_ticks() < self.message_timer:
            message_text = self.render_text(FONT_MEDIUM, self.message, BLUE)
            self.screen.blit(message_text, (self.width // 2 - message_text.get_width() // 2, 20))
        
        # Only draw game stats if a game is active
        if self.game and self.game.game_active:
            # Calculate errors (mismatches)
            total_matches = self.game.player.matches
            total_attempts = self.game.player.moves
            errors = max(0, total_attempts - total_matches)
            
            # Calculate elapsed time
            current_time = self.game.scoreboard.current_game_stats["start_time"]
            elapsed_time = time.time() - current_time
            
            # Draw stats background - create semi-transparent background
            stats_rect = pygame.Rect(10, 10, 200, 70)
            stats_bg = pygame.Surface((stats_rect.width, stats_rect.height), pygame.SRCALPHA)
            stats_bg.fill((0, 0, 0, 128))  # Semi-transparent black
            self.screen.blit(stats_bg, stats_rect)
            pygame.draw.rect(self.screen, BLUE, stats_rect, 2, 5)
            
            # Draw stats text
            player_text = self.render_text(FONT_SMALL, f"Player: {self.player_name}", WHITE)
            errors_text = self.render_text(FONT_SMALL, f"Errors: {errors}", WHITE)
            time_text = self.render_text(FONT_SMALL, f"Time: {self.format_time(elapsed_time)}", WHITE)
            
            self.screen.blit(player_text, (stats_rect.x + 10, stats_rect.y + 10))
            self.screen.blit(errors_text, (stats_rect.x + 10, stats_rect.y + 30))
            self.screen.blit(time_text, (stats_rect.x + 10, stats_rect.y + 50))
    
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
        
        # Game over text - handle empty player name gracefully
        if self.player_name:
            game_over_text = FONT_LARGE.render(f"¡FELICIDADES {self.player_name}!", True, YELLOW)
        else:
            game_over_text = FONT_LARGE.render("¡FELICIDADES!", True, YELLOW)
        self.screen.blit(game_over_text, (self.width // 2 - game_over_text.get_width() // 2, 160))
        
        # Calculate time taken
        time_taken = self.game.scoreboard.current_game_stats["end_time"] - self.game.scoreboard.current_game_stats["start_time"]
        
        # Calculate errors (mismatches)
        total_matches = self.game.player.matches
        total_attempts = self.game.player.moves
        errors = max(0, total_attempts - total_matches)
        
        # Save game stats to database
        db = get_database()
        difficulty_map = {4: "Easy", 6: "Medium", 10: "Hard"}
        difficulty = difficulty_map.get(self.game.board.rows, "Custom")
        
        db.save_game_stats(
            player_name=self.player_name if self.player_name else "Anonymous",
            difficulty=difficulty,
            start_time=self.game.scoreboard.current_game_stats["start_time"],
            end_time=self.game.scoreboard.current_game_stats["end_time"],
            moves=total_attempts,
            matches=total_matches,
            completed=True
        )
        
        # Show only time and errors as requested
        errors_text = self.render_text(FONT_MEDIUM, f"Errors: {errors}", WHITE)
        time_text = self.render_text(FONT_MEDIUM, f"Time: {self.format_time(time_taken)}", WHITE)
        
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
            
            # Actually flip the card in the game model right away to prevent the bug
            # where rapid clicking causes the first card to be lost
            if is_flipping_up:
                card.is_face_up = True
            
            # Set a timer event to handle the post-animation logic
            pygame.time.set_timer(pygame.USEREVENT, 150, 1)  # One-time event
    
    def check_game_over(self):
        """Check if the game is over and trigger the game over event if needed."""
        if not self.game:
            return False
            
        # Simple direct check for game completion
        if self.game.game_active and self.game.player.matches >= len(self.game.board.cards) // 2:
            print("Game over detected in check_game_over!")
            self.game.game_active = False
            self.game.scoreboard.end_game()
            
            # Show game over screen directly instead of using a timer
            print("Showing game over screen from check_game_over!")
            result = self.show_game_over()
            
            # Return True to indicate that we've handled the game over condition
            return True
            
        return False
    
    def show_stats_screen(self):
        """Show the statistics screen with leaderboard and player stats."""
        db = get_database()
        self.screen.fill(WHITE)
        
        # Title
        title = FONT_LARGE.render("Game Statistics", True, BLUE)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 30))
        
        # Get leaderboard data
        easy_leaders = db.get_leaderboard(difficulty="Easy", limit=5)
        medium_leaders = db.get_leaderboard(difficulty="Medium", limit=5)
        hard_leaders = db.get_leaderboard(difficulty="Hard", limit=5)
        
        # Draw tab buttons
        tab_width, tab_height = 120, 40
        tabs_y = 100
        
        easy_tab_rect = pygame.Rect(self.width // 4 - tab_width // 2, tabs_y, tab_width, tab_height)
        medium_tab_rect = pygame.Rect(self.width // 2 - tab_width // 2, tabs_y, tab_width, tab_height)
        hard_tab_rect = pygame.Rect(3 * self.width // 4 - tab_width // 2, tabs_y, tab_width, tab_height)
        
        # Tabs data
        tabs = [
            {"name": "Easy", "rect": easy_tab_rect, "data": easy_leaders},
            {"name": "Medium", "rect": medium_tab_rect, "data": medium_leaders},
            {"name": "Hard", "rect": hard_tab_rect, "data": hard_leaders}
        ]
        
        selected_tab = 0  # Default to Easy tab
        
        # Back button
        back_rect = pygame.Rect(self.width // 2 - 100, 520, 200, 50)
        
        # Main loop for stats screen
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = False
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        mouse_clicked = True
            
            # Clear screen
            self.screen.fill(WHITE)
            
            # Draw title
            self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 30))
            
            # Draw tabs
            for i, tab in enumerate(tabs):
                # Determine tab color based on selection and hover
                if i == selected_tab:
                    tab_color = BLUE
                    text_color = WHITE
                elif tab["rect"].collidepoint(mouse_pos):
                    tab_color = (150, 150, 255)
                    text_color = BLACK
                else:
                    tab_color = (220, 220, 255)
                    text_color = BLACK
                
                # Draw tab and handle click
                pygame.draw.rect(self.screen, tab_color, tab["rect"], 0, 10)
                pygame.draw.rect(self.screen, BLUE, tab["rect"], 2, 10)
                
                tab_text = FONT_MEDIUM.render(tab["name"], True, text_color)
                self.screen.blit(tab_text, (tab["rect"].centerx - tab_text.get_width() // 2, 
                                          tab["rect"].centery - tab_text.get_height() // 2))
                
                if mouse_clicked and tab["rect"].collidepoint(mouse_pos):
                    selected_tab = i
            
            # Draw selected tab content (leaderboard)
            current_tab = tabs[selected_tab]
            leaderboard_data = current_tab["data"]
            
            # Leaderboard title
            lb_title = FONT_MEDIUM.render(f"Top Players - {current_tab['name']}", True, BLACK)
            self.screen.blit(lb_title, (self.width // 2 - lb_title.get_width() // 2, 160))
            
            # Draw leaderboard headers
            header_y = 200
            headers = ["Rank", "Player", "Time", "Moves", "Errors"]
            header_widths = [60, 200, 100, 100, 100]
            header_x = self.width // 2 - sum(header_widths) // 2
            
            for i, header in enumerate(headers):
                header_text = FONT_SMALL.render(header, True, BLUE)
                self.screen.blit(header_text, (header_x, header_y))
                header_x += header_widths[i]
            
            # Draw leaderboard data
            if leaderboard_data:
                for i, entry in enumerate(leaderboard_data):
                    row_y = 230 + i * 30
                    row_x = self.width // 2 - sum(header_widths) // 2
                    
                    # Convert duration to MM:SS format
                    duration_formatted = self.format_time(entry["duration_seconds"])
                    
                    # Row data
                    row_data = [
                        f"{i+1}",
                        entry["player_name"],
                        duration_formatted,
                        str(entry["moves"]),
                        str(entry["errors"])
                    ]
                    
                    for j, data in enumerate(row_data):
                        data_text = FONT_SMALL.render(data, True, BLACK)
                        self.screen.blit(data_text, (row_x, row_y))
                        row_x += header_widths[j]
            else:
                no_data_text = FONT_MEDIUM.render("No games played yet!", True, GRAY)
                self.screen.blit(no_data_text, (self.width // 2 - no_data_text.get_width() // 2, 280))
            
            # Draw personal stats for current player if available
            if self.player_name:
                player_stats = db.get_player_stats(self.player_name)
                if player_stats:
                    # Calculate aggregate stats
                    total_games = len(player_stats)
                    completed_games = sum(1 for stat in player_stats if stat["completed"])
                    total_time = sum(stat["duration_seconds"] for stat in player_stats)
                    avg_time = total_time / total_games if total_games > 0 else 0
                    best_time = min((stat["duration_seconds"] for stat in player_stats if stat["completed"]), default=0)
                    
                    # Player stats section
                    stats_y = 380
                    stats_title = FONT_MEDIUM.render(f"Your Stats: {self.player_name}", True, GREEN)
                    self.screen.blit(stats_title, (self.width // 2 - stats_title.get_width() // 2, stats_y))
                    
                    stats_text = [
                        f"Games Played: {total_games}",
                        f"Games Completed: {completed_games}",
                        f"Best Time: {self.format_time(best_time)}",
                        f"Average Time: {self.format_time(avg_time)}"
                    ]
                    
                    for i, text in enumerate(stats_text):
                        stat_text = FONT_SMALL.render(text, True, BLACK)
                        self.screen.blit(stat_text, (self.width // 2 - stat_text.get_width() // 2, stats_y + 40 + i * 25))
            
            # Draw back button
            button_color = GREEN if back_rect.collidepoint(mouse_pos) else (100, 200, 100)
            pygame.draw.rect(self.screen, button_color, back_rect, 0, 10)
            pygame.draw.rect(self.screen, BLACK, back_rect, 2, 10)
            
            back_text = FONT_MEDIUM.render("Back to Menu", True, WHITE)
            self.screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2, 
                                       back_rect.centery - back_text.get_height() // 2))
            
            if mouse_clicked and back_rect.collidepoint(mouse_pos):
                running = False
            
            pygame.display.flip()
            self.clock.tick(FPS)
    
    def run(self):
        """Run the game loop."""
        self.setup_window()
        running = True
        
        # Get player name before starting
        self.player_name = self.get_player_name()
        
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
            game_completed = False  # Flag to track if we've already handled game completion
            
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
                                    
                                    # Check if this is the second card being flipped
                                    face_up_cards = [c for c in self.game.board.cards 
                                                   if c.is_face_up and not c.is_matched]
                                    
                                    # If we now have 2 cards face up, process the match check after animation
                                    if len(face_up_cards) == 2:
                                        # Set a timer to check for matches
                                        pygame.time.set_timer(pygame.USEREVENT, 150, 1)
                    
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            # Save abandoned game stats
                            if self.game and self.game.game_active:
                                db = get_database()
                                difficulty_map = {4: "Easy", 6: "Medium", 10: "Hard"}
                                difficulty = difficulty_map.get(self.game.board.rows, "Custom")
                                
                                # Record end time as current time
                                self.game.scoreboard.current_game_stats["end_time"] = time.time()
                                
                                db.save_game_stats(
                                    player_name=self.player_name if self.player_name else "Anonymous",
                                    difficulty=difficulty,
                                    start_time=self.game.scoreboard.current_game_stats["start_time"],
                                    end_time=self.game.scoreboard.current_game_stats["end_time"],
                                    moves=self.game.player.moves,
                                    matches=self.game.player.matches,
                                    completed=False  # Mark as abandoned
                                )
                            
                            # Go back to main menu
                            game_active = False
                    
                    elif event.type == pygame.USEREVENT:
                        # Check for matches
                        face_up_cards = [c for c in self.game.board.cards 
                                       if c.is_face_up and not c.is_matched]
                        
                        if len(face_up_cards) == 2:
                            # We have two cards face up, process the match
                            card1, card2 = face_up_cards
                            row1, col1 = self.game.board.get_card_position(card1.card_id)
                            row2, col2 = self.game.board.get_card_position(card2.card_id)
                            
                            # Record the move in the game
                            result = self.game.check_match(row1, col1, row2, col2)
                            
                            if "Match found" in result:
                                self.show_message(f"Match found! +10 points", 1500)
                                
                                # Start match animation
                                self.match_animation_active = True
                                self.match_animation_start = pygame.time.get_ticks()
                                self.match_animation_cards = face_up_cards.copy()
                                
                                # Check if the game is over - SIMPLIFIED APPROACH
                                if self.game.player.matches >= len(self.game.board.cards) // 2:
                                    print("Match detection found game completed!")
                                    # End the game immediately
                                    self.game.game_active = False
                                    self.game.scoreboard.end_game()
                                    game_completed = True
                                    
                                    # Force show the game over screen directly here
                                    # Instead of using a timer, show it immediately
                                    print("Directly showing game over screen!")
                                    result = self.show_game_over()
                                    
                                    if result:
                                        # Play again with same difficulty
                                        # End this game session and start a new one
                                        self.game = Game(rows=rows, cols=cols)
                                        self.game.start_game()
                                        
                                        # Reset game session variables
                                        waiting_for_flip_back = False
                                        flip_back_time = 0
                                        game_completed = False
                                    else:
                                        # Return to main menu
                                        game_active = False
                            else:
                                # Not a match, schedule to flip them back
                                waiting_for_flip_back = True
                                flip_back_time = pygame.time.get_ticks() + 1500  # 1.5 seconds
                                
                                # Start shake animation
                                self.shake_animation_active = True
                                self.shake_animation_start = pygame.time.get_ticks()
                                self.shake_animation_cards = face_up_cards.copy()
                    
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
                if self.game and self.game.game_active and not game_completed:
                    # Check for game completion after each frame - SIMPLIFIED APPROACH
                    if self.game.player.matches >= len(self.game.board.cards) // 2:
                        print(f"Extra check found game completed! Matches: {self.game.player.matches}, Total pairs: {len(self.game.board.cards) // 2}")
                        game_completed = True  # Mark as completed to prevent duplicate handling
                        
                        # Directly show the game over screen without any delay
                        self.game.game_active = False
                        self.game.scoreboard.end_game()
                        
                        print("Showing game over screen from extra check!")
                        result = self.show_game_over()
                        
                        if result:
                            # Play again with same difficulty
                            # End this game session and start a new one
                            self.game = Game(rows=rows, cols=cols)
                            self.game.start_game()
                            
                            # Reset game session variables
                            waiting_for_flip_back = False
                            flip_back_time = 0
                            game_completed = False
                        else:
                            # Return to main menu
                            game_active = False
                        
                        # Skip the rest of the loop to avoid any drawing or further processing
                        continue
                
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
