from datetime import datetime
from flask import Flask, render_template

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
