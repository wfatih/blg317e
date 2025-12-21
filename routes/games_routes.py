from flask import Flask, render_template, request, redirect, url_for, session, Blueprint
import sqlite3

games_bp = Blueprint("games_bp", __name__, template_folder="../templates/games")


def db():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    return con


# ----------------- GAMES LIST -----------------
@games_bp.route("/games")
def games_list():
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = db()
    cur = con.cursor()

    game_id = request.args.get("game_id", "").strip()
    season = request.args.get("season", "").strip()
    team_id = request.args.get("team", "").strip()
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



    if team_id:
        query += " AND (g.home_team_id = ? OR g.away_team_id = ?)"
        params.append(team_id)
        params.append(team_id)


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
    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()

    con.close()

    return render_template(
        "games_list.html",
        games=games,
        teams=teams,
        total_games=total_games,
        total_pages=total_pages,
        page=page
    )




# ----------------- ADD GAME -----------------
@games_bp.route("/games/add", methods=["GET", "POST"])
def add_game():
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = db()
    cur = con.cursor()

    teams = cur.execute("SELECT * FROM teams ORDER BY team_name").fetchall()
    stadiums = cur.execute("SELECT * FROM stadiums ORDER BY stadium_name").fetchall()

    if request.method == "POST":

        # Get next game_id automatically
        max_id = cur.execute("SELECT MAX(game_id) FROM games").fetchone()[0]
        next_game_id = (max_id + 1) if max_id else 1

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
            next_game_id,  # Auto-generated ID
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
        con.close()
        return redirect("/games")

    con.close()
    empty_game = {}
    return render_template("games_form.html", title="Add Game", game=empty_game, teams=teams, stadiums=stadiums)


# ----------------- EDIT GAME -----------------
@games_bp.route("/games/edit/<int:gid>", methods=["GET", "POST"])
def edit_game(gid):
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = db()
    cur = con.cursor()

    game = cur.execute("SELECT * FROM games WHERE game_id=?", (gid,)).fetchone()
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
            UPDATE games SET
                home_team_id=?, away_team_id=?, stadium_id=?,
                game_date=?, season=?, arena_name=?,
                home_team_score=?, away_team_score=?,
                fg_pct_home=?, fg_pct_away=?, ft_pct_home=?, ft_pct_away=?,
                fg3_pct_home=?, fg3_pct_away=?,
                ast_home=?, ast_away=?, reb_home=?, reb_away=?,
                home_team_wins=?
            WHERE game_id=?
        """, (
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

            winner,
            gid
        ))

        con.commit()
        con.close()
        return redirect("/games")

    con.close()
    return render_template("games_form.html", title="Edit Game", game=game, teams=teams, stadiums=stadiums)


# ----------------- DELETE GAME -----------------
@games_bp.route("/games/delete/<int:gid>")
def delete_game(gid):
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = db()
    cur = con.cursor()

    cur.execute("DELETE FROM games WHERE game_id=?", (gid,))
    con.commit()
    con.close()

    return redirect("/games")

# ----------------- ENHANCED GAME DETAIL -----------------
@games_bp.route("/games/<int:gid>")
def game_detail(gid):
    if "logged_in" not in session: return redirect(url_for("login_page"))
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

    # EXISTING QUERIES (keeping your original ones)
    # Home Team Season Stats
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

    # Away Team Season Stats
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

    # ==================================================================
    # NEW COMPLEX QUERY 1: SEASON COMPARISON WITH 4+ TABLE JOIN + GROUP BY
    # ==================================================================
    # This query joins games, teams, stadiums, and aggregates stadium performance
    season_comparison = cur.execute("""
        SELECT 
            t.team_id,
            t.team_name,
            t.city,
            COUNT(DISTINCT g.game_id) as games_played,
            SUM(CASE 
                WHEN (g.home_team_id = t.team_id AND g.home_team_wins = 1) 
                  OR (g.away_team_id = t.team_id AND g.home_team_wins = 0) 
                THEN 1 ELSE 0 
            END) as total_wins,
            ROUND(AVG(CASE 
                WHEN g.home_team_id = t.team_id THEN g.home_team_score 
                ELSE g.away_team_score 
            END), 1) as avg_points_scored,
            ROUND(AVG(CASE 
                WHEN g.home_team_id = t.team_id THEN g.away_team_score 
                ELSE g.home_team_score 
            END), 1) as avg_points_allowed,
            COUNT(DISTINCT g.stadium_id) as stadiums_played,
            COUNT(DISTINCT CASE WHEN g.home_team_id = t.team_id THEN g.game_id END) as home_games,
            COUNT(DISTINCT CASE WHEN g.away_team_id = t.team_id THEN g.game_id END) as away_games
        FROM teams t
        INNER JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
        WHERE t.team_id IN (?, ?)
          AND g.season = ?
          AND g.game_date < ?
        GROUP BY t.team_id, t.team_name, t.city
        ORDER BY total_wins DESC
    """, (game_dict['home_team_id'], game_dict['away_team_id'], 
          game_dict['season'], game_dict['game_date'])).fetchall()
    
    game_dict['season_comparison'] = [dict(row) for row in season_comparison]

    # ==================================================================
    # NEW COMPLEX QUERY 2: STADIUM PERFORMANCE WITH OUTER JOIN + NESTED QUERY
    # ==================================================================
    # Left outer join to include all stadiums even if no games played
    # Nested subquery to calculate average performance
    stadium_performance = cur.execute("""
        SELECT 
            s.stadium_id,
            s.stadium_name,
            s.city as stadium_city,
            s.capacity,
            COALESCE(games_count.total_games, 0) as games_hosted,
            COALESCE(games_count.avg_total_score, 0) as avg_total_score,
            COALESCE(games_count.avg_home_win_margin, 0) as avg_home_advantage,
            CASE 
                WHEN games_count.total_games > 0 
                THEN ROUND((games_count.home_wins * 100.0 / games_count.total_games), 1)
                ELSE 0 
            END as home_win_percentage
        FROM stadiums s
        LEFT OUTER JOIN (
            SELECT 
                stadium_id,
                COUNT(*) as total_games,
                ROUND(AVG(home_team_score + away_team_score), 1) as avg_total_score,
                ROUND(AVG(home_team_score - away_team_score), 1) as avg_home_win_margin,
                SUM(CASE WHEN home_team_wins = 1 THEN 1 ELSE 0 END) as home_wins
            FROM games
            WHERE season = ?
              AND game_date <= ?
            GROUP BY stadium_id
        ) as games_count ON s.stadium_id = games_count.stadium_id
        WHERE s.stadium_id IN (
            SELECT DISTINCT stadium_id 
            FROM games 
            WHERE (home_team_id = ? OR away_team_id = ?)
              AND season = ?
              AND stadium_id IS NOT NULL
        )
        ORDER BY games_hosted DESC
        LIMIT 10
    """, (game_dict['season'], game_dict['game_date'],
          game_dict['home_team_id'], game_dict['away_team_id'],
          game_dict['season'])).fetchall()
    
    game_dict['stadium_performance'] = [dict(row) for row in stadium_performance]

    # ==================================================================
    # NEW COMPLEX QUERY 3: ADVANCED TEAM ANALYTICS WITH NESTED SUBQUERIES
    # ==================================================================
    # Nested queries to compare home vs away performance
    advanced_analytics = cur.execute("""
        SELECT 
            t.team_id,
            t.team_name,
            home_stats.home_games,
            home_stats.home_wins,
            home_stats.home_avg_score,
            away_stats.away_games,
            away_stats.away_wins,
            away_stats.away_avg_score,
            ROUND(
                (home_stats.home_avg_score - away_stats.away_avg_score), 1
            ) as home_away_differential
        FROM teams t
        LEFT JOIN (
            SELECT 
                home_team_id as team_id,
                COUNT(*) as home_games,
                SUM(CASE WHEN home_team_wins = 1 THEN 1 ELSE 0 END) as home_wins,
                ROUND(AVG(home_team_score), 1) as home_avg_score
            FROM games
            WHERE season = ? AND game_date < ?
            GROUP BY home_team_id
        ) as home_stats ON t.team_id = home_stats.team_id
        LEFT JOIN (
            SELECT 
                away_team_id as team_id,
                COUNT(*) as away_games,
                SUM(CASE WHEN home_team_wins = 0 THEN 1 ELSE 0 END) as away_wins,
                ROUND(AVG(away_team_score), 1) as away_avg_score
            FROM games
            WHERE season = ? AND game_date < ?
            GROUP BY away_team_id
        ) as away_stats ON t.team_id = away_stats.team_id
        WHERE t.team_id IN (?, ?)
    """, (game_dict['season'], game_dict['game_date'],
          game_dict['season'], game_dict['game_date'],
          game_dict['home_team_id'], game_dict['away_team_id'])).fetchall()
    
    game_dict['advanced_analytics'] = [dict(row) for row in advanced_analytics]

    # ==================================================================
    # NEW COMPLEX QUERY 4: LEAGUE RANKINGS WITH COMPLEX AGGREGATION
    # ==================================================================
    # This shows where both teams rank in the league with complex calculations
    league_rankings = cur.execute("""
        SELECT 
            team_id,
            team_name,
            total_wins,
            total_games,
            win_percentage,
            avg_margin,
            RANK() OVER (ORDER BY win_percentage DESC) as league_rank
        FROM (
            SELECT 
                t.team_id,
                t.team_name,
                COUNT(g.game_id) as total_games,
                SUM(CASE 
                    WHEN (g.home_team_id = t.team_id AND g.home_team_wins = 1) 
                      OR (g.away_team_id = t.team_id AND g.home_team_wins = 0) 
                    THEN 1 ELSE 0 
                END) as total_wins,
                ROUND(
                    SUM(CASE 
                        WHEN (g.home_team_id = t.team_id AND g.home_team_wins = 1) 
                          OR (g.away_team_id = t.team_id AND g.home_team_wins = 0) 
                        THEN 1 ELSE 0 
                    END) * 100.0 / COUNT(g.game_id), 1
                ) as win_percentage,
                ROUND(AVG(
                    CASE 
                        WHEN g.home_team_id = t.team_id 
                        THEN g.home_team_score - g.away_team_score
                        ELSE g.away_team_score - g.home_team_score
                    END
                ), 1) as avg_margin
            FROM teams t
            INNER JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
            WHERE g.season = ? AND g.game_date < ?
            GROUP BY t.team_id, t.team_name
            HAVING COUNT(g.game_id) >= 5
        ) as team_stats
        WHERE team_id IN (?, ?)
        ORDER BY win_percentage DESC
    """, (game_dict['season'], game_dict['game_date'],
          game_dict['home_team_id'], game_dict['away_team_id'])).fetchall()
    
    game_dict['league_rankings'] = [dict(row) for row in league_rankings]

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


    return redirect("/games")