"""
checker.py — FlightDrop price checker (Travelpayouts version)
--------------------------------------------------------------
This script runs on a schedule and:
  1. Loads all active subscribers from the database
  2. Checks the current cheapest price for their route via Travelpayouts
  3. Sends an alert email if the price drops below their target
"""

import sqlite3
import os
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

TRAVELPAYOUTS_TOKEN = os.getenv('TRAVELPAYOUTS_TOKEN')
RESEND_API_KEY      = os.getenv('RESEND_API_KEY')
FROM_EMAIL          = os.getenv('FROM_EMAIL', 'alerts@yourdomain.com')
DATABASE            = 'flightdrop.db'


def get_cheapest_flight(origin, destination, travel_month):
    """
    Fetch the cheapest flight price for a route in a given month.
    Uses Travelpayouts Aviasales Data API (free, cached prices).
    travel_month format: "2025-08"
    """
    try:
        response = requests.get(
            'https://api.travelpayouts.com/v1/prices/cheap',
            params={
                'origin':      origin,
                'destination': destination,
                'depart_date': travel_month,
                'currency':    'usd',
                'token':       TRAVELPAYOUTS_TOKEN,
            },
            timeout=10
        )

        if response.status_code != 200:
            print(f"  ⚠️  API error {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()

        if not data.get('success') or not data.get('data'):
            print(f"  ℹ️  No flights found for {origin} → {destination} in {travel_month}")
            return None

        # Grab the first (cheapest) result from the response
        destination_data = data['data'].get(destination, {})
        if not destination_data:
            all_results = list(data['data'].values())
            if not all_results:
                return None
            destination_data = all_results[0]

        first_result = destination_data.get('0') or list(destination_data.values())[0]
        return float(first_result['price'])

    except Exception as e:
        print(f"  ❌ Error fetching price: {e}")
        return None


def build_booking_link(origin, destination, travel_month):
    """Build an Aviasales affiliate booking link (earns you commission)."""
    try:
        year, month = travel_month.split('-')
        month_abbrs = ['JAN','FEB','MAR','APR','MAY','JUN',
                       'JUL','AUG','SEP','OCT','NOV','DEC']
        month_abbr = month_abbrs[int(month) - 1]
        date_str = f"15{month_abbr}"
    except:
        date_str = "15AUG"
    return f"https://www.aviasales.com/search/{origin}{date_str}{destination}1"


def send_alert_email(to_email, origin, destination, price, max_price, travel_month):
    """Send a price drop alert email via Resend."""

    booking_link   = build_booking_link(origin, destination, travel_month)
    unsubscribe_url = f"http://localhost:5000/unsubscribe?email={to_email}"

    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:2rem">
      <h2 style="color:#1a1a2e">✈️ Price drop alert!</h2>
      <p>A fare just dropped below your target price.</p>
      <div style="background:#f0f7ff;border-radius:8px;padding:1.25rem;margin:1.5rem 0">
        <p style="margin:0 0 0.5rem"><strong>Route:</strong> {origin} → {destination}</p>
        <p style="margin:0 0 0.5rem"><strong>Travel month:</strong> {travel_month}</p>
        <p style="margin:0 0 0.5rem"><strong>Current price:</strong>
          <span style="color:#1a7f3c;font-size:1.2rem;font-weight:bold">${price:.0f}</span>
        </p>
        <p style="margin:0;color:#666;font-size:0.85rem">Your target: below ${max_price:.0f}</p>
      </div>
      <p>
        <a href="{booking_link}"
           style="background:#4f8ef7;color:white;padding:0.6rem 1.2rem;border-radius:6px;
                  text-decoration:none;font-weight:600">
          Book this flight →
        </a>
      </p>
      <p style="color:#999;font-size:0.75rem;margin-top:2rem">
        Prices change fast — act quickly!<br>
        <a href="{unsubscribe_url}" style="color:#999">Unsubscribe</a>
      </p>
    </div>
    """

    response = requests.post(
        'https://api.resend.com/emails',
        headers={
            'Authorization': f'Bearer {RESEND_API_KEY}',
            'Content-Type':  'application/json',
        },
        json={
            'from':    FROM_EMAIL,
            'to':      [to_email],
            'subject': f'✈️ ${price:.0f} fare: {origin} → {destination} ({travel_month})',
            'html':    html_body,
        }
    )

    if response.status_code in (200, 201):
        print(f"  📧 Alert sent to {to_email}")
    else:
        print(f"  ❌ Email failed: {response.status_code} — {response.text}")


def save_price(origin, destination, travel_month, price):
    """Save price to history table for trend tracking."""
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        'INSERT INTO price_history (origin, destination, travel_month, price) VALUES (?,?,?,?)',
        (origin, destination, travel_month, price)
    )
    conn.commit()
    conn.close()


def run_check():
    """Check prices for all subscribers and send alerts if prices dropped."""

    print(f"\n{'─'*50}")
    print(f"🔍 Running price check at {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    if not TRAVELPAYOUTS_TOKEN:
        print("❌ TRAVELPAYOUTS_TOKEN not set in .env file!")
        return

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    subscribers = conn.execute('SELECT * FROM subscribers WHERE active = 1').fetchall()
    conn.close()

    if not subscribers:
        print("ℹ️  No active subscribers yet.")
        return

    print(f"👥 Checking {len(subscribers)} subscriber(s)...")

    checked_routes = {}

    for sub in subscribers:
        route_key = f"{sub['origin']}-{sub['destination']}-{sub['travel_month']}"
        print(f"\n  {sub['origin']} → {sub['destination']} ({sub['travel_month']}) for {sub['email']}")

        if route_key in checked_routes:
            price = checked_routes[route_key]
            print(f"  (cached: ${price})")
        else:
            price = get_cheapest_flight(sub['origin'], sub['destination'], sub['travel_month'])
            checked_routes[route_key] = price
            if price:
                save_price(sub['origin'], sub['destination'], sub['travel_month'], price)

        if price is None:
            print(f"  ⏭️  No price found, skipping.")
            continue

        print(f"  💰 Current: ${price:.0f} | Target: below ${sub['max_price']:.0f}")

        if price <= sub['max_price']:
            print(f"  🎯 Price dropped! Sending alert...")
            send_alert_email(
                to_email=sub['email'],
                origin=sub['origin'],
                destination=sub['destination'],
                price=price,
                max_price=sub['max_price'],
                travel_month=sub['travel_month'],
            )
        else:
            print(f"  ⏳ Not yet (${price - sub['max_price']:.0f} above target)")

        time.sleep(0.5)

    print(f"\n✅ Check complete.")


if __name__ == '__main__':
    CHECK_EVERY_HOURS = 4
    while True:
        run_check()
        print(f"Next check in {CHECK_EVERY_HOURS} hours...")
        time.sleep(CHECK_EVERY_HOURS * 60 * 60)
    #     time.sleep(CHECK_EVERY_HOURS * 60 * 60)
