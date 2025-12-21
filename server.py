from datetime import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
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
    return render_template("arenas.html", arenas=arenas, teams=teams)

@app.route("/arenas/add", methods=["POST"])
def add_arena():
    if "logged_in" not in session: return redirect(url_for("login_page"))

    stadium_name = request.form.get("stadium_name")
    city = request.form.get("city")
    capacity = request.form.get("capacity")
    team_id = request.form.get("team_id")

    if not team_id:
        team_id = None

    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    query = "INSERT INTO stadiums (stadium_name, city, capacity, team_id) VALUES (?, ?, ?, ?)"
    cur.execute(query, (stadium_name, city, capacity, team_id))
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

    if not team_id:
        team_id = None

    con = sqlite3.connect("nba.db")
    cur = con.cursor()
    query = """
        UPDATE stadiums 
        SET stadium_name=?, city=?, capacity=?, team_id=? 
        WHERE stadium_id=?
    """
    cur.execute(query, (stadium_name, city, capacity, team_id, id))
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


# ==========================================
# STATISTICS (İSTATİSTİKLER) BÖLÜMÜ
# ==========================================

@app.route("/statistics")
def statistics_page():
    if "logged_in" not in session: return redirect(url_for("login_page"))

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

@app.route("/statistics/add", methods=["GET", "POST"])
def add_statistic():
    if "logged_in" not in session: return redirect(url_for("login_page"))

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
        "stat_id": "", "player_id": "", "game_id": "",
        "points": "", "assists": "", "rebounds": "", "minutes_played": "",
    }

    return render_template(
        "statistics_form.html", 
        title="Add Statistic",
        statistic=empty_statistic, 
        players=players, 
        games=games
    )

@app.route("/statistics/edit/<int:sid>", methods=["GET", "POST"])
def edit_statistic(sid):
    if "logged_in" not in session: return redirect(url_for("login_page"))

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

@app.route("/statistics/delete/<int:sid>")
def delete_statistic(sid):
    if "logged_in" not in session: return redirect(url_for("login_page"))

    with sqlite3.connect("nba.db") as con:
        con.execute("PRAGMA foreign_keys = ON;")
        cur = con.cursor()

        try:
            cur.execute("DELETE FROM player_game_stats WHERE stat_id=?", (sid,))
            con.commit()
        except Exception as e:
            print("Delete error:", e)

        return redirect("/statistics")


# ==========================================
# UYGULAMAYI BAŞLAT
# ==========================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)