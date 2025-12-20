import csv
import sqlite3
import os

DB = "nba.db"

# --- LİNKLER (Proxy Korumalı - Sorunsuz) ---
ALL_LEGENDS = {
    "1610612737": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/4/4e/Dominique_Wilkins_2018.jpg&w=600",
    "1610612738": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/6/6f/Larry_Bird_Lipofsky.jpg&w=600",
    "1610612751": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/d/d4/Julius_Erving_1981.jpg&w=600",
    "1610612766": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/f/fe/Kemba_Walker_2014.jpg&w=600",
    "1610612741": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/b/b3/Jordan_Lipofsky.jpg&w=600",
    "1610612739": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/c/cf/LeBron_James_crop_%282012%29.jpg&w=600",
    "1610612742": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/7/7c/Dirk_Nowitzki_2010.jpg&w=600",
    "1610612743": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/3/36/Nikola_Joki%C4%87_free_throw_%28cropped%29.jpg&w=600",
    "1610612765": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/5/52/Isiah_Thomas_2012.jpg&w=600",
    "1610612744": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/3/36/Stephen_Curry_dribbling_2016_%28cropped%29.jpg&w=600",
    "1610612745": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/1/13/Hakeem_Olajuwon_Lipofsky.jpg&w=600",
    "1610612754": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/2/27/Reggie_Miller_2019.jpg&w=600",
    "1610612746": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/d/d3/Kawhi_Leonard_dribbling_2019_%28cropped%29.jpg&w=600",
    "1610612747": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/5/56/Kobe_Bryant_2014.jpg&w=600",
    "1610612763": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/1/1a/Ja_Morant_dribbling_2019_%28cropped%29.jpg&w=600",
    "1610612748": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/4/4d/Dwyane_Wade_waving_2018.jpg&w=600",
    "1610612749": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/9/93/Giannis_Antetokounmpo_2019.jpg&w=600",
    "1610612750": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/5/57/Kevin_Garnett_2008.jpg&w=600",
    "1610612740": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/7/72/Anthony_Davis_2013.jpg&w=600",
    "1610612752": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/a/ae/Patrick_Ewing_Lipofsky.jpg&w=600",
    "1610612760": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/b/b5/Kevin_Durant_2014.jpg&w=600",
    "1610612753": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/e/ea/Shaquille_O%27Neal_2009.jpg&w=600",
    "1610612755": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/c/c9/Allen_Iverson_Lipofsky.jpg&w=600",
    "1610612756": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/1/10/Steve_Nash_2008.jpg&w=600",
    "1610612757": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/d/df/Damian_Lillard_2018.jpg&w=600",
    "1610612758": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/c/cb/Chris_Webber_1.jpg&w=600",
    "1610612759": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/0/05/Tim_Duncan_2013.jpg&w=600",
    "1610612761": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/e/e3/Vince_Carter_dunk.jpg&w=600",
    "1610612762": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/9/90/Karl_Malone_Lipofsky.jpg&w=600",
    "1610612764": "https://wsrv.nl/?url=upload.wikimedia.org/wikipedia/commons/2/29/John_Wall_2014.jpg&w=600"
}
FALLBACK_IMG = "https://cdn.nba.com/manage/2021/08/nba-75th-anniversary-logo-white-background.jpg"

if os.path.exists(DB):
    try:
        os.remove(DB)
        print("Eski DB silindi.")
    except:
        pass

con = sqlite3.connect(DB)
cur = con.cursor()
con.execute("PRAGMA foreign_keys = ON;")

# --- TABLOLAR ---
cur.executescript("""
    DROP TABLE IF EXISTS player_game_stats;
    DROP TABLE IF EXISTS stadiums;
    DROP TABLE IF EXISTS games;
    DROP TABLE IF EXISTS players;
    DROP TABLE IF EXISTS teams;

    CREATE TABLE teams (
        team_id             INTEGER PRIMARY KEY,
        team_name           TEXT, nickname TEXT, abbreviation TEXT, conference TEXT,
        city                TEXT, founded_year INTEGER, owner TEXT, generalmanager TEXT,
        headcoach           TEXT, dleagueaffiliation TEXT, arena TEXT, arenacapacity INTEGER,
        legendary_player_img TEXT 
    );
    CREATE TABLE players (player_id INTEGER PRIMARY KEY, team_id INTEGER, full_name TEXT, position TEXT, height_cm REAL, weight_kg REAL, birthdate TEXT, country TEXT, FOREIGN KEY (team_id) REFERENCES teams(team_id));
    CREATE TABLE stadiums (stadium_id INTEGER PRIMARY KEY AUTOINCREMENT, team_id INTEGER UNIQUE, stadium_name TEXT, city TEXT, capacity INTEGER, FOREIGN KEY (team_id) REFERENCES teams(team_id));
    CREATE TABLE games (game_id INTEGER PRIMARY KEY, home_team_id INTEGER, away_team_id INTEGER, game_date TEXT, season TEXT, arena_name TEXT, home_team_score INTEGER, away_team_score INTEGER, fg_pct_home REAL, fg_pct_away REAL, ft_pct_home REAL, ft_pct_away REAL, fg3_pct_home REAL, fg3_pct_away REAL, ast_home INTEGER, ast_away INTEGER, reb_home INTEGER, reb_away INTEGER, home_team_wins INTEGER, stadium_id INTEGER, FOREIGN KEY(home_team_id) REFERENCES teams(team_id), FOREIGN KEY(away_team_id) REFERENCES teams(team_id), FOREIGN KEY(stadium_id) REFERENCES stadiums(stadium_id));
    CREATE TABLE player_game_stats (stat_id INTEGER PRIMARY KEY AUTOINCREMENT, player_id INTEGER, game_id INTEGER, points INTEGER, assists INTEGER, rebounds INTEGER, minutes_played REAL, FOREIGN KEY (player_id) REFERENCES players(player_id), FOREIGN KEY (game_id) REFERENCES games(game_id), UNIQUE (player_id, game_id));
""")

print("--- TAKIMLAR YÜKLENİYOR ---")
with open("data/teams.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    # Header temizliği
    reader.fieldnames = [name.strip() for name in reader.fieldnames]
    
    for row in reader:
        raw_id = row.get("TEAM_ID", "").strip()
        assigned_img = ALL_LEGENDS.get(raw_id, FALLBACK_IMG)
        
        # LOG
        if raw_id in ALL_LEGENDS:
            print(f"✅ {row.get('NICKNAME'):<15} -> EKLENDİ")
        
        cap = row.get("ARENACAPACITY", 0)
        if not cap: cap = 0

        cur.execute("INSERT OR IGNORE INTO teams (team_id, team_name, nickname, abbreviation, city, founded_year, owner, generalmanager, headcoach, dleagueaffiliation, arena, arenacapacity, legendary_player_img) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (raw_id, f"{row.get('CITY')} {row.get('NICKNAME')}", row.get("NICKNAME"), row.get("ABBREVIATION"), row.get("CITY"), row.get("YEARFOUNDED"), row.get("OWNER"), row.get("GENERALMANAGER"), row.get("HEADCOACH"), row.get("DLEAGUEAFFILIATION"), row.get("ARENA"), cap, assigned_img))
        
        if row.get("ARENA"):
            cur.execute("INSERT OR IGNORE INTO stadiums (team_id, stadium_name, city, capacity) VALUES (?,?,?,?)", (raw_id, row.get("ARENA"), row.get("CITY"), cap))

print("\n--- OYUNCULAR & MAÇLAR YÜKLENİYOR ---")
with open("data/players.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("INSERT OR IGNORE INTO players (player_id, team_id, full_name) VALUES (?, ?, ?)", (row["PLAYER_ID"], row["TEAM_ID"], row["PLAYER_NAME"]))

with open("data/games.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute("INSERT OR IGNORE INTO games (game_id, home_team_id, away_team_id, game_date, season, home_team_score, away_team_score, home_team_wins) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (row["GAME_ID"], row["HOME_TEAM_ID"], row["VISITOR_TEAM_ID"], row["GAME_DATE_EST"], row["SEASON"], row["PTS_home"], row["PTS_away"], row["HOME_TEAM_WINS"]))

print("--- DETAYLAR YÜKLENİYOR (Hataları atlıyoruz) ---")
with open("data/games_details.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            m = row.get("MIN", "0")
            min_val = float(m.split(":")[0]) + float(m.split(":")[1])/60 if ":" in m else (float(m) if m else 0)
            
            # BURADA HATA OLURSA SESSİZCE GEÇECEK (try-except)
            cur.execute("INSERT INTO player_game_stats (player_id, game_id, points, assists, rebounds, minutes_played) VALUES (?, ?, ?, ?, ?, ?)",
                       (row["PLAYER_ID"], row["GAME_ID"], row["PTS"], row["AST"], row["REB"], min_val))
        except sqlite3.IntegrityError:
            # Foreign Key hatası veren satırları atla
            continue
        except Exception:
            continue

con.commit()
con.close()
print("\n🔥 İŞLEM BAŞARIYLA TAMAMLANDI! 🔥")
print("Artık sayfayı yenileyebilirsin.")