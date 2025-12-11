from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3

teams_bp = Blueprint("teams_bp", __name__)

def db():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    return con

# ----------------- TEAMS LIST (Filtreleme Aynı Kalıyor) -----------------
@teams_bp.route("/teams")
def teams_list():
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
        stats=head_to_head_stats
    )

# ----------------- ADD/EDIT/DELETE (AYNI KALIYOR) -----------------
@teams_bp.route("/teams/add", methods=["GET", "POST"])
def add_team():
    # ... (Eski kodunun aynısı)
    if request.method == "POST":
        con = db()
        cur = con.cursor()
        try:
            cur.execute("""
                INSERT INTO teams (
                    team_id, abbreviation, nickname, yearfounded, city, 
                    arena, arenacapacity, owner, generalmanager, headcoach, dleagueaffiliation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form["team_id"], request.form["abbreviation"], request.form["nickname"],
                request.form["yearfounded"], request.form["city"], request.form["arena"],
                request.form["arenacapacity"] or 0, request.form["owner"], request.form["generalmanager"],
                request.form["headcoach"], request.form["dleagueaffiliation"]
            ))
            con.commit()
            return redirect("/teams")
        except sqlite3.IntegrityError:
            return "Error: Team ID already exists!"
        finally:
            con.close()
    return render_template("teams/teams_form.html", title="Add Team", team={})

@teams_bp.route("/teams/edit/<int:tid>", methods=["GET", "POST"])
def edit_team(tid):
    # ... (Eski kodunun aynısı)
    con = db()
    cur = con.cursor()
    if request.method == "POST":
        cur.execute("""
            UPDATE teams SET
                abbreviation=?, nickname=?, yearfounded=?, city=?, 
                arena=?, arenacapacity=?, owner=?, generalmanager=?, 
                headcoach=?, dleagueaffiliation=?
            WHERE team_id=?
        """, (
            request.form["abbreviation"], request.form["nickname"], request.form["yearfounded"],
            request.form["city"], request.form["arena"], request.form["arenacapacity"],
            request.form["owner"], request.form["generalmanager"], request.form["headcoach"],
            request.form["dleagueaffiliation"], tid
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