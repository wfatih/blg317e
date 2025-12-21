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

    game_id = request.args.get("game_id", "").strip()
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

    if game_id:
        query += " AND g.game_id LIKE ?"
        params.append(f"%{game_id}%")

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

    # Main game query with team info
    game = cur.execute("""
        SELECT 
            g.*,
            ht.team_name AS home_team,
            at.team_name AS away_team,
            ht.city AS home_city,
            at.city AS away_city,
            ht.arena AS home_arena
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams at ON g.away_team_id = at.team_id
        WHERE g.game_id = ?
    """, (gid,)).fetchone()

    if not game:
        con.close()
        return "Game not found", 404

    game_dict = dict(game)
    
    # Format date
    if game_dict.get('game_date'):
        from datetime import datetime
        try:
            date_obj = datetime.strptime(game_dict['game_date'], '%Y-%m-%d')
            game_dict['date'] = date_obj
        except:
            game_dict['date'] = None
    else:
        game_dict['date'] = None

    # SUBQUERY 1: Home Team Season Stats
    home_stats = cur.execute("""
        SELECT 
            COUNT(*) as total_games,
            SUM(CASE 
                WHEN (home_team_id = ? AND home_team_wins = 1) 
                  OR (away_team_id = ? AND home_team_wins = 0) 
                THEN 1 ELSE 0 
            END) as wins,
            ROUND(AVG(CASE 
                WHEN home_team_id = ? THEN home_team_score 
                ELSE away_team_score 
            END), 1) as avg_score
        FROM games 
        WHERE season = ? 
          AND (home_team_id = ? OR away_team_id = ?)
          AND game_date < ?
    """, (game_dict['home_team_id'], game_dict['home_team_id'], 
          game_dict['home_team_id'], game_dict['season'],
          game_dict['home_team_id'], game_dict['home_team_id'],
          game_dict['game_date'])).fetchone()
    
    game_dict['home_season_stats'] = dict(home_stats) if home_stats else {}

    # SUBQUERY 2: Away Team Season Stats
    away_stats = cur.execute("""
        SELECT 
            COUNT(*) as total_games,
            SUM(CASE 
                WHEN (home_team_id = ? AND home_team_wins = 1) 
                  OR (away_team_id = ? AND home_team_wins = 0) 
                THEN 1 ELSE 0 
            END) as wins,
            ROUND(AVG(CASE 
                WHEN home_team_id = ? THEN home_team_score 
                ELSE away_team_score 
            END), 1) as avg_score
        FROM games 
        WHERE season = ? 
          AND (home_team_id = ? OR away_team_id = ?)
          AND game_date < ?
    """, (game_dict['away_team_id'], game_dict['away_team_id'],
          game_dict['away_team_id'], game_dict['season'],
          game_dict['away_team_id'], game_dict['away_team_id'],
          game_dict['game_date'])).fetchone()
    
    game_dict['away_season_stats'] = dict(away_stats) if away_stats else {}

    # SUBQUERY 3: Head to Head History
    h2h_games = cur.execute("""
        SELECT 
            game_date,
            home_team_score,
            away_team_score,
            home_team_wins,
            CASE WHEN home_team_id = ? THEN 1 ELSE 0 END as is_team1_home
        FROM games
        WHERE ((home_team_id = ? AND away_team_id = ?) 
            OR (home_team_id = ? AND away_team_id = ?))
          AND game_date < ?
        ORDER BY game_date DESC 
        LIMIT 5
    """, (game_dict['home_team_id'], 
          game_dict['home_team_id'], game_dict['away_team_id'],
          game_dict['away_team_id'], game_dict['home_team_id'],
          game_dict['game_date'])).fetchall()
    
    game_dict['h2h_history'] = [dict(g) for g in h2h_games]

    # SUBQUERY 4: Home Team Recent Form (Last 5 games)
    home_form = cur.execute("""
        SELECT 
            game_date,
            CASE WHEN home_team_id = ? THEN home_team_score ELSE away_team_score END as team_score,
            CASE WHEN home_team_id = ? THEN away_team_score ELSE home_team_score END as opponent_score,
            CASE 
                WHEN (home_team_id = ? AND home_team_wins = 1) 
                  OR (away_team_id = ? AND home_team_wins = 0) 
                THEN 'W' ELSE 'L' 
            END as result
        FROM games
        WHERE (home_team_id = ? OR away_team_id = ?)
          AND game_date < ?
        ORDER BY game_date DESC 
        LIMIT 5
    """, (game_dict['home_team_id'], game_dict['home_team_id'],
          game_dict['home_team_id'], game_dict['home_team_id'],
          game_dict['home_team_id'], game_dict['home_team_id'],
          game_dict['game_date'])).fetchall()
    
    game_dict['home_form'] = [dict(g) for g in home_form]

    # SUBQUERY 5: Away Team Recent Form (Last 5 games)
    away_form = cur.execute("""
        SELECT 
            game_date,
            CASE WHEN home_team_id = ? THEN home_team_score ELSE away_team_score END as team_score,
            CASE WHEN home_team_id = ? THEN away_team_score ELSE home_team_score END as opponent_score,
            CASE 
                WHEN (home_team_id = ? AND home_team_wins = 1) 
                  OR (away_team_id = ? AND home_team_wins = 0) 
                THEN 'W' ELSE 'L' 
            END as result
        FROM games
        WHERE (home_team_id = ? OR away_team_id = ?)
          AND game_date < ?
        ORDER BY game_date DESC 
        LIMIT 5
    """, (game_dict['away_team_id'], game_dict['away_team_id'],
          game_dict['away_team_id'], game_dict['away_team_id'],
          game_dict['away_team_id'], game_dict['away_team_id'],
          game_dict['game_date'])).fetchall()
    
    game_dict['away_form'] = [dict(g) for g in away_form]

    # SUBQUERY 6: Arena Statistics
    if game_dict.get('arena_name'):
        arena_stats = cur.execute("""
            SELECT 
                COUNT(*) as games_played,
                ROUND(AVG(home_team_score + away_team_score), 1) as avg_total_score,
                MAX(home_team_score + away_team_score) as highest_score
            FROM games
            WHERE arena_name = ?
              AND game_date < ?
        """, (game_dict['arena_name'], game_dict['game_date'])).fetchone()
        
        game_dict['arena_stats'] = dict(arena_stats) if arena_stats else {}

    # Set venue
    game_dict['venue'] = game_dict.get('arena_name') or game_dict.get('home_arena') or 'Not specified'
    
    # Set scores
    game_dict['home_score'] = game_dict.get('home_team_score')
    game_dict['away_score'] = game_dict.get('away_team_score')
    game_dict['id'] = gid

    # Calculate win percentages
    if game_dict['home_season_stats'].get('total_games', 0) > 0:
        game_dict['home_win_pct'] = round(
            (game_dict['home_season_stats']['wins'] / game_dict['home_season_stats']['total_games']) * 100, 1
        )
    else:
        game_dict['home_win_pct'] = 0

    if game_dict['away_season_stats'].get('total_games', 0) > 0:
        game_dict['away_win_pct'] = round(
            (game_dict['away_season_stats']['wins'] / game_dict['away_season_stats']['total_games']) * 100, 1
        )
    else:
        game_dict['away_win_pct'] = 0

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