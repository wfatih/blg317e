from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3

# Blueprint oluştur
players_bp = Blueprint("players_bp", __name__)

# -------- PLAYERS LIST --------
@players_bp.route("/players")
def players_page():
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # GET params
    team = request.args.get("team", "").strip()
    name = request.args.get("name", "").strip()
    page = int(request.args.get("page", 1))  # default page = 1
    per_page = 15

    # Base query
    query = """
        SELECT p.*, t.team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE 1 = 1
    """
    params = []

    # Filters
    if name:
        query += " AND p.full_name LIKE ?"
        params.append("%" + name + "%")

    if team:
        query += " AND t.team_name = ?"
        params.append(team)

    # COUNT for pagination
    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    total_rows = cur.execute(count_query, params).fetchone()[0]
    total_pages = (total_rows + per_page - 1) // per_page

    # Add LIMIT/OFFSET
    offset = (page - 1) * per_page
    query += " ORDER BY p.player_id LIMIT ? OFFSET ?"
    params += [per_page, offset]

    players = cur.execute(query, params).fetchall()

    # Dropdown Teams
    all_teams = cur.execute(
        "SELECT team_name FROM teams ORDER BY team_name"
    ).fetchall()

    return render_template(
        "players/players_list.html",
        players=players,
        teams=all_teams,
        page=page,
        total_pages=total_pages,
        name=name,
        team=team
    )



# -------- ADD PLAYER --------
@players_bp.route("/players/add", methods=["GET", "POST"])
def add_player():
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()

    if request.method == "POST":
        cur.execute("""
            INSERT INTO players (
                player_id, team_id, full_name, position,
                height_cm, weight_kg, birthdate, country
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["player_id"],
            request.form["team_id"] or None,
            request.form["full_name"],
            request.form["position"],
            request.form["height_cm"],
            request.form["weight_kg"],
            request.form["birthdate"],
            request.form["country"],
        ))
        con.commit()
        return redirect("/players")

    empty_player = {
        "player_id": "",
        "team_id": "",
        "full_name": "",
        "position": "",
        "height_cm": "",
        "weight_kg": "",
        "birthdate": "",
        "country": ""
    }

    return render_template(
        "players/players_form.html",
        title="Add Player",
        player=empty_player,
        teams=teams
    )


# -------- EDIT PLAYER --------
@players_bp.route("/players/edit/<int:pid>", methods=["GET", "POST"])
def edit_player(pid):
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    player = cur.execute(
        "SELECT * FROM players WHERE player_id=?", (pid,)
    ).fetchone()

    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()

    if request.method == "POST":
        cur.execute("""
            UPDATE players
            SET team_id = ?,
                full_name = ?,
                position = ?,
                height_cm = ?,
                weight_kg = ?,
                birthdate = ?,
                country = ?
            WHERE player_id = ?
        """, (
            request.form["team_id"] or None,
            request.form["full_name"],
            request.form["position"],
            request.form["height_cm"],
            request.form["weight_kg"],
            request.form["birthdate"],
            request.form["country"],
            pid
        ))
        con.commit()
        return redirect("/players")

    return render_template(
        "players/players_form.html",
        title="Edit Player",
        player=player,
        teams=teams
    )


# -------- DELETE PLAYER --------
@players_bp.route("/players/delete/<int:pid>")
def delete_player(pid):
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = sqlite3.connect("nba.db")
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()

    try:
        cur.execute("DELETE FROM players WHERE player_id=?", (pid,))
        con.commit()
    except Exception as e:
        print("Delete error:", e)

    return redirect("/players")

# -------- VIEW PLAYER --------
@players_bp.route("/players/view/<int:pid>")
def view_player(pid):
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 1) PLAYER INFO
    player = cur.execute("""
        SELECT 
            p.player_id,
            p.full_name,
            p.position,
            p.team_id,
            t.team_name,
            t.abbreviation,
            t.city,
            t.conference
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.player_id = ?
    """, (pid,)).fetchone()

    if not player:
        con.close()
        return "Player not found", 404

    # 2) PLAYER'S GAME STATS
    game_stats = cur.execute("""
        SELECT 
            g.game_id,
            g.game_date,
            g.season,
            g.home_team_id,
            g.away_team_id,
            g.home_team_score,
            g.away_team_score,
            t1.team_name AS home_team_name,
            t1.abbreviation AS home_team_abbr,
            t2.team_name AS away_team_name,
            t2.abbreviation AS away_team_abbr,
            s.points,
            s.assists,
            s.rebounds,
                             
            ROUND(s.minutes_played, 1) as minutes_played,
            CASE 
                WHEN g.home_team_id = ? AND g.home_team_score > g.away_team_score THEN 1
                WHEN g.away_team_id = ? AND g.away_team_score > g.home_team_score THEN 1
                ELSE 0
            END AS player_team_won
        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        LEFT JOIN teams t1 ON g.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON g.away_team_id = t2.team_id
        WHERE s.player_id = ?
        ORDER BY g.game_date DESC
    """, (player['team_id'], player['team_id'], pid)).fetchall()

    # 3) SEASON STATS (her sezon için ortalamalar)
    season_stats = cur.execute("""
        SELECT 
            g.season,
            COUNT(s.stat_id) AS games_played,
            ROUND(AVG(s.points), 1) AS avg_points,
            ROUND(AVG(s.assists), 1) AS avg_assists,
            ROUND(AVG(s.rebounds), 1) AS avg_rebounds,
            ROUND(AVG(s.minutes_played), 1) AS avg_minutes,
            CAST(SUM(s.points) AS INTEGER) AS total_points,
            CAST(SUM(s.assists) AS INTEGER) AS total_assists,
            CAST(SUM(s.rebounds) AS INTEGER) AS total_rebounds
        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        WHERE s.player_id = ?
        GROUP BY g.season
        ORDER BY g.season DESC
    """, (pid,)).fetchall()

    # 4) CAREER AVERAGES
    career_avg = cur.execute("""
        SELECT 
            COUNT(s.stat_id) AS total_games,
            ROUND(AVG(CAST(s.points AS REAL)), 1) AS avg_points,
            ROUND(AVG(CAST(s.assists AS REAL)), 1) AS avg_assists,
            ROUND(AVG(CAST(s.rebounds AS REAL)), 1) AS avg_rebounds,
            ROUND(AVG(CAST(s.minutes_played AS REAL)), 1) AS avg_minutes,
            SUM(CAST(s.points AS INTEGER)) AS total_points,
            MAX(CAST(s.points AS INTEGER)) AS career_high_points
        FROM player_game_stats s
        WHERE s.player_id = ?
    """, (pid,)).fetchone()

# 5) BEST GAME (Sıfırları filtreleyen versiyon)
    best_game = cur.execute("""
        SELECT 
            CAST(COALESCE(s.points, 0) AS INTEGER) AS points,
            CAST(COALESCE(s.assists, 0) AS INTEGER) AS assists,
            CAST(COALESCE(s.rebounds, 0) AS INTEGER) AS rebounds,
            CAST(COALESCE(s.minutes_played, 0) AS INTEGER) AS minutes_played,
            g.game_date,
            g.season,
            g.home_team_score,
            g.away_team_score,
            t1.team_name AS home_team_name,
            t1.abbreviation AS home_team_abbr,
            t2.team_name AS away_team_name,
            t2.abbreviation AS away_team_abbr
        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        LEFT JOIN teams t1 ON g.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON g.away_team_id = t2.team_id
        WHERE s.player_id = ? 
          AND s.points > 0  -- <--- KRİTİK EKLEME: Puanı 0 olan maçları (hatalı kayıtları) görmezden gel
        ORDER BY CAST(s.points AS INTEGER) DESC, CAST(s.rebounds AS INTEGER) DESC
        LIMIT 1
    """, (pid,)).fetchone()

    # 6) ARENAS PLAYER HAS PLAYED IN
    arenas = cur.execute("""
        SELECT DISTINCT 
            t.arena AS stadium_name,
            t.city,
            t.arenacapacity AS capacity,
            COUNT(DISTINCT g.game_id) AS games_played
        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        JOIN teams t ON g.home_team_id = t.team_id
        WHERE s.player_id = ? AND t.arena IS NOT NULL
        GROUP BY t.arena, t.city, t.arenacapacity
        ORDER BY games_played DESC
    """, (pid,)).fetchall()

    # 7) OPPONENTS FACED (en çok karşılaştığı takımlar)
    # 7) OPPONENTS FACED (GÜNCELLENMİŞ - KOMPLEKS SORGU)
    # Kriterler: Nested Query, 4+ Table Join, Group By, Outer Join
    opponents = cur.execute("""
        SELECT 
            t.team_name,
            t.abbreviation,
            s_venue.stadium_name,  -- 4. Tablo (Stadiums)
            
            -- Nested Query: Oyuncunun genel kariyer puan ortalamasını getirir
            (SELECT ROUND(AVG(points), 1) FROM player_game_stats WHERE player_id = ?) as career_avg_pts,
            
            COUNT(g.game_id) AS games_against,
            ROUND(AVG(s.points), 1) AS avg_points_vs,
            ROUND(AVG(s.assists), 1) AS avg_assists_vs,
            ROUND(AVG(s.rebounds), 1) AS avg_rebounds_vs
            
        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        
        -- Complex Join Logic: Rakip takımı bulmak için
        JOIN teams t ON (
            CASE 
                WHEN g.home_team_id = ? THEN g.away_team_id
                ELSE g.home_team_id
            END = t.team_id
        )
        
        -- Outer Join: Stadyum bilgisi (4. Tablo Bağlantısı)
        LEFT JOIN stadiums s_venue ON t.team_id = s_venue.team_id

        WHERE s.player_id = ?
        
        -- Group By
        GROUP BY t.team_id
        ORDER BY games_against DESC
        LIMIT 10
    """, (pid, player['team_id'], pid)).fetchall()

    con.close()

    return render_template(
        "players/player_view.html",
        player=player,
        game_stats=game_stats,
        season_stats=season_stats,
        career_avg=career_avg,
        best_game=best_game,
        arenas=arenas,
        opponents=opponents
    )