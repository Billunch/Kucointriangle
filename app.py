
import os
import time
import ccxt
import requests
from dotenv import load_dotenv
from flask import Flask
import threading
import schedule

# === 載入環境變數 ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MIN_PROFIT = float(os.getenv("MIN_PROFIT_RATE", "0.0104"))
FEE_RATE = 0.001
SLIPPAGE = 0.002
START_USDT = 4700  # 15萬台幣 ≈ 4700 USDT

sim_balance = {
    "usdt": START_USDT,
    "history": []
}

app = Flask(__name__)
exchange = ccxt.kucoin()
exchange.load_markets()

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def get_price(pair):
    ticker = exchange.fetch_ticker(pair)
    return float(ticker["bid"]), float(ticker["ask"])

def triangular_arbitrage():
    try:
        usdt_arb_bid, usdt_arb_ask = get_price("ARB/USDT")
        arb_eth_bid, arb_eth_ask = get_price("ARB/ETH")
        eth_usdt_bid, eth_usdt_ask = get_price("ETH/USDT")

        amount = 1
        arb = amount / (usdt_arb_ask * (1 + FEE_RATE + SLIPPAGE))
        eth = arb * arb_eth_bid * (1 - FEE_RATE - SLIPPAGE)
        usdt_back = eth * eth_usdt_bid * (1 - FEE_RATE - SLIPPAGE)

        profit_ratio = (usdt_back - amount) / amount

        if profit_ratio > MIN_PROFIT:
            profit_usdt = (usdt_back - amount) * sim_balance["usdt"]
            sim_balance["usdt"] += profit_usdt
            sim_balance["history"].append(profit_usdt)
            send_telegram(f"🚨 KuCoin 三角套利機會
利潤率：{profit_ratio*100:.2f}%
模擬獲利：{profit_usdt:.2f} USDT")
    except Exception as e:
        print("❌ 錯誤：", e)

def schedule_daily_report():
    schedule.every().day.at("09:00").do(send_daily_report)
    while True:
        schedule.run_pending()
        time.sleep(30)

def send_daily_report():
    total = sim_balance["usdt"]
    history = sim_balance["history"]
    profit = sum(history)
    msg = f"📊 每日績效報告
💰 資產：{total:.2f} USDT
📈 累積模擬獲利：{profit:.2f} USDT
📆 次數：{len(history)}"
    send_telegram(msg)

@app.route("/")
def index():
    return "✅ KuCoin Triangular Arbitrage Simulator Running"

if __name__ == "__main__":
    threading.Thread(target=schedule_daily_report, daemon=True).start()
    threading.Thread(target=lambda: [triangular_arbitrage() or time.sleep(1) for _ in iter(int, 1)], daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
