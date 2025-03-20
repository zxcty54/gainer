import os
from flask import Flask, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Market Indices API is Running!"

@app.route('/market-indices')
def get_market_indices():
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
            history = stock.history(period="2d")  # ✅ Fetch last 2 days of data

            # ✅ **Check if enough data is available**
            if history.empty or len(history) < 2:
                print(f"⚠ No sufficient data for {name} ({symbol})")
                index_data[name] = {"current_price": "N/A", "percent_change": "N/A"}
                continue

            # ✅ **Safely access Close prices**
            prev_close = history["Close"].iloc[-2]  # Previous Close (Day before)
            current_price = history["Close"].iloc[-1]  # Latest Close

            if prev_close is None or current_price is None:
                print(f"⚠ Missing Close data for {name}")
                index_data[name] = {"current_price": "N/A", "percent_change": "N/A"}
                continue

            # ✅ **Calculate percentage change using Previous Close**
            percent_change = ((current_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0

            index_data[name] = {
                "current_price": round(current_price, 2),
                "percent_change": round(percent_change, 2),
                "previous_close": round(prev_close, 2)  # ✅ Added Previous Close
            }

        return jsonify(index_data)

    except Exception as e:
        print("🚨 Error fetching market indices:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
