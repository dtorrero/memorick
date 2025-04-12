-- Add test data to the game_stats table
INSERT INTO game_stats (player_name, difficulty, start_time, end_time, duration_seconds, moves, matches, errors, completed)
VALUES 
('Alice', 'Easy', 1712000000, 1712000045, 45.5, 10, 8, 2, 1),
('Bob', 'Easy', 1712001000, 1712001060, 60.2, 12, 8, 4, 1),
('Charlie', 'Easy', 1712002000, 1712002035, 35.3, 9, 8, 1, 1),
('David', 'Medium', 1712003000, 1712003150, 150.7, 22, 18, 4, 1),
('Emma', 'Medium', 1712004000, 1712004180, 180.4, 24, 18, 6, 1),
('Frank', 'Hard', 1712005000, 1712005450, 450.1, 60, 50, 10, 1),
('Grace', 'Hard', 1712006000, 1712006520, 520.8, 65, 50, 15, 1),
('Hannah', 'Easy', 1712007000, 1712007042, 42.3, 10, 8, 2, 1),
('Ian', 'Medium', 1712008000, 1712008130, 130.5, 20, 18, 2, 1),
('Julia', 'Hard', 1712009000, 1712009400, 400.2, 58, 50, 8, 1); 