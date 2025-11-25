from datetime import datetime
import sqlite3

from flask import Flask, render_template, request, redirect


app = Flask(__name__)

# -------- HOME --------
@app.route("/")
def home_page():
    today = datetime.today()
    day_name = today.strftime("%A")
    return render_template("home.html", date=day_name)


# -------- TEAMS PAGE --------
@app.route("/teams")
def teams_page():
    return render_template("teams.html")


# -------- STATISTICS PAGE --------
@app.route("/statistics")
def statistics_page():
    return render_template("statistics.html")


# -------- ARENAS PAGE --------
@app.route("/arenas")
def arenas_page():
    return render_template("arenas.html")


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


# -------- RUN APP --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)