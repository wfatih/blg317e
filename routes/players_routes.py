from flask import Blueprint, render_template, request, redirect
import sqlite3

# Blueprint oluştur
players_bp = Blueprint("players_bp", __name__)

# -------- PLAYERS LIST --------
@players_bp.route("/players")
def players_page():
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
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 1) PLAYER INFO
    player = cur.execute("""
        SELECT p.*, t.team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.player_id = ?
    """, (pid,)).fetchone()

    if not player:
        return "Player not found", 404

    # 2) PLAYER'S GAME STATS (JOIN games + player_game_stats)
    game_stats = cur.execute("""
        SELECT 
            g.game_id,
            g.game_date,
            g.home_team_id,
            g.away_team_id,
            g.home_team_score,
            g.away_team_score,
            t1.team_name AS home_team_name,
            t2.team_name AS away_team_name,

            s.points,
            s.assists,
            s.rebounds,
            s.minutes_played

        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        LEFT JOIN teams t1 ON g.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON g.away_team_id = t2.team_id

        WHERE s.player_id = ?
        ORDER BY g.game_date DESC
    """, (pid,)).fetchall()

    # 3) AVERAGE STATS
    avg_stats = cur.execute("""
        SELECT 
            AVG(points) AS avg_points,
            AVG(assists) AS avg_assists,
            AVG(rebounds) AS avg_rebounds,
            AVG(minutes_played) AS avg_minutes
        FROM player_game_stats
        WHERE player_id = ?
    """, (pid,)).fetchone()

    # 4) BEST GAME (highest points)
    best_game = cur.execute("""
        SELECT 
            s.points, s.assists, s.rebounds, s.minutes_played,
            g.game_date,
            t1.team_name AS home_team_name,
            t2.team_name AS away_team_name
        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        LEFT JOIN teams t1 ON g.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON g.away_team_id = t2.team_id
        WHERE s.player_id = ?
        ORDER BY s.points DESC
        LIMIT 1
    """, (pid,)).fetchone()

    # 5) STADIUMS PLAYER HAS PLAYED IN
    stadiums = cur.execute("""
        SELECT DISTINCT st.stadium_name, st.city, st.capacity
        FROM player_game_stats s
        JOIN games g ON s.game_id = g.game_id
        JOIN stadiums st ON g.stadium_id = st.stadium_id
        WHERE s.player_id = ?
    """, (pid,)).fetchall()

    return render_template(
        "players/player_view.html",
        player=player,
        game_stats=game_stats,
        avg_stats=avg_stats,
        best_game=best_game,
        stadiums=stadiums
    )
