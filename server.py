from datetime import datetime
import sqlite3

from flask import Flask, render_template, request, redirect, url_for


app = Flask(__name__)

# -------- HOME --------
@app.route("/")
def home_page():
    today = datetime.today()
    day_name = today.strftime("%A")
    return render_template("home.html", date=day_name)

# -------- ARENAS PAGE --------
@app.route("/arenas", methods=["GET", "POST"])
def arenas_page():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Handle Search
    search_query = request.args.get("search", "")
    if search_query:
        query = """
            SELECT s.*, t.team_name 
            FROM stadiums s 
            LEFT JOIN teams t ON s.team_id = t.team_id
            WHERE s.stadium_name LIKE ? OR s.city LIKE ? OR t.team_name LIKE ?
        """
        like_val = f"%{search_query}%"
        cur.execute(query, (like_val, like_val, like_val))
    else:
        query = """
            SELECT s.*, t.team_name 
            FROM stadiums s 
            LEFT JOIN teams t ON s.team_id = t.team_id
        """
        cur.execute(query)
    
    arenas = cur.fetchall()

    # Get Teams for Dropdown
    cur.execute("SELECT * FROM teams")
    teams = cur.fetchall()

    con.close()
    return render_template("arenas.html", arenas=arenas, teams=teams)

@app.route("/arenas/add", methods=["POST"])
def add_arena():
    stadium_name = request.form.get("stadium_name")
    city = request.form.get("city")
    capacity = request.form.get("capacity")
    team_id = request.form.get("team_id")

    if not team_id:
        team_id = None

    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    query = "INSERT INTO stadiums (stadium_name, city, capacity, team_id) VALUES (?, ?, ?, ?)"
    cur.execute(query, (stadium_name, city, capacity, team_id))
    con.commit()
    con.close()
    return redirect(url_for("arenas_page"))

@app.route("/arenas/delete/<int:id>", methods=["POST"])
def delete_arena(id):
    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    cur.execute("DELETE FROM stadiums WHERE stadium_id = ?", (id,))
    con.commit()
    con.close()
    return redirect(url_for("arenas_page"))

@app.route("/arenas/update/<int:id>", methods=["POST"])
def update_arena(id):
    stadium_name = request.form.get("stadium_name")
    city = request.form.get("city")
    capacity = request.form.get("capacity")
    team_id = request.form.get("team_id")

    if not team_id:
        team_id = None

    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    query = """
        UPDATE stadiums 
        SET stadium_name=?, city=?, capacity=?, team_id=? 
        WHERE stadium_id=?
    """
    cur.execute(query, (stadium_name, city, capacity, team_id, id))
    con.commit()
    con.close()
    return redirect(url_for("arenas_page"))


# -------- ABOUT PROJECT PAGE --------
@app.route("/about")
def about_page():
    return render_template("about.html")



@app.route("/games")
def games_list():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    con.execute("PRAGMA foreign_keys = ON;")

    games = cur.execute("""
        SELECT 
            g.*,
            t1.team_name AS home_team,
            t2.team_name AS away_team,
            s.stadium_name AS stadium_name
        FROM games g
        JOIN teams t1 ON g.home_team_id = t1.team_id
        JOIN teams t2 ON g.away_team_id = t2.team_id
        LEFT JOIN stadiums s ON g.stadium_id = s.stadium_id
        ORDER BY g.game_id
    """).fetchall()

    return render_template("games_list.html", games=games)


@app.route("/games/add", methods=["GET", "POST"])
def add_game():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()
    stadiums = cur.execute("SELECT * FROM stadiums ORDER BY stadium_name").fetchall()

    if request.method == "POST":
        cur.execute("""
            INSERT INTO games (
                game_id, home_team_id, away_team_id, stadium_id,
                game_date, season, arena_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["game_id"],
            request.form["home_team_id"],
            request.form["away_team_id"],
            request.form["stadium_id"] or None,
            request.form["game_date"],
            request.form["season"],
            request.form["arena_name"]
        ))

        con.commit()
        return redirect("/games")

    empty_game = {
        "game_id": "",
        "home_team_id": "",
        "away_team_id": "",
        "stadium_id": "",
        "game_date": "",
        "season": "",
        "arena_name": ""
    }

    return render_template("games_form.html", title="Add Game", game=empty_game, teams=teams, stadiums=stadiums)
@app.route("/games/edit/<int:gid>", methods=["GET", "POST"])
def edit_game(gid):
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    game = cur.execute("SELECT * FROM games WHERE game_id=?", (gid,)).fetchone()
    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()
    stadiums = cur.execute("SELECT * FROM stadiums ORDER BY stadium_name").fetchall()

    if request.method == "POST":
        cur.execute("""
            UPDATE games SET
                home_team_id=?,
                away_team_id=?,
                stadium_id=?,
                game_date=?,
                season=?,
                arena_name=?
            WHERE game_id=?
        """, (
            request.form["home_team_id"],
            request.form["away_team_id"],
            request.form["stadium_id"] or None,
            request.form["game_date"],
            request.form["season"],
            request.form["arena_name"],
            gid
        ))

        con.commit()
        return redirect("/games")

    return render_template("games_form.html", title="Edit Game", game=game, teams=teams, stadiums=stadiums)

@app.route("/games/delete/<int:gid>")
def delete_game(gid):
    con = sqlite3.connect("nba.db")
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()

    try:
        cur.execute("DELETE FROM games WHERE game_id=?", (gid,))
        con.commit()
    except Exception as e:
        print("Error deleting:", e)

    return redirect("/games")

# -------- PLAYERS LIST --------
@app.route("/players")
def players_page():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    players = cur.execute("""
        SELECT 
            p.*,
            t.team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        ORDER BY p.player_id
    """).fetchall()

    return render_template("players_list.html", players=players)


# -------- ADD PLAYER --------
@app.route("/players/add", methods=["GET", "POST"])
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
        "players_form.html",
        title="Add Player",
        player=empty_player,
        teams=teams
    )


# -------- EDIT PLAYER --------
@app.route("/players/edit/<int:pid>", methods=["GET", "POST"])
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
        "players_form.html",
        title="Edit Player",
        player=player,
        teams=teams
    )


# -------- DELETE PLAYER --------
@app.route("/players/delete/<int:pid>")
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

# -------- TEAMS LIST --------
@app.route("/teams")
def teams_page():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    teams = cur.execute("""
        SELECT * FROM teams
        ORDER BY team_id
    """).fetchall()

    return render_template("teams_list.html", teams=teams)

# -------- ADD TEAM --------
@app.route("/teams/add", methods=["GET", "POST"])
def add_team():
    con = sqlite3.connect("nba.db")
    cur = con.cursor()

    if request.method == "POST":
        cur.execute("""
            INSERT INTO teams (
                team_id, team_name, conference, city, founded_year
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            request.form["team_id"],
            request.form["team_name"],
            request.form["conference"],
            request.form["city"],
            request.form["founded_year"]
        ))

        con.commit()
        return redirect("/teams")

    empty_team = {
        "team_id": "",
        "team_name": "",
        "conference": "",
        "city": "",
        "founded_year": "",
    }

    return render_template("teams_form.html", title="Add Team", team=empty_team)

# -------- EDIT TEAM --------
@app.route("/teams/edit/<int:tid>", methods=["GET", "POST"])
def edit_team(tid):
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    team = cur.execute(
        "SELECT * FROM teams WHERE team_id=?", (tid,)
    ).fetchone()

    if request.method == "POST":
        cur.execute("""
            UPDATE teams
            SET team_name = ?,
                conference = ?,
                city = ?,
                founded_year = ?
            WHERE team_id = ?
        """, (
            request.form["team_name"],
            request.form["conference"],
            request.form["city"],
            request.form["founded_year"],
            tid
        ))

        con.commit()
        return redirect("/teams")

    return render_template("teams_form.html", title="Edit Team", team=team)


# -------- DELETE TEAM --------
@app.route("/teams/delete/<int:tid>")
def delete_team(tid):
    con = sqlite3.connect("nba.db")
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()

    try:
        cur.execute("DELETE FROM teams WHERE team_id=?", (tid,))
        con.commit()
    except Exception as e:
        print("Delete error:", e)

    return redirect("/teams")


# -------- STATISTICS LIST --------
@app.route("/statistics")
def statistics_page():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Get page number from query string, default to 1
    page = request.args.get('page', 1, type=int)
    per_page = 5000  # Show 5000 records per page
    offset = (page - 1) * per_page

    # Get total count
    total = cur.execute("SELECT COUNT(*) FROM player_game_stats").fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    # Get paginated results
    statistics = cur.execute("""
        SELECT * FROM player_game_stats
        ORDER BY stat_id
        LIMIT ? OFFSET ?
    """, (per_page, offset)).fetchall()

    return render_template(
        "statistics_list.html", 
        statistics=statistics,
        page=page,
        total_pages=total_pages
    )

# -------- ADD STATISTIC --------
@app.route("/statistics/add", methods=["GET", "POST"])
def add_statistic():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    players = cur.execute("SELECT * FROM players ORDER BY full_name").fetchall()
    games = cur.execute("SELECT * FROM games ORDER BY game_id").fetchall()

    if request.method == "POST":
        cur.execute("""
            INSERT INTO player_game_stats (
                stat_id, player_id, game_id, points, assists, rebounds, minutes_played
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["stat_id"],
            request.form["player_id"],
            request.form["game_id"],
            request.form["points"],
            request.form["assists"],
            request.form["rebounds"],
            request.form["minutes_played"]
        ))

        con.commit()
        return redirect("/statistics")

    empty_statistic = {
        "stat_id": "",
        "player_id": "",
        "game_id": "",
        "points": "",
        "assists": "",
        "rebounds": "",
        "minutes_played": "",
    }

    return render_template(
        "statistics_form.html", 
        title="Add Statistic",
        statistic=empty_statistic, 
        players=players, 
        games=games
    )

# -------- EDIT STATISTIC --------
@app.route("/statistics/edit/<int:sid>", methods=["GET", "POST"])
def edit_statistic(sid):
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    players = cur.execute("SELECT * FROM players ORDER BY full_name").fetchall()
    games = cur.execute("SELECT * FROM games ORDER BY game_id").fetchall()

    statistic = cur.execute(
        "SELECT * FROM player_game_stats WHERE stat_id=?", (sid,)
    ).fetchone()

    if request.method == "POST":
        cur.execute("""
            UPDATE player_game_stats
            SET player_id = ?,
                game_id = ?,
                points = ?,
                assists = ?,
                rebounds = ?,
                minutes_played = ?
            WHERE stat_id = ?
        """, (
            request.form["player_id"],
            request.form["game_id"],
            request.form["points"],
            request.form["assists"],
            request.form["rebounds"],
            request.form["minutes_played"],
            sid
        ))

        con.commit()
        return redirect("/statistics")

    return render_template(
        "statistics_form.html", 
        title="Edit Statistic", 
        statistic=statistic,         
        players=players, 
        games=games
    )

# -------- DELETE STATISTIC --------
@app.route("/statistics/delete/<int:sid>")
def delete_statistic(sid):
    con = sqlite3.connect("nba.db")
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()

    try:
        cur.execute("DELETE FROM player_game_stats WHERE stat_id=?", (sid,))
        con.commit()
    except Exception as e:
        print("Delete error:", e)

    return redirect("/statistics")

# -------- RUN APP --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)