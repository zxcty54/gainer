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

# ✅ Batch Fetch Market Data
def fetch_all_indices():
    try:
        print("🔄 Fetching all market indices in a batch request...")
        
        # ✅ Batch Download All Indices
        data = yf.download(list(INDICES.values()), period="2d", auto_adjust=True, progress=False)

        # ✅ Ensure Data Exists
        if data.empty:
            print("❌ No data received from Yahoo Finance!")
            return

        # ✅ Process Each Index
        for name, symbol in INDICES.items():
            try:
                history = data["Close"][symbol].dropna()

                # ✅ Ensure at Least 2 Data Points
                if len(history) < 2:
                    print(f"⚠️ Insufficient data for {name} ({symbol})")
                    continue

                # ✅ Extract Prices
                prev_close = float(history.iloc[-2])
                current_price = float(history.iloc[-1])

                # ✅ Calculate % Change
                percent_change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0

                # ✅ Store in Firestore
                index_data = {
                    "current_price": round(current_price, 2),
                    "percent_change": round(percent_change, 2),
                    "previous_close": round(prev_close, 2),
                    "last_updated": firestore.SERVER_TIMESTAMP
                }

                db.collection("market_indices").document(name).set(index_data)
                print(f"✅ {name} updated: {index_data}")

            except Exception as e:
                print(f"⚠️ Error processing {name} ({symbol}): {str(e)}")

    except Exception as e:
        print(f"❌ Batch fetch error: {str(e)}")

# ✅ Update Market Data
def update_market_data():
    fetch_all_indices()
    threading.Timer(300, update_market_data).start()  # Auto-run every 5 minutes

# ✅ Start Background Update Task
update_market_data()

@app.route('/')
def home():
    return "✅ Batch Market Indices API is Running!"

@app.route('/update-market-indices')
def manual_update():
    try:
        fetch_all_indices()
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
