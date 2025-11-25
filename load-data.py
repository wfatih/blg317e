import csv
import sqlite3

DB = "nba.db"

con = sqlite3.connect(DB)
cur = con.cursor()

con.execute("PRAGMA foreign_keys = ON;")

# -----------------------------
# 1) TEAMS
# -----------------------------
print("Loading teams...")

with open("data/teams.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("""
            INSERT OR IGNORE INTO teams (team_id, team_name, conference, city, founded_year)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row["TEAM_ID"],
            row["NICKNAME"],
            None,
            row["CITY"],
            row["YEARFOUNDED"]
        ))


# -----------------------------
# 2) PLAYERS
# -----------------------------
print("Loading players...")

with open("data/players.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("""
            INSERT OR IGNORE INTO players (
                player_id, team_id, full_name, position,
                height_cm, weight_kg, birthdate, country
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["PLAYER_ID"],
            row["TEAM_ID"],
            row["PLAYER_NAME"],
            None,
            None,
            None,
            None,
            None
        ))


# -----------------------------
# 3) GAMES
# -----------------------------
print("Loading games...")

with open("data/games.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("""
            INSERT OR IGNORE INTO games (
                game_id, home_team_id, away_team_id, game_date, season, arena_name
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row["GAME_ID"],
            row["HOME_TEAM_ID"],
            row["VISITOR_TEAM_ID"],
            row["GAME_DATE_EST"],
            row["SEASON"],
            None
        ))


# -----------------------------
# 4) PLAYER GAME STATS
# -----------------------------
print("Loading game details...")

with open("data/games_details.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:

        player_id = row["PLAYER_ID"]
        game_id = row["GAME_ID"]
        full_name = row["PLAYER_NAME"]

        # 1) Eğer player yoksa → otomatik oluştur
        cur.execute("SELECT 1 FROM players WHERE player_id = ?", (player_id,))
        if cur.fetchone() is None:
            cur.execute("""
                INSERT INTO players (player_id, full_name)
                VALUES (?, ?)
            """, (player_id, full_name))

        # 2) Eğer game yoksa → o satırı atla (bu çok nadir olur)
        cur.execute("SELECT 1 FROM games WHERE game_id = ?", (game_id,))
        if cur.fetchone() is None:
            continue

        # 3) dakika formatı (18:06, 29.00000, vb.)
        minutes_raw = row["MIN"]

        if not minutes_raw or minutes_raw.strip() == "":
            minutes = 0
        elif ":" in minutes_raw:
            m, s = minutes_raw.split(":")
            minutes = float(m) + float(s) / 60
        else:
            try:
                minutes = float(minutes_raw)
            except:
                minutes = 0

        # 4) INSERT
        cur.execute("""
            INSERT OR IGNORE INTO player_game_stats (
                player_id, game_id, points, assists, rebounds, minutes_played
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            player_id,
            game_id,
            row["PTS"],
            row["AST"],
            row["REB"],
            minutes
        ))


con.commit()
con.close()

print("Import finished successfully!")
