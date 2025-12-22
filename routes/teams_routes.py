from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3

teams_bp = Blueprint("teams_bp", __name__)

def db():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    return con

# ----------------- TEAMS LIST (Filtreleme Aynı Kalıyor) -----------------
@teams_bp.route("/teams")
def teams_list():
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = db()
    cur = con.cursor()

    search = request.args.get("search", "").strip()
    min_year = request.args.get("min_year", "").strip()
    min_capacity = request.args.get("min_capacity", "").strip()
    
    page = request.args.get("page", 1, type=int)
    per_page = 12 
    offset = (page - 1) * per_page

    query = "SELECT * FROM teams WHERE 1=1"
    params = []

    if search:
        query += " AND (nickname LIKE ? OR city LIKE ? OR abbreviation LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard])

    if min_year and min_year.isdigit():
        query += " AND founded_year >= ?"
        params.append(min_year)

    if min_capacity and min_capacity.isdigit():
        query += " AND arenacapacity >= ?"
        params.append(min_capacity)

    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_teams = cur.execute(count_query, params).fetchone()[0]
    total_pages = (total_teams + per_page - 1) // per_page

    query += " ORDER BY city ASC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    teams = cur.execute(query, params).fetchall()
    con.close()

    return render_template(
        "teams/teams_list.html",
        teams=teams,
        total_pages=total_pages,
        page=page,
        total_games=total_teams
    )

# ----------------- TEAM DETAIL (KRİTİK DÜZELTME BURADA) -----------------
@teams_bp.route("/teams/<int:tid>")
def team_detail(tid):
    if "logged_in" not in session: return redirect(url_for("login_page"))
    con = db()
    cur = con.cursor()
    
    # 1. Takım Bilgisi
    team = cur.execute("SELECT * FROM teams WHERE team_id=?", (tid,)).fetchone()
    if not team:
        con.close()
        return "Team not found", 404

    # 2. Dropdown Verileri
    seasons = cur.execute("SELECT DISTINCT season FROM games ORDER BY season DESC").fetchall()
    all_teams = cur.execute("SELECT team_id, team_name FROM teams WHERE team_id != ? ORDER BY team_name", (tid,)).fetchall()

    selected_season = request.args.get("season", "")
    opponent_id = request.args.get("opponent_id", "")

    # 3. KADRO SORGUSU (DÜZELTİLDİ: Sadece o takımın oyuncuları gelecek)
    if selected_season:
        # Mantık: O sezon o takımın maçına çıkmış VE takım ID'si eşleşen oyuncular
        players_query = """
            SELECT DISTINCT p.* FROM players p
            JOIN player_game_stats s ON p.player_id = s.player_id
            JOIN games g ON s.game_id = g.game_id
            WHERE ((g.home_team_id = ? OR g.away_team_id = ?) AND g.season = ?)
            AND p.team_id = ?  -- <--- BU SATIR RAKİPLERİ ENGELLER
            ORDER BY p.full_name ASC
        """
        players = cur.execute(players_query, (tid, tid, selected_season, tid)).fetchall()
    else:
        players = cur.execute("SELECT * FROM players WHERE team_id = ? ORDER BY full_name ASC", (tid,)).fetchall()

    # 4. KARŞILAŞTIRMA (HEAD-TO-HEAD)
    comparison_games = []
    head_to_head_stats = {"wins": 0, "losses": 0, "total": 0}

    if opponent_id and opponent_id.isdigit():
        games_query = """
            SELECT g.*, 
                   t_home.nickname as home_nick,
                   t_away.nickname as away_nick
            FROM games g
            JOIN teams t_home ON g.home_team_id = t_home.team_id
            JOIN teams t_away ON g.away_team_id = t_away.team_id
            WHERE ((g.home_team_id = ? AND g.away_team_id = ?) 
               OR (g.home_team_id = ? AND g.away_team_id = ?))
            ORDER BY g.game_date DESC
        """
        comparison_games = cur.execute(games_query, (tid, opponent_id, opponent_id, tid)).fetchall()
        
        for g in comparison_games:
            head_to_head_stats["total"] += 1
            if (g["home_team_id"] == tid and g["home_team_wins"] == 1) or \
               (g["away_team_id"] == tid and g["home_team_wins"] == 0):
                head_to_head_stats["wins"] += 1
            else:
                head_to_head_stats["losses"] += 1

    top_seasons = cur.execute("""
        SELECT *
        FROM (
            SELECT 
                g.season,
                SUM(
                    CASE 
                        WHEN (g.home_team_id = ? AND g.home_team_wins = 1)
                          OR (g.away_team_id = ? AND g.home_team_wins = 0)
                        THEN 1 ELSE 0
                    END
                ) AS wins
            FROM games g
            WHERE g.home_team_id = ? OR g.away_team_id = ?
            GROUP BY g.season
        ) season_stats
        ORDER BY wins DESC
        LIMIT 3
    """, (tid, tid, tid, tid)).fetchall()

    # 6. HOME vs AWAY PERFORMANCE
    home_away = cur.execute("""
        SELECT
             SUM(
                CASE 
                    WHEN g.home_team_id = ? AND g.home_team_wins = 1 THEN 1
                     ELSE 0
                 END
             ) AS home_wins,
                SUM(
                    CASE 
                        WHEN g.away_team_id = ? AND g.home_team_wins = 0 THEN 1
                         ELSE 0
                END
            ) AS away_wins
        FROM games g
        WHERE g.home_team_id = ? OR g.away_team_id = ?
    """, (tid, tid, tid, tid)).fetchone()

    # 7. AVERAGE POINT DIFFERENTIAL
    avg_point_diff = cur.execute("""
         SELECT
            ROUND(AVG(
                 CASE
                    WHEN home_team_id = ? 
                        THEN home_team_score - away_team_score
                    ELSE away_team_score - home_team_score
                END
            ), 2) AS avg_point_diff
        FROM games
        WHERE home_team_id = ? OR away_team_id = ?
    """, (tid, tid, tid)).fetchone()

    # ARENA ID (stadiums tablosundan)
    arena_row = cur.execute("""
        SELECT stadium_id
        FROM stadiums
        WHERE team_id = ?
    """, (tid,)).fetchone()

    arena_id = arena_row["stadium_id"] if arena_row else None

    con.close()

    return render_template(
        "teams/teams_detail.html", 
        team=team, 
        players=players,
        seasons=seasons,
        all_teams=all_teams,
        selected_season=selected_season,
        opponent_id=int(opponent_id) if opponent_id.isdigit() else None,
        comparison_games=comparison_games,
        stats=head_to_head_stats,
        top_seasons=top_seasons,
        home_away=home_away,
        avg_point_diff=avg_point_diff,
        arena_id=arena_id,
    )

# ----------------- ADD/EDIT/DELETE (AYNI KALIYOR) -----------------
@teams_bp.route("/teams/add", methods=["GET", "POST"])
def add_team():

    if request.method == "POST":
        con = db()
        cur = con.cursor()
        try:
            cur.execute("""
                INSERT INTO teams (
                    team_id, abbreviation, nickname, founded_year, city,
                    arena, arenacapacity, owner, generalmanager, headcoach, dleagueaffiliation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form["team_id"],
                
                request.form["abbreviation"],
                request.form["nickname"],
                request.form.get("founded_year"),
                request.form["city"],
                request.form["arena"],
                request.form.get("arenacapacity") or 0,
                request.form.get("owner"),
                request.form.get("generalmanager"),
                request.form.get("headcoach"),
                request.form.get("dleagueaffiliation")
            ))
            con.commit()
            return redirect("/teams")
        except sqlite3.IntegrityError as e:
            return f"DB Error: {e}"
        finally:
            con.close()

    return render_template("teams/teams_form.html", title="Add Team", team={})


@teams_bp.route("/teams/edit/<int:tid>", methods=["GET", "POST"])
def edit_team(tid):

    con = db()
    cur = con.cursor()

    if request.method == "POST":
        cur.execute("""
            UPDATE teams SET
                
                abbreviation=?,
                nickname=?,
                founded_year=?,
                city=?,
                arena=?,
                arenacapacity=?,
                owner=?,
                generalmanager=?,
                headcoach=?,
                dleagueaffiliation=?
            WHERE team_id=?
        """, (
            
            request.form["abbreviation"],
            request.form["nickname"],
            request.form.get("founded_year"),
            request.form["city"],
            request.form["arena"],
            request.form.get("arenacapacity"),
            request.form.get("owner"),
            request.form.get("generalmanager"),
            request.form.get("headcoach"),
            request.form.get("dleagueaffiliation"),
            tid
        ))
        con.commit()
        con.close()
        return redirect(f"/teams/{tid}")

    team = cur.execute("SELECT * FROM teams WHERE team_id=?", (tid,)).fetchone()
    con.close()
    return render_template("teams/teams_form.html", title="Edit Team", team=team)


@teams_bp.route("/teams/delete/<int:tid>")
def delete_team(tid):
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM teams WHERE team_id=?", (tid,))
    con.commit()
    con.close()
    return redirect("/teams")