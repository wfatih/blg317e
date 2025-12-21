# Slide 1: Team Introduction - Group "Segmentation"
Layout Instruction: Create a slide with a 5-column layout or a clean grid to introduce the team members. Each entry should have a placeholder for a photo, the name, student number, and their specific role in the project.

Content to insert:
1. Alperen BUDAK (150220028)
   - Role: Player Data Manager
   - Responsibility: Maintains player profiles, physical stats, and team links.
2. Fatih ÇAKIR (150220086)
   - Role: Match & Schedule Coordinator
   - Responsibility: Documents match details including teams, dates, and venues.
3. Bahadır Selim BAKLA (150220001)
   - Role: Team Operations Lead
   - Responsibility: Manages core information of all NBA teams.
4. Emre TOY (150200023)
   - Role: Performance Metrics Analyst
   - Responsibility: Analyzes player performance metrics for individual games.
5. Çağan ÇOBANOĞLU (150210315)
   - Role: Arena & Infrastructure Manager
   - Responsibility: Records arena details including capacity and home teams.

# Slide 2: Project Overview: NBA Game Database Application
Layout Instruction: Split layout. On the left side, use bullet points for text. On the right side, place an illustrative image of a web dashboard or a database server icon.

Content to insert:
The Application:
- A web-based Database Management System (Admin Panel) designed to store, manage, and analyze NBA historical data.
- Built to handle complex relationships between players, teams, games, and arenas.

Motivation:
- Data Volume: The dataset contains detailed info about NBA games from the 2004 season onward.
- Complexity: Managing match results, player statistics, and team rankings requires a structured relational database rather than flat files.
- Analytics: Designed to support projects like predicting game outcomes or analyzing team and player performance trends.

Project Goals:
- Normalization: Convert raw data into a structured 3NF/BCNF relational schema.
- Management: Provide a user-friendly interface for CRUD operations on NBA entities.
- Insight: Enable complex queries to extract meaningful statistics (e.g., Triple-Doubles, Home Court Advantage).

# Slide 3: Entity-Relationship (ER) Diagram Structure
Layout Instruction: Split layout. Left side text explaining the visual syntax used in the class (Chen/Crow's Foot notation). Right side is reserved for the ER Diagram image.

Content to insert:
Visual Syntax Explained:
- Rectangles (Entities): Represent real-world objects. (Project Examples: Players, Teams, Games, Stadiums).
- Diamonds (Relationships): Represent interactions between entities.
  - Example: "Plays_for" connects Players to Teams (N:1).
  - Example: "Hosted_at" connects Games to Stadiums.
- Ellipses (Attributes): Data points describing entities. (Examples: full_name, capacity, game_date).
- Key Attributes (Underlined): Unique identifiers like player_id or team_id.

Structural Constraints (Cardinality):
- 1:N (One-to-Many): A team has many players, but a player belongs to one team.
- 1:1 (One-to-One): Modeled between Teams and Stadiums (Each team has one home arena).

# Slide 4: ER-to-Relational Mapping
Layout Instruction: A flowchart or "Problem -> Solution" layout demonstrating how logical designs turn into physical tables.

Content to insert:
1. Mapping Strong Entities:
   - Each entity rectangle (Teams, Players, Games) becomes a separate table.
   - Primary Keys (team_id, game_id) are preserved.

2. Mapping 1:N Relationships (Foreign Keys):
   - Rule: Place the Foreign Key on the "Many" side.
   - Implementation: The team_id is added as a Foreign Key inside the Players table.

3. Mapping 1:1 Relationships (Unique Constraints):
   - Scenario: Teams ↔ Stadiums.
   - Implementation: team_id is added to the Stadiums table with a UNIQUE constraint to ensure strict 1:1 mapping.

4. Mapping M:N Relationships (The Junction Table):
   - Scenario: Players ↔ Games (Many players play in many games).
   - Solution: Created an associative table named Player_Game_Stats.
   - Structure: Includes FKs (player_id, game_id), Attributes (points, assists), and a Composite Unique Key.

# Slide 5: Normalization: From Chaos to 3NF
Layout Instruction: Two-column comparison layout. Left Column Title: "Unnormalized Data (Issues)", Right Column Title: "Normalized Schema (3NF Solution)".

Content to insert:
Left Side (The Problem):
- Display this dataset as a table:
  - Row 1: LeBron, Lakers, Crypto Arena, 19000, 25 pts
  - Row 2: LeBron, Lakers, Crypto Arena, 19000, 30 pts
  - Row 3: Davis, Lakers, Crypto Arena, 19000, 20 pts
- Issues highlighted:
  - Redundancy: "Crypto Arena" and "19000" are repeated unnecessarily.
  - Transitive Dependency: Capacity depends on Arena, not the Player.

Right Side (The Solution):
- Explain that we split this into dedicated tables:
  - Teams Table: Stores Team Name & City.
  - Stadiums Table: Stores Capacity (Fixed the dependency).
  - Games & Stats Table: Stores only score info.
- Benefit: Eliminates data duplication and prevents update anomalies.

# Slide 6: Dataset Overview & Statistics
Layout Instruction: Infographic style. Split the slide into "Source Info" (Text) and "Volume Statistics" (Big Numbers/Icons).

Content to insert:
1. Data Source & Scope:
   - Source: "NBA Games Data" by Nathan Lauga (Kaggle).
   - Origin: Originally collected via the official NBA Stats API.
   - Coverage: Detailed NBA game data from the 2004 season onward.
   - Authenticity: No synthetic data was used. All records represent real historical NBA match results.

2. Data Parsing Strategy:
   - The raw data was obtained in CSV format.
   - Parsing: We used Python scripts to parse, clean, and normalize these CSV files before importing them into our SQLite database.

3. Data Volume (Key Metrics):
   - 668,000+ Game Details (Player performance records per match).
   - 210,343 Ranking Records.
   - 26,652 Unique Games Played.
   - 7,229 Players Profiled.
   - 31 Teams.

# Slide 7: Application Features
Layout Instruction: 3-Column Layout with placeholders for Screenshots.

Content to insert:
(Leave empty for screenshots)

# Slide 8: Advanced SQL Analytics
Layout Instruction: Create 3 distinct sections (or a carousel layout) covering Players, Teams, and Games. Show the SQL code on one side and the "Insight/Explanation" on the other.

Content to insert:
SECTION 1: PLAYER ANALYTICS

Query 1: The "Tragic Hero" (High Score but Lost)
- Goal: Find games where a player scored 40+ points, but their team still lost.
- Complexity: Requires joining 3 tables (Players -> Stats -> Games) and complex Boolean logic.
SQL Logic:
```sql
SELECT p.full_name, s.points,
       (g.home_team_score || '-' || g.away_team_score) as score
FROM player_game_stats s
JOIN players p ON s.player_id = p.player_id
JOIN games g ON s.game_id = g.game_id
WHERE s.points >= 40
  AND (
    (p.team_id = g.home_team_id AND g.home_team_wins = 0) OR
    (p.team_id = g.away_team_id AND g.home_team_wins = 1)
  );

Query 2: Consistent All-Rounders (Triple-Double Hunter)

Goal: Identify players with the most "Triple-Doubles".

Complexity: Uses COUNT, GROUP BY, and multiple conditional checks inside the WHERE clause. SQL Logic:

SQL

SELECT p.full_name, COUNT(s.game_id) as td_count
FROM player_game_stats s
JOIN players p ON s.player_id = p.player_id
WHERE s.points >= 10 AND s.assists >= 10 AND s.rebounds >= 10
GROUP BY p.player_id
ORDER BY td_count DESC
LIMIT 5;
SECTION 2: TEAM ANALYTICS

Query 3: Total Offensive Output (Union Technique)

Goal: Calculate total points scored by a team in a season (combining Home and Away games).

Complexity: Uses a Subquery with UNION ALL to normalize the dataset. SQL Logic:

SQL

SELECT t.team_name, SUM(total_pts) as season_points
FROM (
    SELECT home_team_id as tid, home_team_score as total_pts FROM games
    UNION ALL
    SELECT away_team_id as tid, away_team_score as total_pts FROM games
) as combined
JOIN teams t ON combined.tid = t.team_id
GROUP BY t.team_id
ORDER BY season_points DESC;
Query 4: Home Fortress Efficiency

Goal: Compare Home Win Rate vs. Away Win Rate.

Complexity: Uses AVG with CASE WHEN dynamically. SQL Logic:

SQL

SELECT t.team_name,
   AVG(CASE WHEN home_team_wins = 1 THEN 1.0 ELSE 0.0 END) as home_win_pct,
   AVG(CASE WHEN home_team_wins = 0 THEN 1.0 ELSE 0.0 END) as away_win_pct
FROM games g
JOIN teams t ON g.home_team_id = t.team_id
GROUP BY t.team_id;
SECTION 3: GAME ANALYTICS

Query 5: Nail-Biter Thrillers

Goal: Find the highest-scoring games decided by 3 points or less.

Complexity: Mathematical operations in WHERE clause. SQL Logic:

SQL

SELECT g.game_date,
       t1.team_name || ' vs ' || t2.team_name as match,
       (g.home_team_score + g.away_team_score) as total_points
FROM games g
JOIN teams t1 ON g.home_team_id = t1.team_id
JOIN teams t2 ON g.away_team_id = t2.team_id
WHERE ABS(g.home_team_score - g.away_team_score) <= 3
ORDER BY total_points DESC
LIMIT 5;
Query 6: Arena Utilization Stats

Goal: Calculate the average total score seen in each arena.

Complexity: Joins Stadiums to Games and aggregates score data. SQL Logic:

SQL

SELECT s.stadium_name, COUNT(g.game_id) as games_hosted,
       AVG(g.home_team_score + g.away_team_score) as avg_total_score
FROM stadiums s
JOIN games g ON s.stadium_id = g.stadium_id
GROUP BY s.stadium_id
ORDER BY avg_total_score DESC;
Slide 9: Testing Strategy & Results
Layout Instruction: Grid layout or 4 distinct quadrants. Each quadrant represents a testing category with a "Checkmark" icon.

Content to insert:

Database Integrity Testing (Constraints):

Test Case: Attempted to delete a "Team" that has assigned "Players".

Expected Result: Due to ON DELETE SET NULL constraint, the team is deleted, and players' team_id is automatically set to NULL.

Outcome: Pass. (Referential integrity preserved).

Test Case: Tried assigning two Teams to the same Stadium.

Outcome: Pass. (Blocked by the UNIQUE(team_id) constraint).

Performance & Volume Testing:

Scenario: Loading the "Game Statistics" page with 668,000+ records.

Issue: Initial load without pagination was slow.

Solution: Implemented SQL LIMIT/OFFSET pagination in Flask.

Outcome: Pass. (Page load time reduced to <1 second).

Security & Access Control:

Test Case: Unauthenticated user trying to access /players/add via direct URL.

Mechanism: Flask Session check (if "logged_in" not in session).

Outcome: Pass. (Redirects to Login Page).

Data Validation (Edge Cases):

Test Case: Entering a negative value for "Stadium Capacity" or "Player Height".

Outcome: Pass. (Form validation prevented invalid data entry).