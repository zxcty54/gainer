import os
import json
import threading
import time
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

# ✅ Load Firebase credentials from Render environment variable
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)
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

# ✅ Fetch Individual Market Data
def fetch_index_data(name, symbol, retries=3):
    for attempt in range(retries):
        try:
            print(f"🔄 Fetching {name} ({symbol}) - Attempt {attempt + 1}")

            # Fetch last 2 days of data
            data = yf.download(symbol, period="2d", auto_adjust=True, progress=False)

            if data.empty:
                print(f"❌ No data for {name} ({symbol})")
                continue  # Retry

            # Extract close prices
            if "Close" not in data or data["Close"].empty:
                print(f"⚠️ No Close price data for {name} ({symbol})")
                continue  # Retry

            history = data["Close"].dropna()

            if history.empty or len(history) < 2:
                print(f"⚠️ Insufficient data for {name} ({symbol})")
                continue  # Retry

            # Calculate values
            prev_close = history.iloc[-2]
            current_price = history.iloc[-1]
            percent_change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0

            # ✅ Store in Firestore
            index_data = {
                "current_price": round(current_price, 2),
                "percent_change": round(percent_change, 2),
                "previous_close": round(prev_close, 2),
                "last_updated": firestore.SERVER_TIMESTAMP  # Add timestamp
            }

            db.collection("market_indices").document(name).set(index_data)
            print(f"✅ {name} updated successfully: {index_data}")
            return

        except Exception as e:
            print(f"⚠️ Error fetching {name} ({symbol}): {str(e)}")
        
        time.sleep(2)  # Wait before retrying

    print(f"❌ Failed to fetch {name} after {retries} attempts")

# ✅ Update Market Data
def update_market_data():
    print("🔄 Updating Market Indices...")
    for name, symbol in INDICES.items():
        fetch_index_data(name, symbol)
    
    # ✅ Run every 5 minutes
    threading.Timer(300, update_market_data).start()

# ✅ Start Background Update Task
update_market_data()

@app.route('/')
def home():
    return "✅ Market Indices API with Firestore is Running!"

@app.route('/update-market-indices')
def manual_update():
    try:
        update_market_data()
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
