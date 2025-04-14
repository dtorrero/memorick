"""
Enhanced script for the Memory Card Game with remote statistics features.
Run this instead of main.py to enable remote stats and view global leaderboards.
"""
import sys
import os

# Import the database_sync module to get the synchronized database
from database_sync import get_sync_database

# Import the original game code
from main import GameGUI, main as original_main, pygame, FONT_MEDIUM, FONT_SMALL, WHITE, BLUE, GREEN, BLACK, GRAY

# Replace the database import in the main module with our sync version
import main
import builtins

# Store the original import function
original_import = builtins.__import__

# Define a custom import function that replaces database imports
def custom_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == 'database' and fromlist and 'get_database' in fromlist:
        # When main.py tries to import get_database from database,
        # give it our sync version instead
        module = original_import(name, globals, locals, fromlist, level)
        module.get_database = get_sync_database
        return module
    return original_import(name, globals, locals, fromlist, level)

# Replace the import function with our custom version
builtins.__import__ = custom_import

# Extend the GameGUI class to add global stats viewing capability
class RemoteStatsGameGUI(GameGUI):
    """Extended GameGUI with remote statistics capabilities."""
    
    def show_stats_screen(self):
        """
        Override the original stats screen to show both local and global leaderboards.
        """
        # Show loading indicator while fetching data
        self.screen.fill(WHITE)
        loading_text = FONT_MEDIUM.render("Loading statistics...", True, BLUE)
        self.screen.blit(loading_text, (self.width // 2 - loading_text.get_width() // 2, self.height // 2 - loading_text.get_height() // 2))
        pygame.display.flip()
        
        # Get the syncing database and force a refresh of data when the screen is opened
        db = get_sync_database()
        
        # Always attempt to refresh data when opening the screen
        if db.online or db.check_server_connection():
            try:
                print("Force refreshing server data on stats screen open")
                # This will update the local cache with the latest server data
                db._refresh_server_data()
            except Exception as e:
                print(f"Error refreshing data when opening stats screen: {e}")
        else:
            print("Server offline - using cached data")
        
        self.screen.fill(WHITE)
        
        # Title
        title = FONT_MEDIUM.render("Game Statistics (with Remote Data)", True, BLUE)
        self.screen.blit(title, (self.width // 2 - title.get_width() // 2, 30))
        
        # Get local and remote leaderboard data
        local_easy = db.get_leaderboard(difficulty="Easy", limit=5)
        local_medium = db.get_leaderboard(difficulty="Medium", limit=5)
        local_hard = db.get_leaderboard(difficulty="Hard", limit=5)
        
        # Try to get remote leaderboard data (will fall back to local if offline)
        remote_easy = db.get_remote_leaderboard(difficulty="Easy", limit=5) 
        remote_medium = db.get_remote_leaderboard(difficulty="Medium", limit=5)
        remote_hard = db.get_remote_leaderboard(difficulty="Hard", limit=5)
        
        # Setup tab structure - now we have local and global tabs
        tab_width, tab_height = 120, 40
        tabs_y = 100
        
        # Local tabs
        easy_tab_rect = pygame.Rect(self.width // 6 - tab_width // 2, tabs_y, tab_width, tab_height)
        medium_tab_rect = pygame.Rect(3 * self.width // 6 - tab_width // 2, tabs_y, tab_width, tab_height)
        hard_tab_rect = pygame.Rect(5 * self.width // 6 - tab_width // 2, tabs_y, tab_width, tab_height)
        
        # Switch between local and global leaderboards
        local_global_switch_rect = pygame.Rect(self.width // 2 - 150, 70, 300, 30)
        
        # Define all tabs data
        tabs = [
            {"name": "Easy", "rect": easy_tab_rect, "local_data": local_easy, "remote_data": remote_easy},
            {"name": "Medium", "rect": medium_tab_rect, "local_data": local_medium, "remote_data": remote_medium},
            {"name": "Hard", "rect": hard_tab_rect, "local_data": local_hard, "remote_data": remote_hard}
        ]
        
        selected_tab = 0  # Default to Easy tab
        show_remote = True  # Default to showing remote data
        
        # Back button
        back_rect = pygame.Rect(self.width // 2 - 120, 520, 240, 50)
        
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
            
            # Draw local/global switch
            switch_text = FONT_SMALL.render(f"{'GLOBAL' if show_remote else 'LOCAL'} LEADERBOARD", True, WHITE)
            switch_color = GREEN if show_remote else BLUE
            pygame.draw.rect(self.screen, switch_color, local_global_switch_rect, 0, 10)
            self.screen.blit(switch_text, (local_global_switch_rect.centerx - switch_text.get_width() // 2, 
                                        local_global_switch_rect.centery - switch_text.get_height() // 2))
            
            if mouse_clicked and local_global_switch_rect.collidepoint(mouse_pos):
                show_remote = not show_remote
            
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
            leaderboard_data = current_tab["remote_data"] if show_remote else current_tab["local_data"]
            
            # Leaderboard title
            source = "Global" if show_remote else "Local"
            lb_title = FONT_MEDIUM.render(f"{source} Top Players - {current_tab['name']}", True, BLACK)
            self.screen.blit(lb_title, (self.width // 2 - lb_title.get_width() // 2, 160))
            
            # Draw leaderboard headers
            header_y = 200
            headers = ["Rank", "Player", "Time", "Errors"]
            header_widths = [60, 240, 110, 110]
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
                    
                    # Row data for leaderboard
                    row_data = [
                        f"{i+1}",
                        entry["player_name"],
                        duration_formatted,
                        str(entry["errors"])
                    ]
                    
                    # Determine row color based on whether this is cached data
                    row_color = BLACK
                    if entry.get("cached", False):
                        row_color = (180, 0, 0)  # Red for cached entries
                    
                    for j, data in enumerate(row_data):
                        data_text = FONT_SMALL.render(data, True, row_color)
                        self.screen.blit(data_text, (row_x, row_y))
                        row_x += header_widths[j]
                
                # Show warning if using cached data
                if any(entry.get("cached", False) for entry in leaderboard_data):
                    warning_text = FONT_SMALL.render("⚠ Showing cached data - Data loaded when you last opened this screen", True, (180, 0, 0))
                    self.screen.blit(warning_text, (self.width // 2 - warning_text.get_width() // 2, 410))
            else:
                no_data_text = FONT_MEDIUM.render("No games played yet!", True, GRAY)
                self.screen.blit(no_data_text, (self.width // 2 - no_data_text.get_width() // 2, 280))
            
            # Draw player stats
            if self.player_name:
                # Get player stats - local or remote based on switch
                if show_remote:
                    player_data = db.get_player_remote_stats(self.player_name)
                    player_stats = player_data.get("stats", [])
                    local_only_stats = player_data.get("local_stats", [])
                    using_cached = player_data.get("using_cached", False)
                    has_local_data = player_data.get("has_local_data", False)
                    error_message = player_data.get("error", None)
                else:
                    player_stats = db.get_player_stats(self.player_name)
                    local_only_stats = []
                    using_cached = False
                    has_local_data = True
                    error_message = None
                
                # Filter stats for the selected difficulty
                current_difficulty = tabs[selected_tab]["name"]
                difficulty_stats = [stat for stat in player_stats if stat["difficulty"] == current_difficulty]
                
                # Create status text with connection information
                source_text = source
                if using_cached:
                    source_text += " (Offline Mode)"
                    status_color = (255, 140, 0)  # Orange for offline mode
                elif show_remote and has_local_data and local_only_stats:
                    source_text += " + Local"
                    status_color = GREEN  # Green for online with local data
                elif show_remote:
                    status_color = GREEN  # Green for online
                else:
                    status_color = BLUE  # Blue for local-only view
                
                # Display connection error if present
                if error_message and show_remote:
                    error_y = 350
                    error_text = FONT_SMALL.render(f"Connection Status: {error_message}", True, (180, 0, 0))
                    self.screen.blit(error_text, (self.width // 2 - error_text.get_width() // 2, error_y))
                
                if difficulty_stats:
                    # Calculate filtered stats for the selected difficulty
                    total_games = len(difficulty_stats)
                    completed_games = sum(1 for stat in difficulty_stats if stat["completed"])
                    
                    # Only use completed games for time calculations
                    completed_stats = [stat for stat in difficulty_stats if stat["completed"]]
                    total_time = sum(stat["duration_seconds"] for stat in completed_stats)
                    avg_time = total_time / len(completed_stats) if completed_stats else 0
                    best_time = min((stat["duration_seconds"] for stat in completed_stats), default=0)
                    
                    # Player stats section
                    stats_y = 380
                    stats_title = FONT_MEDIUM.render(f"Your {source_text} {current_difficulty} Stats: {self.player_name}", True, status_color)
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
                    
                    # Show local-only stats count if available
                    if show_remote and local_only_stats:
                        local_difficulty_stats = [stat for stat in local_only_stats if stat["difficulty"] == current_difficulty]
                        if local_difficulty_stats:
                            local_text = FONT_SMALL.render(f"Additional local-only games: {len(local_difficulty_stats)}", True, BLUE)
                            self.screen.blit(local_text, (self.width // 2 - local_text.get_width() // 2, stats_y + 70))
                else:
                    # No stats for this difficulty
                    stats_y = 380
                    stats_title = FONT_MEDIUM.render(f"Your {source_text} {current_difficulty} Stats: {self.player_name}", True, status_color)
                    self.screen.blit(stats_title, (self.width // 2 - stats_title.get_width() // 2, stats_y))
                    
                    no_stats = FONT_SMALL.render(f"No games played on {current_difficulty} difficulty", True, GRAY)
                    self.screen.blit(no_stats, (self.width // 2 - no_stats.get_width() // 2, stats_y + 40))
                    
                    # Show local-only stats count if available
                    if show_remote and local_only_stats:
                        local_difficulty_stats = [stat for stat in local_only_stats if stat["difficulty"] == current_difficulty]
                        if local_difficulty_stats:
                            local_text = FONT_SMALL.render(f"Additional local-only games: {len(local_difficulty_stats)}", True, BLUE)
                            self.screen.blit(local_text, (self.width // 2 - local_text.get_width() // 2, stats_y + 70))
            
            # Draw connection status
            try:
                RED = (255, 0, 0)
            except:
                RED = (180, 0, 0)  # Fallback if RED is not defined
                
            status_color = GREEN if db.online else RED
            status_text = FONT_SMALL.render(f"Server: {'Online' if db.online else 'Offline'}", True, status_color)
            self.screen.blit(status_text, (10, 10))
            
            # Draw last update time
            update_time = FONT_SMALL.render("Data updated: Just now", True, GRAY if db.online else RED)
            self.screen.blit(update_time, (self.width - update_time.get_width() - 10, 10))
            
            # Draw back button
            button_color = GREEN if back_rect.collidepoint(mouse_pos) else (100, 200, 100)
            pygame.draw.rect(self.screen, button_color, back_rect, 0, 10)
            pygame.draw.rect(self.screen, BLACK, back_rect, 2, 10)
            
            # Use smaller font for back button to avoid text touching border
            back_text = FONT_MEDIUM.render("Back to Menu", True, WHITE)
            self.screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2, 
                                       back_rect.centery - back_text.get_height() // 2))
            
            if mouse_clicked and back_rect.collidepoint(mouse_pos):
                running = False
            
            pygame.display.flip()
            self.clock.tick(60)

def main():
    """Run the game with remote database support and enhanced statistics UI."""
    print("Running Memory Game with remote statistics enabled")
    # Create our custom GUI instead of the original
    game_gui = RemoteStatsGameGUI()
    game_gui.run()

if __name__ == "__main__":
    main() 