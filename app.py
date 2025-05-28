import os
import time
import ccxt
import threading
import schedule
import requests
from flask import Flask
from dotenv import load_dotenv

# === 初始化 ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FEE_RATE = 0.001  # 假設每邊手續費 0.1%
MIN_PROFIT_RATE = float(os.getenv("MIN_PROFIT_RATE", "0.01"))  # 預設套利門檻 1%

# === 初始化交易所 ===
exchange = ccxt.kucoin()
exchange.load_markets()

# === 三角路徑設定 ===
tri_paths = [
    ["USDT", "BTC", "ETH"],
    ["USDT", "KCS", "ETH"],
    ["USDT", "TRX", "BTC"],
    ["USDT", "XRP", "ETH"]
]

# === 模擬資金 ===
sim_balance = {"usdt": 150000}

# === 發送 Telegram 訊息 ===
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("❌ Telegram 發送失敗：", e)

# === 三角套利計算 ===
def check_tri_arbitrage():
    for path in tri_paths:
        base, mid, quote = path
        try:
            pair1 = f"{mid}/{base}"   # 如 BTC/USDT
            pair2 = f"{quote}/{mid}"  # 如 ETH/BTC
            pair3 = f"{quote}/{base}"  # 如 ETH/USDT

            if pair1 not in exchange.symbols or pair2 not in exchange.symbols or pair3 not in exchange.symbols:
                continue

            p1 = exchange.fetch_ticker(pair1)['ask'] * (1 + FEE_RATE)
            p2 = exchange.fetch_ticker(pair2)['ask'] * (1 + FEE_RATE)
            p3 = exchange.fetch_ticker(pair3)['bid'] * (1 - FEE_RATE)

            cost = 1 * p1 * p2
            revenue = p3
            profit_ratio = (revenue - cost) / cost

            if profit_ratio > MIN_PROFIT_RATE:
                profit_usdt = sim_balance['usdt'] * profit_ratio
                msg = (
                    f"🚨 KuCoin 三角套利機會 ({base}->{mid}->{quote}->{base})\n"
                    f"利潤率：{profit_ratio * 100:.2f}%\n"
                    f"模擬獲利：{profit_usdt:.2f} USDT"
                )
                send_telegram(msg)
        except Exception as e:
            print(f"❌ 套利錯誤 ({path}):", e)

# === 每日報告 ===
def send_daily_report():
    msg = f"📊 模擬資金報告：\n💵 現金 USDT：{sim_balance['usdt']:.2f}"
    send_telegram(msg)

def schedule_report():
    schedule.every().day.at("09:00").do(send_daily_report)
    while True:
        schedule.run_pending()
        time.sleep(30)

# === Flask 偽裝頁面 ===
app = Flask(__name__)

@app.route('/')
def index():
    return "🟢 Multi-Tri Arbitrage on KuCoin Running"

if __name__ == "__main__":
    send_telegram("🚀 多組 KuCoin 三角套利模擬器已啟動")
    threading.Thread(target=schedule_report, daemon=True).start()
    threading.Thread(target=lambda: [check_tri_arbitrage() or time.sleep(1) for _ in iter(int, 1)], daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
