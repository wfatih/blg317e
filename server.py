from datetime import datetime
import sqlite3

from flask import Flask, render_template, request, redirect, url_for
from routes.players_routes import players_bp
from routes.games_routes import games_bp
from routes.teams_routes import teams_bp

app = Flask(__name__)

app.register_blueprint(players_bp)
app.register_blueprint(games_bp)
app.register_blueprint(teams_bp)

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
    return render_template("arenas/list.html", arenas=arenas, teams=teams)

@app.route("/arenas/<int:id>")
def arena_detail(id):
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    # Get Arena Details with Team Name
    query = """
        SELECT s.*, t.team_name, t.nickname
        FROM stadiums s 
        LEFT JOIN teams t ON s.team_id = t.team_id
        WHERE s.stadium_id = ?
    """
    arena = cur.execute(query, (id,)).fetchone()

    stats = {}
    if arena and arena["team_id"]:
        team_id = arena["team_id"]
        
        # 1. Total Games Hosted
        total_games = cur.execute(
            "SELECT COUNT(*) FROM games WHERE home_team_id = ?", 
            (team_id,)
        ).fetchone()[0]

        # 2. Avg Total Score (Home + Away)
        avg_score = cur.execute(
            "SELECT AVG(home_team_score + away_team_score) FROM games WHERE home_team_id = ?", 
            (team_id,)
        ).fetchone()[0]

        # 3. Highest Score (Home + Away) with Breakdown
        max_score_row = cur.execute(
            "SELECT home_team_score, away_team_score FROM games WHERE home_team_id = ? ORDER BY (home_team_score + away_team_score) DESC LIMIT 1", 
            (team_id,)
        ).fetchone()
        
        if max_score_row:
            max_score_val = max_score_row[0] + max_score_row[1]
            max_score_display = f"{max_score_val} ({max_score_row[0]}-{max_score_row[1]})"
        else:
            max_score_display = "N/A"

        # 4. Home Win Rate
        home_wr_val = cur.execute("""
            SELECT AVG(CASE WHEN home_team_wins = 1 THEN 1.0 ELSE 0.0 END) 
            FROM games WHERE home_team_id = ?
        """, (team_id,)).fetchone()[0]
        
        win_rate = round(home_wr_val * 100, 1) if home_wr_val is not None else 0

        # 5. Home Advantage (Home WR - Away WR)
        away_wr_val = cur.execute("""
            SELECT AVG(CASE WHEN home_team_wins = 0 THEN 1.0 ELSE 0.0 END) 
            FROM games WHERE away_team_id = ?
        """, (team_id,)).fetchone()[0]
        
        if home_wr_val is not None and away_wr_val is not None:
            home_adv_val = (home_wr_val - away_wr_val) * 100
            home_advantage = f"{'+' if home_adv_val > 0 else ''}{round(home_adv_val, 1)}%"
        else:
            home_advantage = "N/A"

        # 6. Home Field Accuracy (FG%)
        home_fg = cur.execute(
            "SELECT AVG(fg_pct_home) FROM games WHERE home_team_id = ?", 
            (team_id,)
        ).fetchone()[0]
        home_accuracy = f"{round(home_fg * 100, 1)}%" if home_fg else "N/A"

        # 7. Thrilling Finishes (Margin <= 5, ordered by total score)
        thrillers = cur.execute("""
            SELECT 
                g.game_date,
                g.home_team_score,
                g.away_team_score,
                t.team_name as opponent,
                g.home_team_wins,
                ABS(g.home_team_score - g.away_team_score) as margin
            FROM games g
            JOIN teams t ON g.away_team_id = t.team_id
            WHERE g.home_team_id = ? 
              AND ABS(g.home_team_score - g.away_team_score) <= 5
            ORDER BY (g.home_team_score + g.away_team_score) DESC
            LIMIT 5
        """, (team_id,)).fetchall()
        
        # Convert row objects to dicts for easier use
        close_games = []
        for row in thrillers:
            close_games.append({
                "date": row["game_date"],
                "score_display": f"{row['home_team_score']}-{row['away_team_score']}",
                "opponent": row["opponent"],
                "result": "Win" if row["home_team_wins"] else "Loss",
                "margin": row["margin"]
            })

        # 8. Hall of Fame Performances (Smart List: TD -> DD)
        best_performances = []
        limit = 5
        
        # 8. Hall of Fame Performances (Smart List: TD -> DD)
        best_performances = []
        limit = 5
        
        # QUERY A: Triple Doubles (Points desc)
        td_query = """
            SELECT 
                p.player_id, 
                p.full_name as player_name, 
                CAST(pgs.points as INTEGER) as pts, 
                CAST(pgs.rebounds as INTEGER) as reb, 
                CAST(pgs.assists as INTEGER) as ast, 
                g.game_id,
                g.game_date, 
                'TD' as type
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.player_id
            JOIN games g ON pgs.game_id = g.game_id
            WHERE g.home_team_id = ?
              AND (
                  (CAST(pgs.points as INTEGER) >= 10 AND CAST(pgs.rebounds as INTEGER) >= 10 AND CAST(pgs.assists as INTEGER) >= 10)
              )
            ORDER BY pts DESC
            LIMIT ?
        """
        triple_doubles = cur.execute(td_query, (team_id, limit)).fetchall()
        
        for row in triple_doubles:
            best_performances.append(dict(row))
            
        # If we need more to fill top 5, get Double Doubles
        slots_remaining = limit - len(best_performances)
        
        if slots_remaining > 0:
            # QUERY B: Double Doubles (Points desc)
            dd_query = """
                SELECT 
                    p.player_id, 
                    p.full_name as player_name, 
                    CAST(pgs.points as INTEGER) as pts, 
                    CAST(pgs.rebounds as INTEGER) as reb, 
                    CAST(pgs.assists as INTEGER) as ast, 
                    g.game_id,
                    g.game_date, 
                    'DD' as type
                FROM player_game_stats pgs
                JOIN players p ON pgs.player_id = p.player_id
                JOIN games g ON pgs.game_id = g.game_id
                WHERE g.home_team_id = ?
                  AND (
                      (CAST(pgs.points as INTEGER) >= 10 AND CAST(pgs.rebounds as INTEGER) >= 10 AND CAST(pgs.assists as INTEGER) < 10) OR
                      (CAST(pgs.points as INTEGER) >= 10 AND CAST(pgs.assists as INTEGER) >= 10 AND CAST(pgs.rebounds as INTEGER) < 10) OR
                      (CAST(pgs.rebounds as INTEGER) >= 10 AND CAST(pgs.assists as INTEGER) >= 10 AND CAST(pgs.points as INTEGER) < 10)
                  )
                ORDER BY pts DESC
                LIMIT ?
            """
            double_doubles = cur.execute(dd_query, (team_id, slots_remaining)).fetchall()
            
            for row in double_doubles:
                best_performances.append(dict(row))

        stats = {
            "total_games": total_games or 0,
            "avg_score": round(avg_score, 1) if avg_score else 0,
            "max_score": max_score_display,
            "win_rate": win_rate,
            "home_advantage": home_advantage,
            "home_accuracy": home_accuracy,
            "close_games": close_games,
            "best_performances": best_performances
        }

    con.close()
    
    if not arena:
        return "Arena not found", 404
        
    return render_template("arenas/detail.html", arena=arena, stats=stats)

@app.route("/arenas/add", methods=["POST"])
def add_arena():
    stadium_name = request.form.get("stadium_name")
    city = request.form.get("city")
    capacity = request.form.get("capacity")
    team_id = request.form.get("team_id")
    image_url = request.form.get("image_url")  # New field

    if not team_id:
        team_id = None

    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    query = "INSERT INTO stadiums (stadium_name, city, capacity, team_id, image_url) VALUES (?, ?, ?, ?, ?)"
    cur.execute(query, (stadium_name, city, capacity, team_id, image_url))
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
    image_url = request.form.get("image_url")  # New field

    if not team_id:
        team_id = None

    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    query = """
        UPDATE stadiums 
        SET stadium_name=?, city=?, capacity=?, team_id=?, image_url=? 
        WHERE stadium_id=?
    """
    cur.execute(query, (stadium_name, city, capacity, team_id, image_url, id))
    con.commit()
    con.close()
    return redirect(url_for("arenas_page"))


# -------- ABOUT PROJECT PAGE --------
@app.route("/about")
def about_page():
    return render_template("about.html")



# -------- PLAYERS LIST --------
@app.route("/players")
def players_page():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # GET parameters
    team = request.args.get("team", "").strip()
    name = request.args.get("name", "").strip()

    # Base query
    query = """
        SELECT p.*, t.team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE 1 = 1
    """
    params = []

    # Name filter
    if name:
        query += " AND p.full_name LIKE ?"
        params.append("%" + name + "%")

    # Team filter
    if team:
        query += " AND t.team_name = ?"
        params.append(team)

    query += " ORDER BY p.player_id"

    players = cur.execute(query, params).fetchall()

    # For dropdown list
    all_teams = cur.execute("SELECT team_name FROM teams ORDER BY team_name").fetchall()

    return render_template("players_list.html",
                           players=players,
                           teams=all_teams)




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


# -------- STATISTICS LIST --------
@app.route("/statistics")
def statistics_page():
    with sqlite3.connect("nba.db") as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page

        total = cur.execute("SELECT COUNT(*) FROM player_game_stats").fetchone()[0]
        total_pages = (total + per_page - 1) // per_page

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
    with sqlite3.connect("nba.db") as con:
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
    with sqlite3.connect("nba.db") as con:
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
    with sqlite3.connect("nba.db") as con:
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