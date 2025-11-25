PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS player_game_stats;
DROP TABLE IF EXISTS stadiums;
DROP TABLE IF EXISTS games;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS teams;

------------------------------------------------------------
-- 1) TEAMS TABLE
------------------------------------------------------------
CREATE TABLE teams (
    team_id        INTEGER PRIMARY KEY,
    team_name      TEXT NOT NULL UNIQUE,
    conference     TEXT,
    city           TEXT,
    founded_year   INTEGER
);

------------------------------------------------------------
-- 2) PLAYERS TABLE
------------------------------------------------------------
CREATE TABLE players (
    player_id      INTEGER PRIMARY KEY,
    team_id        INTEGER,
    full_name      TEXT NOT NULL,
    position       TEXT,
    height_cm      REAL,
    weight_kg      REAL,
    birthdate      TEXT,
    country        TEXT,

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

------------------------------------------------------------
-- 3) GAMES TABLE
------------------------------------------------------------
DROP TABLE IF EXISTS games;

CREATE TABLE games (
    game_id INTEGER PRIMARY KEY,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    game_date TEXT NOT NULL,
    season TEXT NOT NULL,
    arena_name TEXT,
    
    -- NEW: game stats from games.csv
    home_team_score INTEGER,
    away_team_score INTEGER,
    fg_pct_home REAL,
    fg_pct_away REAL,
    ft_pct_home REAL,
    ft_pct_away REAL,
    fg3_pct_home REAL,
    fg3_pct_away REAL,
    ast_home INTEGER,
    ast_away INTEGER,
    reb_home INTEGER,
    reb_away INTEGER,
    home_team_wins INTEGER,

    stadium_id INTEGER,

    FOREIGN KEY(home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY(away_team_id) REFERENCES teams(team_id),
    FOREIGN KEY(stadium_id) REFERENCES stadiums(stadium_id)
);

------------------------------------------------------------
-- 4) STADIUMS TABLE
------------------------------------------------------------
CREATE TABLE stadiums (
    stadium_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id         INTEGER UNIQUE,
    stadium_name    TEXT NOT NULL,
    city            TEXT,
    capacity        INTEGER,

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

------------------------------------------------------------
-- 5) PLAYER GAME STATS TABLE
------------------------------------------------------------
CREATE TABLE player_game_stats (
    stat_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id          INTEGER NOT NULL,
    game_id            INTEGER NOT NULL,
    points             INTEGER DEFAULT 0,
    assists            INTEGER DEFAULT 0,
    rebounds           INTEGER DEFAULT 0,
    minutes_played     REAL DEFAULT 0,

    FOREIGN KEY (player_id)
        REFERENCES players(player_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (game_id)
        REFERENCES games(game_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE (player_id, game_id)
);
