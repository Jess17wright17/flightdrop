"""
app.py — FlightDrop backend server
-----------------------------------
This is the main web server. It does two things:
  1. Accepts sign-ups from the landing page (/subscribe)
  2. Saves subscribers to a SQLite database

Run it with:  python app.py
It will start a local server at http://localhost:5000
"""

import sqlite3
import os
from flask import Flask, request, jsonify
from flask_cors import CORS  # Allows the HTML page to talk to this server

# ── App setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)  # Allow requests from any origin (needed for local development)

# The database file will be created automatically in the same folder
DATABASE = 'flightdrop.db'


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Lets us access columns by name
    return conn


def init_db():
    """
    Create the subscribers table if it doesn't exist yet.
    This runs once when the app starts.
    """
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT NOT NULL,
            origin       TEXT NOT NULL,   -- e.g. "LAX"
            destination  TEXT NOT NULL,   -- e.g. "JFK"
            max_price    REAL NOT NULL,   -- alert when price drops below this
            travel_month TEXT NOT NULL,   -- e.g. "2025-08"
            active       INTEGER DEFAULT 1,  -- 1 = active, 0 = unsubscribed
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Also create a table to track prices over time (useful for history)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            origin       TEXT NOT NULL,
            destination  TEXT NOT NULL,
            travel_month TEXT NOT NULL,
            price        REAL NOT NULL,
            checked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database ready.")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Receives a sign-up from the landing page.
    Expects JSON: { email, origin, destination, max_price, travel_month }
    """
    data = request.get_json()

    # Basic validation — make sure all fields are present
    required = ['email', 'origin', 'destination', 'max_price', 'travel_month']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    # Save to database
    conn = get_db()
    conn.execute('''
        INSERT INTO subscribers (email, origin, destination, max_price, travel_month)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data['email'].lower().strip(),
        data['origin'].upper().strip(),
        data['destination'].upper().strip(),
        float(data['max_price']),
        data['travel_month'],
    ))
    conn.commit()
    conn.close()

    print(f"✅ New subscriber: {data['email']} — {data['origin']} → {data['destination']}")
    return jsonify({'message': 'Subscribed successfully'}), 200


@app.route('/subscribers', methods=['GET'])
def list_subscribers():
    """
    Admin endpoint — view all active subscribers.
    Visit http://localhost:5000/subscribers in your browser.
    (You'd want to add password protection before going live!)
    """
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM subscribers WHERE active = 1 ORDER BY created_at DESC'
    ).fetchall()
    conn.close()

    # Convert rows to a list of dicts so Flask can return them as JSON
    result = [dict(row) for row in rows]
    return jsonify(result), 200


@app.route('/unsubscribe', methods=['GET'])
def unsubscribe():
    """
    Unsubscribe link — include ?email=user@example.com in the URL.
    You'll add this link to the bottom of every alert email.
    """
    email = request.args.get('email', '').lower().strip()
    if not email:
        return 'Missing email address.', 400

    conn = get_db()
    conn.execute('UPDATE subscribers SET active = 0 WHERE email = ?', (email,))
    conn.commit()
    conn.close()

    return f'<p style="font-family:sans-serif;padding:2rem">✅ {email} has been unsubscribed. Sorry to see you go!</p>'


# ── Start the server ──────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()  # Set up the database tables on first run
    print("🚀 FlightDrop server running at http://localhost:5000")
   app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
