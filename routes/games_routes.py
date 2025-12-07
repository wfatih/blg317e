from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

games_bp = Blueprint("games_bp", __name__, template_folder="../templates/games")


def db():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    return con


# ----------------- GAMES LIST -----------------
@games_bp.route("/games")
def games_list():

    con = db()
    cur = con.cursor()

    season = request.args.get("season", "").strip()
    team = request.args.get("team", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    query = """
        SELECT 
            g.*, 
            t1.team_name AS home_team,
            t2.team_name AS away_team
        FROM games g
        JOIN teams t1 ON g.home_team_id = t1.team_id
        JOIN teams t2 ON g.away_team_id = t2.team_id
        WHERE 1=1
    """

    params = []

    if season:
        query += " AND g.season LIKE ?"
        params.append(f"%{season}%")

    if team:
        query += " AND (t1.team_name LIKE ? OR t2.team_name LIKE ?)"
        params.append(f"%{team}%")
        params.append(f"%{team}%")

    if date_from:
        query += " AND g.game_date >= ?"
        params.append(date_from)

    if date_to:
        query += " AND g.game_date <= ?"
        params.append(date_to)

    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_games = cur.execute(count_query, params).fetchone()[0]

    total_pages = (total_games + per_page - 1) // per_page

    query += " ORDER BY g.game_date DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    games = cur.execute(query, params).fetchall()

    con.close()

    return render_template(
        "games_list.html",
        games=games,
        total_games=total_games,
        total_pages=total_pages,
        page=page
    )


# ----------------- GAME DETAIL -----------------
@games_bp.route("/games/<int:gid>")
def game_detail(gid):
    
    con = db()
    cur = con.cursor()

    # Get game with team names (location kaldırıldı)
    game = cur.execute("""
        SELECT 
            g.*,
            t1.team_name AS home_team,
            t2.team_name AS away_team,
            s.stadium_name
        FROM games g
        JOIN teams t1 ON g.home_team_id = t1.team_id
        JOIN teams t2 ON g.away_team_id = t2.team_id
        LEFT JOIN stadiums s ON g.stadium_id = s.stadium_id
        WHERE g.game_id = ?
    """, (gid,)).fetchone()

    if not game:
        con.close()
        return "Game not found", 404

    # Convert to dict
    game_dict = dict(game)
    
    # Add formatted date
    if game_dict.get('game_date'):
        from datetime import datetime
        try:
            date_obj = datetime.strptime(game_dict['game_date'], '%Y-%m-%d')
            game_dict['date'] = date_obj
        except:
            game_dict['date'] = None
    else:
        game_dict['date'] = None

    # Set venue (sadece stadium_name veya arena_name)
    game_dict['venue'] = game_dict.get('stadium_name') or game_dict.get('arena_name') or 'Not specified'
    
    # Set scores
    game_dict['home_score'] = game_dict.get('home_team_score')
    game_dict['away_score'] = game_dict.get('away_team_score')
    
    # Set ID
    game_dict['id'] = gid

    con.close()

    # Create object for template
    class GameObj:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
    
    game_obj = GameObj(game_dict)

    return render_template("games_detail.html", game=game_obj)


# ----------------- ADD GAME -----------------
@games_bp.route("/games/add", methods=["GET", "POST"])
def add_game():

    con = db()
    cur = con.cursor()

    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()
    stadiums = cur.execute("SELECT * FROM stadiums ORDER BY stadium_name").fetchall()

    if request.method == "POST":

        home_score = request.form.get("home_team_score")
        away_score = request.form.get("away_team_score")

        if home_score and away_score:
            winner = 1 if int(home_score) > int(away_score) else 0
        else:
            winner = None

        cur.execute("""
            INSERT INTO games (
                game_id, home_team_id, away_team_id, stadium_id,
                game_date, season, arena_name,
                home_team_score, away_team_score,
                fg_pct_home, fg_pct_away, ft_pct_home, ft_pct_away,
                fg3_pct_home, fg3_pct_away, ast_home, ast_away,
                reb_home, reb_away, home_team_wins
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["game_id"],
            request.form["home_team_id"],
            request.form["away_team_id"],
            request.form["stadium_id"] or None,

            request.form["game_date"],
            request.form["season"],
            request.form["arena_name"],

            home_score or None,
            away_score or None,

            request.form["fg_pct_home"] or None,
            request.form["fg_pct_away"] or None,
            request.form["ft_pct_home"] or None,
            request.form["ft_pct_away"] or None,
            request.form["fg3_pct_home"] or None,
            request.form["fg3_pct_away"] or None,
            request.form["ast_home"] or None,
            request.form["ast_away"] or None,
            request.form["reb_home"] or None,
            request.form["reb_away"] or None,

            winner
        ))

        con.commit()
        return redirect("/games")

    empty_game = {}
    return render_template("games_form.html", title="Add Game", game=empty_game, teams=teams, stadiums=stadiums)


# ----------------- EDIT GAME -----------------
@games_bp.route("/games/edit/<int:gid>", methods=["GET", "POST"])
def edit_game(gid):

    con = db()
    cur = con.cursor()

    game = cur.execute("SELECT * FROM games WHERE game_id=?", (gid,)).fetchone()
    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()
    stadiums = cur.execute("SELECT * FROM stadiums ORDER BY stadium_name").fetchall()

    if request.method == "POST":

        cur.execute("""
            UPDATE games SET
                home_team_id=?, away_team_id=?, stadium_id=?,
                game_date=?, season=?, arena_name=?,
                home_team_score=?, away_team_score=?,
                fg_pct_home=?, fg_pct_away=?, ft_pct_home=?, ft_pct_away=?,
                fg3_pct_home=?, fg3_pct_away=?,
                ast_home=?, ast_away=?, reb_home=?, reb_away=?
            WHERE game_id=?
        """, (
            request.form["home_team_id"],
            request.form["away_team_id"],
            request.form["stadium_id"] or None,

            request.form["game_date"],
            request.form["season"],
            request.form["arena_name"],

            request.form["home_team_score"] or None,
            request.form["away_team_score"] or None,

            request.form["fg_pct_home"] or None,
            request.form["fg_pct_away"] or None,
            request.form["ft_pct_home"] or None,
            request.form["ft_pct_away"] or None,
            request.form["fg3_pct_home"] or None,
            request.form["fg3_pct_away"] or None,
            request.form["ast_home"] or None,
            request.form["ast_away"] or None,
            request.form["reb_home"] or None,
            request.form["reb_away"] or None,

            gid
        ))

        con.commit()
        return redirect("/games")

    return render_template("games_form.html", title="Edit Game", game=game, teams=teams, stadiums=stadiums)


# ----------------- DELETE GAME -----------------
@games_bp.route("/games/delete/<int:gid>")
def delete_game(gid):

    con = db()
    cur = con.cursor()

    cur.execute("DELETE FROM games WHERE game_id=?", (gid,))
    con.commit()

    return redirect("/games")