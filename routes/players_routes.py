from flask import Blueprint, render_template, request, redirect
import sqlite3

# Blueprint oluştur
players_bp = Blueprint("players_bp", __name__)

# -------- PLAYERS LIST --------
@players_bp.route("/players")
def players_page():
    con = sqlite3.connect("nba.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # GET params
    team = request.args.get("team", "").strip()
    name = request.args.get("name", "").strip()
    page = int(request.args.get("page", 1))  # default page = 1
    per_page = 15

    # Base query
    query = """
        SELECT p.*, t.team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE 1 = 1
    """
    params = []

    # Filters
    if name:
        query += " AND p.full_name LIKE ?"
        params.append("%" + name + "%")

    if team:
        query += " AND t.team_name = ?"
        params.append(team)

    # COUNT for pagination
    count_query = "SELECT COUNT(*) FROM (" + query + ")"
    total_rows = cur.execute(count_query, params).fetchone()[0]
    total_pages = (total_rows + per_page - 1) // per_page

    # Add LIMIT/OFFSET
    offset = (page - 1) * per_page
    query += " ORDER BY p.player_id LIMIT ? OFFSET ?"
    params += [per_page, offset]

    players = cur.execute(query, params).fetchall()

    # Dropdown Teams
    all_teams = cur.execute(
        "SELECT team_name FROM teams ORDER BY team_name"
    ).fetchall()

    return render_template(
        "players/players_list.html",
        players=players,
        teams=all_teams,
        page=page,
        total_pages=total_pages,
        name=name,
        team=team
    )



# -------- ADD PLAYER --------
@players_bp.route("/players/add", methods=["GET", "POST"])
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
        "players/players_form.html",
        title="Add Player",
        player=empty_player,
        teams=teams
    )


# -------- EDIT PLAYER --------
@players_bp.route("/players/edit/<int:pid>", methods=["GET", "POST"])
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
        "players/players_form.html",
        title="Edit Player",
        player=player,
        teams=teams
    )


# -------- DELETE PLAYER --------
@players_bp.route("/players/delete/<int:pid>")
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
