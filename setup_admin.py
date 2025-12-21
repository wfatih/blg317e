import sqlite3
from werkzeug.security import generate_password_hash

def create_admin_table():
    con = sqlite3.connect("nba.db")
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    hashed_password = generate_password_hash("1234") 
    
    try:
        cur.execute("INSERT INTO admins (username, password) VALUES (?, ?)", ("admin", hashed_password))
        print(f"Admin eklendi. Hash: {hashed_password}")
    except sqlite3.IntegrityError:
        print("Admin zaten var.")

    con.commit()
    con.close()

if __name__ == "__main__":
    create_admin_table()