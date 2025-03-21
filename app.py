import os
import json
import threading
import time
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import schedule  # Install with 'pip install schedule'

app = Flask(__name__)
CORS(app)

# ✅ Load Firebase credentials from Render environment variable
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)  # ✅ Convert string to JSON
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    raise ValueError("🚨 FIREBASE_CREDENTIALS environment variable is missing!")

# ✅ Market Indices to Fetch
INDICES = {
    "Dow Jones": "^DJI",
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK"
}

# ✅ Fetch all indices in one API call every 5 minutes
def update_market_data():
    try:
        tickers = list(INDICES.values())  # Get all ticker symbols
        stock_data = yf.download(tickers, period="2d", group_by='ticker')  # ✅ Batch API request

        index_data = {}

        for name, symbol in INDICES.items():
            if symbol not in stock_data:
                print(f"❌ No data for {name}")
                continue

            history = stock_data[symbol]["Close"]

            if history.empty or len(history) < 2:
                index_data[name] = {"current_price": "N/A", "percent_change": "N/A"}
                continue

            prev_close = history.iloc[-2]
            current_price = history.iloc[-1]
            percent_change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0

            index_data[name] = {
                "current_price": round(current_price, 2),
                "percent_change": round(percent_change, 2),
                "previous_close": round(prev_close, 2)
            }

            # ✅ Store in Firestore
            db.collection("market_indices").document(name).set(index_data[name])

        print("✅ Market data updated in Firestore:", index_data)

    except Exception as e:
        print("❌ Error updating market data:", str(e))

# ✅ Schedule batch update every 5 minutes
schedule.every(5).minutes.do(update_market_data)

# ✅ Background Scheduler Loop
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(10)  # ✅ Check every 10 seconds for scheduled tasks

# ✅ Start scheduler in a separate thread
threading.Thread(target=run_scheduler, daemon=True).start()

@app.route('/')
def home():
    return "✅ Market Indices API with Firestore is Running!"

@app.route('/update-market-indices')
def manual_update():
    try:
        update_market_data()  # Call the update function manually
        return jsonify({"message": "✅ Market indices updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/market-indices')
def get_market_indices():
    try:
        docs = db.collection("market_indices").stream()
        data = {doc.id: doc.to_dict() for doc in docs}
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
