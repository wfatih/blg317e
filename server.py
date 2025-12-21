from datetime import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import check_password_hash

# Eğer blueprint dosyaların varsa bunları tutabilirsin,
# ancak aşağıdaki kodlar ana dosyada tanımlı olduğu için çakışma olmaması adına
# blueprint rotalarının bu dosyadaki rotalarla aynı URL'yi kullanmadığından emin ol.
from routes.players_routes import players_bp
from routes.games_routes import games_bp
from routes.teams_routes import teams_bp

app = Flask(__name__)

# --- AYARLAR ---
# Session güvenliği için rastgele bir anahtar. Bunu canlı ortamda gizli tutmalısın.
app.secret_key = "super_gizli_nba_anahtari"

app.register_blueprint(players_bp)
app.register_blueprint(games_bp)
app.register_blueprint(teams_bp)

# ==========================================
# LOGIN & AUTHENTICATION (GİRİŞ İŞLEMLERİ)
# ==========================================
@app.route("/", methods=["GET", "POST"])
def login_page():
    if "logged_in" in session:
        return redirect(url_for("home_page"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        con = sqlite3.connect("nba.db")
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        user = cur.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        con.close()

        # KONTROL BURADA DEĞİŞTİ:
        # User varsa VE hash'ler eşleşiyorsa giriş yap
        if user and check_password_hash(user["password"], password):
            session["logged_in"] = True
            session["username"] = user["username"]
            return redirect(url_for("home_page"))
        else:
            return render_template("login.html", error="Hatalı kullanıcı adı veya şifre!")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()  # Tüm oturum verilerini (kullanıcı adı, logged_in durumu) siler
    return redirect(url_for("login_page"))  # Giriş sayfasına geri gönderir

# ==========================================
# ANA SAYFA (DASHBOARD)
# ==========================================

@app.route("/home")
def home_page():
    # GÜVENLİK KONTROLÜ
    if "logged_in" not in session:
        return redirect(url_for("login_page"))

    today = datetime.today()
    day_name = today.strftime("%A")
    return render_template("home.html", date=day_name)


# ==========================================
# ARENAS (STADIUMS) BÖLÜMÜ
# ==========================================

@app.route("/arenas", methods=["GET", "POST"])
def arenas_page():
    if "logged_in" not in session: return redirect(url_for("login_page"))

    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Arama İşlemi
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

    # Dropdown için takımlar
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
    if "logged_in" not in session: return redirect(url_for("login_page"))

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
    if "logged_in" not in session: return redirect(url_for("login_page"))

    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    cur.execute("DELETE FROM stadiums WHERE stadium_id = ?", (id,))
    con.commit()
    con.close()
    return redirect(url_for("arenas_page"))

@app.route("/arenas/update/<int:id>", methods=["POST"])
def update_arena(id):
    if "logged_in" not in session: return redirect(url_for("login_page"))

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


# ==========================================
# ABOUT PAGE
# ==========================================

@app.route("/about")
def about_page():
    # Hakkımızda sayfası genelde herkese açıktır, ama istersen burayı da kilitleyebilirsin.
    return render_template("about.html")


# ==========================================
# PLAYERS (OYUNCULAR) BÖLÜMÜ
# ==========================================

@app.route("/players")
def players_page():
    if "logged_in" not in session: return redirect(url_for("login_page"))

    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # GET parametreleri
    team = request.args.get("team", "").strip()
    name = request.args.get("name", "").strip()

    # Temel sorgu
    query = """
        SELECT p.*, t.team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE 1 = 1
    """
    params = []

    # İsim filtresi
    if name:
        query += " AND p.full_name LIKE ?"
        params.append("%" + name + "%")

    # Takım filtresi
    if team:
        query += " AND t.team_name = ?"
        params.append(team)

    query += " ORDER BY p.player_id"

    players = cur.execute(query, params).fetchall()

    # Dropdown için takımlar
    all_teams = cur.execute("SELECT team_name FROM teams ORDER BY team_name").fetchall()

    return render_template("players_list.html",
                           players=players,
                           teams=all_teams)

@app.route("/players/add", methods=["GET", "POST"])
def add_player():
    if "logged_in" not in session: return redirect(url_for("login_page"))

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
        "player_id": "", "team_id": "", "full_name": "", "position": "",
        "height_cm": "", "weight_kg": "", "birthdate": "", "country": ""
    }

    return render_template(
        "players_form.html",
        title="Add Player",
        player=empty_player,
        teams=teams
    )

@app.route("/players/edit/<int:pid>", methods=["GET", "POST"])
def edit_player(pid):
    if "logged_in" not in session: return redirect(url_for("login_page"))

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

@app.route("/players/delete/<int:pid>")
def delete_player(pid):
    if "logged_in" not in session: return redirect(url_for("login_page"))

    con = sqlite3.connect("nba.db")
    con.execute("PRAGMA foreign_keys = ON;")
    cur = con.cursor()

    try:
        cur.execute("DELETE FROM players WHERE player_id=?", (pid,))
        con.commit()
    except Exception as e:
        print("Delete error:", e)

    return redirect("/players")


# ==========================================
# TEAMS (TAKIMLAR) BÖLÜMÜ
# ==========================================

@app.route("/teams")
def teams_page():
    if "logged_in" not in session: return redirect(url_for("login_page"))

    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    teams = cur.execute("""
        SELECT * FROM teams
        ORDER BY team_id
    """).fetchall()

    return render_template("teams_list.html", teams=teams)


# -------- API ENDPOINTS --------
@app.route("/api/games")
def get_games_by_date_api():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify([])
    
    with sqlite3.connect("nba.db") as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        
        query = """
            SELECT 
                g.game_id, 
                g.home_team_id, 
                g.away_team_id,
                ht.team_name as home_name,
                at.team_name as away_name
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id
            LEFT JOIN teams at ON g.away_team_id = at.team_id
            WHERE g.game_date = ? 
            ORDER BY g.game_id
        """
        games = cur.execute(query, (date_str,)).fetchall()
        
        return jsonify([
            {
                "id": g["game_id"], 
                "label": f"Game {g['game_id']}: {g['home_name']} vs {g['away_name']}"
            } 
            for g in games
        ])

@app.route("/api/game/<int:game_id>/players")
def get_game_players_api(game_id):
    with sqlite3.connect("nba.db") as con:
        cur = con.cursor()
        
        game = cur.execute("SELECT home_team_id, away_team_id FROM games WHERE game_id=?", (game_id,)).fetchone()
        if not game:
            return jsonify([])
            
        query = """
            SELECT player_id, full_name, team_id 
            FROM players 
            WHERE team_id IN (?, ?) 
            ORDER BY full_name
        """
        players = cur.execute(query, (game[0], game[1])).fetchall()
        
        return jsonify([{"id": p[0], "name": p[1]} for p in players])

# -------- STATISTICS LIST --------
@app.route("/statistics")
def statistics_page():
    if "logged_in" not in session: return redirect(url_for("login_page"))

    with sqlite3.connect("nba.db") as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        # 1. Get the new 'name' parameter
        filter_date = request.args.get('date', '')
        filter_game_id = request.args.get('game_id', '')
        filter_player_id = request.args.get('player_id', '')
        filter_name = request.args.get('name', '').strip()  # <--- NEW

        sort_by = request.args.get('sort', 'date')
        order = request.args.get('order', 'desc').lower()
        if order not in ['asc', 'desc']: order = 'desc'
        page = request.args.get('page', 1, type=int)
        per_page = 20

        sql = """
            SELECT s.*, p.full_name, g.game_date, g.season
            FROM player_game_stats s
            JOIN players p ON s.player_id = p.player_id
            JOIN games g ON s.game_id = g.game_id
            WHERE 1=1
        """
        params = []

        if filter_date:
            sql += " AND g.game_date = ?"
            params.append(filter_date)
        if filter_game_id:
            sql += " AND s.game_id = ?"
            params.append(filter_game_id)
        if filter_player_id:
            sql += " AND s.player_id = ?"
            params.append(filter_player_id)
        
        # 2. Add SQL logic for name search
        if filter_name:
            sql += " AND p.full_name LIKE ?"
            params.append(f"%{filter_name}%")

        summary = None
        # 3. Update summary check to include filter_name
        if filter_date or filter_game_id or filter_player_id or filter_name:
            avg_sql = """
                SELECT COUNT(*) as games_played, 
                       COALESCE(AVG(s.points), 0) as ppg,
                       COALESCE(AVG(s.assists), 0) as apg, 
                       COALESCE(AVG(s.rebounds), 0) as rpg
                FROM player_game_stats s
                JOIN players p ON s.player_id = p.player_id
                JOIN games g ON s.game_id = g.game_id
                WHERE 1=1
            """
            avg_params = []
            if filter_date:
                avg_sql += " AND g.game_date = ?"
                avg_params.append(filter_date)
            if filter_game_id:
                avg_sql += " AND s.game_id = ?"
                avg_params.append(filter_game_id)
            if filter_player_id:
                avg_sql += " AND s.player_id = ?"
                avg_params.append(filter_player_id)
            if filter_name:
                avg_sql += " AND p.full_name LIKE ?"
                avg_params.append(f"%{filter_name}%")
                
            summary = cur.execute(avg_sql, avg_params).fetchone()
            
        
        valid_sorts = {
            'points': 's.points', 'assists': 's.assists',
            'rebounds': 's.rebounds', 'minutes': 's.minutes_played',
            'date': 'g.game_date', 'player': 'p.full_name'
        }
        sort_col = valid_sorts.get(sort_by, 'g.game_date')
        is_numeric = sort_by in ['points', 'assists', 'rebounds', 'minutes']
        
        null_check = f"(CASE WHEN {sort_col} IS NULL OR {sort_col} = '' THEN 1 ELSE 0 END) ASC"
        
        if is_numeric:
            sql += f" ORDER BY {null_check}, CAST({sort_col} AS REAL) {order.upper()}"
        else:
            sql += f" ORDER BY {null_check}, {sort_col} {order.upper()}"

        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        total = cur.execute(count_sql, params).fetchone()[0]
        total_pages = (total + per_page - 1) // per_page

        offset = (page - 1) * per_page
        sql += " LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        statistics = cur.execute(sql, params).fetchall()

    return render_template(
        "statistics/statistics_list.html",
        statistics=statistics, page=page, total_pages=total_pages,
        filter_date=filter_date, filter_game_id=filter_game_id, 
        filter_player_id=filter_player_id, filter_name=filter_name, # <--- Pass filter_name
        sort_by=sort_by, order=order,
        next_order='asc' if order == 'desc' else 'desc', summary=summary
    )

# -------- STATISTIC DETAIL VIEW --------
@app.route("/statistics/view/<int:sid>")
def view_statistic(sid):
    with sqlite3.connect("nba.db") as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        # UPDATED SQL QUERY
        sql = """
            SELECT 
                s.*, 
                p.full_name, 
                p.player_id,
                pt.team_name as player_team_name,  -- NEW: Get player's team name
                g.game_date, 
                g.season,
                ht.team_name as home_name, 
                at.team_name as away_name
            FROM player_game_stats s
            JOIN players p ON s.player_id = p.player_id
            LEFT JOIN teams pt ON p.team_id = pt.team_id -- NEW: Join for player's team
            JOIN games g ON s.game_id = g.game_id
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id
            LEFT JOIN teams at ON g.away_team_id = at.team_id
            WHERE s.stat_id = ?
        """
        stat = cur.execute(sql, (sid,)).fetchone()
        
        if not stat:
            return redirect("/statistics")

        # Use COALESCE to handle NULL averages (e.g. if minutes were never recorded)
        avg_sql = """
            SELECT 
                COALESCE(AVG(s.points), 0) as avg_pts,
                COALESCE(AVG(s.assists), 0) as avg_ast,
                COALESCE(AVG(s.rebounds), 0) as avg_reb,
                COALESCE(AVG(s.minutes_played), 0) as avg_min,
                COUNT(*) as games_played
            FROM player_game_stats s
            JOIN games g ON s.game_id = g.game_id
            WHERE s.player_id = ? AND g.season = ?
        """
        avgs = cur.execute(avg_sql, (stat['player_id'], stat['season'])).fetchone()

        game_avg_sql = """
            SELECT AVG(points) as g_pts, AVG(assists) as g_ast, AVG(rebounds) as g_reb 
            FROM player_game_stats 
            WHERE game_id = ?
        """
        game_avgs = cur.execute(game_avg_sql, (stat['game_id'],)).fetchone()

    return render_template(
        "statistics/view.html", 
        stat=stat, 
        avgs=avgs, 
        game_avgs=game_avgs
    )

# -------- ADD STATISTIC --------
@app.route("/statistics/add", methods=["GET", "POST"])
def add_statistic():
    if "logged_in" not in session: return redirect(url_for("login_page"))
    
    error = None
    statistic = {
        "stat_id": "", "player_id": "", "game_id": "", "game_date": "",
        "points": "", "assists": "", "rebounds": "", "minutes_played": ""
    }
    
    if request.method == "POST":
        with sqlite3.connect("nba.db") as con:
            cur = con.cursor()
            
            pid = request.form.get("player_id")
            gid = request.form.get("game_id")
            
            try:
                pts = int(request.form["points"])
                ast = int(request.form["assists"])
                reb = int(request.form["rebounds"])
                mins = float(request.form["minutes_played"])
            except ValueError:
                error = "Numeric fields must be valid numbers."
            
            statistic.update({
                "player_id": int(pid) if pid else "",
                "game_id": int(gid) if gid else "",
                "points": request.form["points"], 
                "assists": request.form["assists"], 
                "rebounds": request.form["rebounds"], 
                "minutes_played": request.form["minutes_played"]
            })

            if not error and (pts < 0 or ast < 0 or reb < 0):
                error = "Stats cannot be negative."
            elif not error and (mins < 0 or mins > 65):
                error = "Minutes must be 0-65."
            
            if not error:
                exists = cur.execute("SELECT 1 FROM player_game_stats WHERE player_id=? AND game_id=?", (pid, gid)).fetchone()
                if exists:
                    error = "Statistics for this Player in this Game already exist."

            if not error:
                cur.execute("""
                    INSERT INTO player_game_stats (player_id, game_id, points, assists, rebounds, minutes_played)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pid, gid, pts, ast, reb, mins))
                con.commit()
                return redirect("/statistics")

    return render_template("statistics/statistics_form.html", title="Add Statistic", statistic=statistic, error=error)

@app.route("/statistics/edit/<int:sid>", methods=["GET", "POST"])
def edit_statistic(sid):
    if "logged_in" not in session: return redirect(url_for("login_page"))

    with sqlite3.connect("nba.db") as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        query = """
            SELECT 
                s.*, 
                p.full_name,
                g.game_date,
                ht.team_name as home_name, 
                at.team_name as away_name 
            FROM player_game_stats s
            JOIN players p ON s.player_id = p.player_id
            JOIN games g ON s.game_id = g.game_id
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id
            LEFT JOIN teams at ON g.away_team_id = at.team_id
            WHERE s.stat_id=?
        """
        row = cur.execute(query, (sid,)).fetchone()
        
        if not row:
            return redirect("/statistics")
            
        statistic = dict(row)
        error = None

        if request.method == "POST":
            try:
                pts = int(request.form["points"])
                ast = int(request.form["assists"])
                reb = int(request.form["rebounds"])
                mins = float(request.form["minutes_played"])
            except ValueError:
                error = "Numeric fields must be valid numbers."

            statistic.update({
                "points": pts, "assists": ast, "rebounds": reb, "minutes_played": mins
            })

            if not error and (pts < 0 or ast < 0 or reb < 0):
                error = "Stats cannot be negative."
            elif not error and (mins < 0 or mins > 65):
                error = "Minutes must be 0-65."

            if not error:
                cur.execute("""
                    UPDATE player_game_stats
                    SET points=?, assists=?, rebounds=?, minutes_played=?
                    WHERE stat_id=?
                """, (pts, ast, reb, mins, sid))
                con.commit()
                return redirect("/statistics")

    return render_template(
        "statistics/statistics_form.html", 
        title="Edit Statistic", 
        statistic=statistic, 
        error=error
    )

@app.route("/statistics/delete/<int:sid>")
def delete_statistic(sid):
    if "logged_in" not in session: return redirect(url_for("login_page"))

    with sqlite3.connect("nba.db") as con:
        con.execute("PRAGMA foreign_keys = ON;")
        cur = con.cursor()
        try:
            cur.execute("DELETE FROM player_game_stats WHERE stat_id=?", (sid,))
            con.commit()
        except:
            pass
        return redirect("/statistics")
    
@app.route("/api/players/search")
def search_players_api():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    
    with sqlite3.connect("nba.db") as con:
        cur = con.cursor()
        # Find top 10 players matching the search string
        sql = "SELECT full_name FROM players WHERE full_name LIKE ? ORDER BY full_name LIMIT 10"
        results = cur.execute(sql, (f"%{query}%",)).fetchall()
        
        # Return just the names as a JSON list
        return jsonify([row[0] for row in results])
    
@app.route("/api/check_stat_exists")
def check_stat_exists_api():
    pid = request.args.get("player_id")
    gid = request.args.get("game_id")
    
    if not pid or not gid:
        return jsonify({"exists": False})
    
    with sqlite3.connect("nba.db") as con:
        cur = con.cursor()
        row = cur.execute(
            "SELECT stat_id FROM player_game_stats WHERE player_id=? AND game_id=?", 
            (pid, gid)
        ).fetchone()
        
        if row:
            return jsonify({"exists": True, "stat_id": row[0]})
        return jsonify({"exists": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)