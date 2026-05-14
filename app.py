import sqlite3
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = 'flightdrop.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT NOT NULL,
            origin       TEXT NOT NULL,
            destination  TEXT NOT NULL,
            max_price    REAL NOT NULL,
            travel_month TEXT NOT NULL,
            active       INTEGER DEFAULT 1,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
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
    print("Database ready.")


@app.route('/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json()
    required = ['email', 'origin', 'destination', 'max_price', 'travel_month']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400
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
    print(f"New subscriber: {data['email']}")
    return jsonify({'message': 'Subscribed successfully'}), 200


@app.route('/subscribers', methods=['GET'])
def list_subscribers():
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM subscribers WHERE active = 1 ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    result = [dict(row) for row in rows]
    return jsonify(result), 200


@app.route('/unsubscribe', methods=['GET'])
def unsubscribe():
    email = request.args.get('email', '').lower().strip()
    if not email:
        return 'Missing email address.', 400
    conn = get_db()
    conn.execute('UPDATE subscribers SET active = 0 WHERE email = ?', (email,))
    conn.commit()
    conn.close()
    return f'<p style="font-family:sans-serif;padding:2rem">Unsubscribed {email}.</p>'


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
