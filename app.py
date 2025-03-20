import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

# Load Firebase credentials from Render environment variable
firebase_credentials = json.loads(os.getenv("FIREBASE_CREDENTIALS"))

# Initialize Firebase Admin SDK
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route('/')
def home():
    return "Market Indices API with Firestore is Running!"

@app.route('/update-market-indices')
def update_market_indices():
    try:
        indices = {
            "Dow Jones": "^DJI",
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "NIFTY 50": "^NSEI",
            "SENSEX": "^BSESN",
            "BANK NIFTY": "^NSEBANK"
        }

        index_data = {}

        for name, symbol in indices.items():
            stock = yf.Ticker(symbol)
            history = stock.history(period="2d")  

            if history.empty or len(history) < 2:
                index_data[name] = {"current_price": "N/A", "percent_change": "N/A"}
                continue

            prev_close = history["Close"].iloc[-2]
            current_price = history["Close"].iloc[-1]

            if prev_close is None or current_price is None:
                index_data[name] = {"current_price": "N/A", "percent_change": "N/A"}
                continue

            percent_change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0

            index_data[name] = {
                "current_price": round(current_price, 2),
                "percent_change": round(percent_change, 2),
                "previous_close": round(prev_close, 2)
            }

            # Store in Firestore
            db.collection("market_indices").document(name).set(index_data)

        return jsonify({"message": "Market indices updated successfully", "data": index_data})

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
