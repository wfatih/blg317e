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


# -------- PLAYERS PAGE --------
@app.route("/players")
def players_page():
    return render_template("players.html")


# -------- GAMES PAGE --------
@app.route("/games")
def games_page():
    return render_template("games.html")


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


# -------- RUN APP --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

@app.route("/games")
def games_list():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    query = """
        SELECT g.*, 
               t1.team_name AS home_team_name,
               t2.team_name AS away_team_name,
               s.stadium_name AS stadium_name
        FROM Games g
        JOIN Teams t1 ON g.home_team_id = t1.team_id
        JOIN Teams t2 ON g.away_team_id = t2.team_id
        JOIN Stadiums s ON g.stadium_id = s.stadium_id
    """

    games = cur.execute(query).fetchall()
    con.close()

    return render_template("game_list.html", games=games)

@app.route("/games/add", methods=["GET", "POST"])
def add_game():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    teams = cur.execute("SELECT * FROM Teams").fetchall()
    stadiums = cur.execute("SELECT * FROM Stadiums").fetchall()

    if request.method == "POST":
        cur.execute("""
            INSERT INTO Games (home_team_id, away_team_id, stadium_id, game_date, season, arena_name)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            request.form["home_team_id"],
            request.form["away_team_id"],
            request.form["stadium_id"],
            request.form["game_date"],
            request.form["season"],
            request.form["arena_name"]
        ))

        con.commit()
        con.close()
        return redirect("/games")

    empty_game = {"home_team_id": None, "away_team_id": None, "stadium_id": None, "game_date": "", "season": "", "arena_name": ""}

    return render_template("game_form.html", title="Add Game", game=empty_game, teams=teams, stadiums=stadiums)

@app.route("/games/edit/<int:game_id>", methods=["GET", "POST"])
def edit_game(game_id):
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    game = cur.execute("SELECT * FROM Games WHERE game_id = ?", (game_id,)).fetchone()
    teams = cur.execute("SELECT * FROM Teams").fetchall()
    stadiums = cur.execute("SELECT * FROM Stadiums").fetchall()

    if request.method == "POST":
        cur.execute("""
            UPDATE Games
            SET home_team_id=?, away_team_id=?, stadium_id=?, game_date=?, season=?, arena_name=?
            WHERE game_id=?
        """, (
            request.form["home_team_id"],
            request.form["away_team_id"],
            request.form["stadium_id"],
            request.form["game_date"],
            request.form["season"],
            request.form["arena_name"],
            game_id
        ))

        con.commit()
        con.close()
        return redirect("/games")

    return render_template("game_form.html", title="Edit Game", game=game, teams=teams, stadiums=stadiums)

@app.route("/games/delete/<int:game_id>")
def delete_game(game_id):
    con = sqlite3.connect("nba.db")
    cur = con.cursor()

    cur.execute("DELETE FROM Games WHERE game_id=?", (game_id,))

    con.commit()
    con.close()

    return redirect("/games")
