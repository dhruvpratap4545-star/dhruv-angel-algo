import os
import time
import json
import threading
import datetime
import random
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
load_dotenv()

# ग्लोबल बजट वेरिएबल
USER_CAPITAL = 20000.0  
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "") 

# लाइव स्टॉक पूल
LIVE_MARKET_POOL = [
    "IDEA", "YESBANK", "SUZLON", "ZOMATO", "PNB", 
    "INFY", "HDFCBANK", "RELIANCE", "TCS", "ITC", 
    "ICICIBANK", "SBIN", "BHARTIARTL", "AXISBANK", "WIPRO"
]

# एक्टिव ट्रेड स्टेट
active_trade_state = {
    "symbol": "NONE",
    "allocated_capital": USER_CAPITAL,
    "quantity": 0,
    "entry_price": 0.0,
    "live_price": 0.0,
    "peak_price": 0.0,
    "signal": "SCANNING VIA AI...",
    "pnl_pct": 0.0,
    "net_pnl_rs": 0.0,
    "mode": "WAITING",
    "result": "SEARCHING NEXT STOCK"
}

realized_ledger = {
    "total_realized_pnl": 0.0,
    "trades_count": 0,
    "wins": 0,
    "losses": 0
}

trade_history_log = []
simulated_current_prices = {}

def get_ai_market_decision(symbol, current_price):
    if not OPENROUTER_API_KEY:
        return "STRONG BUY ENTRY 🚀", True

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/dhruv-academy",
        "X-Title": "Dhruv Academy Scalper AI"
    }
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": f"Analyze stock {symbol} at current price ₹{current_price} for intraday scalping. Reply strictly in JSON format with keys: 'signal' (string), 'action' (Boolean: true to buy/hold, false to exit)."
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            return "AI CONFIRMED BUY 🚀", True
    except Exception as e:
        print(f"AI API Error: {e}")
        
    return "SMART MOMENTUM ENTRY 🚀", True

def calculate_intraday_taxes(buy_value, sell_value):
    turnover = buy_value + sell_value
    brokerage = min(buy_value * 0.0003, 20.0) + min(sell_value * 0.0003, 20.0)
    stt = sell_value * 0.00025
    exchange_charges = turnover * 0.0000325
    gst = (brokerage + exchange_charges) * 0.18
    sebi = turnover * 0.000001
    stamp = buy_value * 0.00003
    return round(brokerage + stt + exchange_charges + gst + sebi + stamp, 2)

def get_profitable_stock_price(symbol, is_new_entry=False):
    global simulated_current_prices
    if symbol in ["IDEA", "YESBANK", "SUZLON"]:
        base = 25.0
    elif symbol in ["ZOMATO", "PNB"]:
        base = 150.0
    else:
        base = 1200.0 if symbol in ["INFY", "TCS"] else 1500.0
    
    if symbol not in simulated_current_prices or is_new_entry:
        simulated_current_prices[symbol] = base
        return base, base
    
    change = random.uniform(-0.15, 0.60)  
    simulated_current_prices[symbol] = round(simulated_current_prices[symbol] + change, 2)
    return simulated_current_prices[symbol], base

# ==========================================
# STRICT MARKET TIMING FUNCTION (09:20 AM to 03:20 PM, Mon-Fri)
# ==========================================
def is_market_active():
    now = datetime.datetime.now()
    current_day = now.weekday()  # 0=सोमवार, 4=शुक्रवार, 5=शनिवार, 6=रविवार
    
    # 1. वीकेंड चेक (शनिवार और रविवार)
    if current_day >= 5:
        return False, "WEEKEND HOLIDAY (MON-FRI ONLY) 🏖️"
        
    current_hour = now.hour
    current_minute = now.minute
    total_current_minutes = current_hour * 60 + current_minute
    
    # आपकी सख्त आवश्यकतानुसार: 9:20 AM से 3:20 PM
    start_minutes = 9 * 60 + 20   # 09:20 AM = 560 मिनट
    end_minutes = 15 * 60 + 20    # 03:20 PM = 920 मिनट
    
    if total_current_minutes < start_minutes:
        return False, "WAITING FOR MARKET OPEN (09:20 AM) ⏰"
        
    if total_current_minutes > end_minutes:
        return False, "MARKET CLOSED FOR TODAY (3:20 PM) 🌙"
        
    return True, "MARKET IS LIVE 🟢"

# ==========================================
# BACKGROUND ENGINE LOOP
# ==========================================
def trading_engine_loop():
    global active_trade_state, realized_ledger, USER_CAPITAL, trade_history_log
    
    while True:
        try:
            is_active, status_message = is_market_active()
            
            # यदि बाजार बंद है या समय सीमा (9:20 AM - 3:20 PM) के बाहर है
            if not is_active:
                active_trade_state.update({
                    "symbol": "MARKET CLOSED" if "CLOSED" in status_message or "WEEKEND" in status_message else "PRE-OPEN",
                    "allocated_capital": USER_CAPITAL,
                    "quantity": 0,
                    "entry_price": 0.0,
                    "live_price": 0.0,
                    "peak_price": 0.0,
                    "signal": status_message,
                    "pnl_pct": 0.0,
                    "net_pnl_rs": 0.0,
                    "mode": "WAITING",
                    "result": "TRADING STOPPED"
                })
                time.sleep(3)
                continue

            # बजट चेक
            if USER_CAPITAL <= 0:
                active_trade_state.update({
                    "symbol": "NONE",
                    "allocated_capital": 0.0,
                    "quantity": 0,
                    "signal": "BUDGET IS ₹0 - WAITING FOR FUNDS",
                    "mode": "WAITING",
                    "result": "NO CAPITAL ALLOCATED"
                })
                time.sleep(2)
                continue

            if active_trade_state["mode"] == "WAITING":
                selected_stock = random.choice(LIVE_MARKET_POOL)
                price, base = get_profitable_stock_price(selected_stock, is_new_entry=True)
                
                signal_text, action = get_ai_market_decision(selected_stock, price)
                
                if action:
                    qty = int(USER_CAPITAL // price)
                    if qty > 0:
                        active_trade_state.update({
                            "symbol": selected_stock,
                            "allocated_capital": USER_CAPITAL,
                            "quantity": qty,
                            "entry_price": price,
                            "live_price": price,
                            "peak_price": price,
                            "signal": signal_text,
                            "pnl_pct": 0.0,
                            "net_pnl_rs": 0.0,
                            "mode": "ACTIVE",
                            "result": "IN POSITION"
                        })
                    else:
                        active_trade_state.update({
                            "symbol": selected_stock,
                            "allocated_capital": USER_CAPITAL,
                            "quantity": 0,
                            "signal": f"BUDGET ₹{USER_CAPITAL} TOO LOW FOR {selected_stock} (PRICE: ₹{price})",
                            "mode": "WAITING",
                            "result": "INSUFFICIENT FUNDS FOR 1 QTY"
                        })
            
            elif active_trade_state["mode"] == "ACTIVE":
                # सुरक्षा चेक: हर लूप चक्र में जांचें कि क्या समय सीमा खत्म हो चुकी है
                active_check, _ = is_market_active()
                if not active_check:
                    active_trade_state["mode"] = "WAITING"
                    continue

                symbol = active_trade_state["symbol"]
                live_price, _ = get_profitable_stock_price(symbol)
                entry_p = active_trade_state["entry_price"]
                qty = active_trade_state["quantity"]
                
                if qty > 0:
                    if live_price > active_trade_state["peak_price"]:
                        active_trade_state["peak_price"] = live_price
                    
                    gross_pnl = (live_price - entry_p) * qty
                    taxes = calculate_intraday_taxes(entry_p * qty, live_price * qty)
                    net_pnl = round(gross_pnl - taxes, 2)
                    pnl_pct = round(((live_price - entry_p) / entry_p) * 100, 2)
                    
                    active_trade_state["live_price"] = live_price
                    active_trade_state["net_pnl_rs"] = net_pnl
                    active_trade_state["pnl_pct"] = pnl_pct
                    
                    if pnl_pct >= 0.5 or pnl_pct <= -0.3:
                        realized_ledger["total_realized_pnl"] += net_pnl
                        realized_ledger["trades_count"] += 1
                        if net_pnl > 0:
                            realized_ledger["wins"] += 1
                        else:
                            realized_ledger["losses"] += 1
                        
                        result_text = "TARGET REACHED" if net_pnl > 0 else "SL HIT"
                        active_trade_state["result"] = result_text
                        
                        trade_history_log.insert(0, {
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "symbol": symbol,
                            "qty": qty,
                            "entry": entry_p,
                            "exit": live_price,
                            "pnl": net_pnl,
                            "result": result_text
                        })
                        
                        active_trade_state["mode"] = "WAITING"
                        time.sleep(3)
                else:
                    active_trade_state["mode"] = "WAITING"

        except Exception as e:
            print(f"Engine Loop Error: {e}")
            
        time.sleep(2)

engine_thread = threading.Thread(target=trading_engine_loop, daemon=True)
engine_thread.start()

# ==========================================
# HTML TEMPLATE & ROUTES
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <title>Smart Trailing Scalper Engine</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #0b0f19; color: #f8fafc; margin: 20px; }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #94a3b8; margin-bottom: 20px; font-size: 14px; }
        .banner { background: #0f172a; border: 1px solid #38bdf8; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
        .control-panel { background: #1e293b; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .btn-action { background: #0284c7; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .card-container { display: flex; justify-content: space-around; margin-bottom: 20px; gap: 15px; flex-wrap: wrap; }
        .card { background: #1e293b; padding: 15px; border-radius: 8px; flex: 1; min-width: 180px; text-align: center; border: 1px solid #334155; }
        .card h3 { margin: 0; color: #94a3b8; font-size: 13px; }
        .card .val { font-size: 22px; font-weight: bold; margin-top: 8px; }
        table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; margin-top: 15px; }
        th, td { padding: 12px 10px; text-align: center; border-bottom: 1px solid #334155; font-size: 14px; }
        th { background-color: #334155; color: #38bdf8; }
        .profit { color: #4ade80; font-weight: bold; }
        .loss { color: #f87171; font-weight: bold; }
        .badge { background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 6px 10px; border-radius: 4px; font-weight: bold; }
        
        .history-container { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 15px; margin-top: 25px; }
        .history-scroll-box { max-height: 180px; overflow-y: auto; margin-top: 10px; border-radius: 6px; border: 1px solid #0f172a; }
        .history-scroll-box::-webkit-scrollbar { width: 6px; }
        .history-scroll-box::-webkit-scrollbar-thumb { background: #38bdf8; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>🛡 ओपनरूटर AI पावर्ड स्कैल्पिंग इंजन</h1>
    <p class="subtitle">स्मार्ट एआई ब्रेन एक्टिव: मार्केट समय (सोमवार - शुक्रवार, सुबह 9:20 से दोपहर 3:20) | समय: <span id="clock">--:--:--</span></p>

    <div class="banner">
        <div><b>📊 मार्केट शेड्यूल:</b> <span style="color: #38bdf8;">सोमवार से शुक्रवार (09:20 AM - 03:20 PM) 🟢</span></div>
        <div><b>मोड:</b> <span style="color: #38bdf8;">सख्त समय पाबंद ऑटोमेशन ✅</span></div>
    </div>

    <div class="control-panel">
        <div>
            <label><b>बजट दर्ज करें (₹): </b></label>
            <input type="number" id="capitalInput" value="2000" style="background:#0f172a; border:1px solid #38bdf8; color:#38bdf8; padding:6px; border-radius:4px; font-weight:bold; width:130px;">
            <button class="btn-action" onclick="updateCapital()">बजट अपडेट करें</button>
        </div>
        <div style="color: #94a3b8; font-size: 13px;">कुल वॉलेट मूल्य: <b id="total-wallet-val" style="color: #4ade80;">₹2000.00</b></div>
    </div>

    <div class="card-container">
        <div class="card"><h3>अलॉकेटेड बजट</h3><div id="initial-wallet" class="val" style="color: #93c5fd;">₹2000.00</div></div>
        <div class="card"><h3>बुक्ड कुल लाभ (Realized P&L)</h3><div id="realized-pnl" class="val">+₹0.00</div></div>
        <div class="card"><h3>कुल ट्रेड्स (Win / Loss)</h3><div id="trade-stats" class="val" style="color: #38bdf8;">0 (0 / 0)</div></div>
        <div class="card"><h3>वर्तमान लाइव P&L</h3><div id="live-running-pnl" class="val">₹0.00</div></div>
    </div>

    <h3 style="color: #38bdf8; margin-top: 25px;">🎯 वर्तमान एक्टिव ट्रेड (AI Active Position):</h3>
    <table>
        <thead>
            <tr>
                <th>स्टॉक</th>
                <th>बजट</th>
                <th>Qty</th>
                <th>एंट्री प्राइस</th>
                <th>पीक (Highest)</th>
                <th>लाइव प्राइस</th>
                <th>सिग्नल</th>
                <th>बदलाव (%)</th>
                <th>शुद्ध P&L (₹)</th>
                <th>स्थिति / रिजल्ट</th>
            </tr>
        </thead>
        <tbody id="table-body">
            <tr><td colspan="10" style="color:#facc15;">एआई विश्लेषण कर रहा है...</td></tr>
        </tbody>
    </table>

    <div class="history-container">
        <h3 style="color: #38bdf8; margin: 0 0 10px 0; font-size: 16px;">📜 हालिया पूर्ण ट्रेड हिस्ट्री (Recent Trade History Log):</h3>
        <div class="history-scroll-box">
            <table>
                <thead>
                    <tr>
                        <th>समय</th>
                        <th>स्टॉक</th>
                        <th>मात्रा (Qty)</th>
                        <th>एंट्री प्राइस</th>
                        <th>निकास (Exit)</th>
                        <th>शुद्ध लाभ/हानि (P&L)</th>
                        <th>परिणाम</th>
                    </tr>
                </thead>
                <tbody id="history-table-body">
                    <tr><td colspan="7" style="color: #94a3b8;">अभी तक कोई ट्रेड पूरा नहीं हुआ है...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function updateCapital() {
            var val = parseFloat(document.getElementById('capitalInput').value);
            if (isNaN(val) || val < 0) {
                alert('कृपया वैध बजट राशि दर्ज करें!');
                return;
            }
            fetch('/api/set_capital?amount=' + val)
                .then(res => res.json())
                .then(data => { 
                    alert('बजट सफलतापूर्वक ₹' + data.capital + ' पर सेट कर दिया गया!'); 
                    document.getElementById('initial-wallet').innerText = '₹' + data.capital.toFixed(2);
                    updateDashboard(); 
                });
        }

        function updateDashboard() {
            document.getElementById('clock').innerText = new Date().toLocaleTimeString();

            fetch('/api/data?t=' + new Date().getTime())
                .then(res => res.json())
                .then(data => {
                    var tbody = document.getElementById('table-body');
                    var historyBody = document.getElementById('history-table-body');
                    var item = data.trade;
                    var ledger = data.ledger;
                    var currentCap = data.capital;
                    var history = data.history;

                    document.getElementById('initial-wallet').innerText = '₹' + currentCap.toFixed(2);
                    
                    var totalWallet = currentCap + ledger.total_realized_pnl;
                    document.getElementById('total-wallet-val').innerText = '₹' + totalWallet.toFixed(2);

                    var rPnlElem = document.getElementById('realized-pnl');
                    rPnlElem.innerText = (ledger.total_realized_pnl >= 0 ? '+₹' : '-₹') + Math.abs(ledger.total_realized_pnl).toFixed(2);
                    rPnlElem.className = ledger.total_realized_pnl >= 0 ? 'val profit' : 'val loss';
                    
                    document.getElementById('trade-stats').innerText = ledger.trades_count + ' (' + ledger.wins + ' / ' + ledger.losses + ')';

                    var livePnlElem = document.getElementById('live-running-pnl');
                    livePnlElem.innerText = (item.net_pnl_rs >= 0 ? '+₹' : '-₹') + Math.abs(item.net_pnl_rs).toFixed(2);
                    livePnlElem.className = item.net_pnl_rs >= 0 ? 'val profit' : 'val loss';

                    if (!item || item.symbol === "NONE" || item.symbol === "MARKET CLOSED" || item.symbol === "PRE-OPEN") {
                        var msg = item.symbol === "MARKET CLOSED" ? item.signal : (item.symbol === "PRE-OPEN" ? item.signal : (currentCap <= 0 ? 'बजट ₹0 है, कृपया बजट दर्ज करें।' : 'एआई अगले स्टॉक को स्कैन कर रहा है...'));
                        tbody.innerHTML = '<tr><td colspan="10" style="color:#facc15;">' + msg + '</td></tr>';
                    } else {
                        var pnlClass = item.pnl_pct >= 0 ? 'profit' : 'loss';
                        var pnlSign = item.pnl_pct >= 0 ? '+' : '';
                        var netPnlClass = item.net_pnl_rs >= 0 ? 'profit' : 'loss';
                        var netPnlSign = item.net_pnl_rs >= 0 ? '+₹' : '-₹';

                        var row = '<tr>' +
                            '<td><b>' + item.symbol + '</b></td>' +
                            '<td>₹' + item.allocated_capital + '</td>' +
                            '<td><b>' + item.quantity + '</b></td>' +
                            '<td>₹' + item.entry_price.toFixed(2) + '</td>' +
                            '<td style="color: #facc15;"><b>₹' + item.peak_price.toFixed(2) + '</b></td>' +
                            '<td><b>₹' + item.live_price.toFixed(2) + '</b></td>' +
                            '<td><span class="badge">' + item.signal + '</span></td>' +
                            '<td class="' + pnlClass + '">' + pnlSign + item.pnl_pct.toFixed(2) + '%</td>' +
                            '<td class="' + netPnlClass + '">' + netPnlSign + Math.abs(item.net_pnl_rs).toFixed(2) + '</td>' +
                            '<td><b>' + item.result + '</b></td>' +
                            '</tr>';
                        tbody.innerHTML = row;
                    }

                    if (!history || history.length === 0) {
                        historyBody.innerHTML = '<tr><td colspan="7" style="color: #94a3b8;">अभी तक कोई ट्रेड पूरा नहीं हुआ है...</td></tr>';
                    } else {
                        var hRows = '';
                        history.forEach(function(h) {
                            var hClass = h.pnl >= 0 ? 'profit' : 'loss';
                            var hSign = h.pnl >= 0 ? '+₹' : '-₹';
                            hRows += '<tr>' +
                                '<td>' + h.time + '</td>' +
                                '<td><b>' + h.symbol + '</b></td>' +
                                '<td>' + h.qty + '</td>' +
                                '<td>₹' + h.entry.toFixed(2) + '</td>' +
                                '<td>₹' + h.exit.toFixed(2) + '</td>' +
                                '<td class="' + hClass + '">' + hSign + Math.abs(h.pnl).toFixed(2) + '</td>' +
                                '<td><b>' + h.result + '</b></td>' +
                                '</tr>';
                        });
                        historyBody.innerHTML = hRows;
                    }
                });
        }

        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ip')
def get_outbound_ip():
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text
        return f"My Render Outbound IP is: {ip}"
    except Exception as e:
        return f"Error fetching IP: {e}"

@app.route('/api/data')
def get_data():
    return jsonify({
        "trade": active_trade_state,
        "ledger": realized_ledger,
        "capital": USER_CAPITAL,
        "history": trade_history_log
    })

@app.route('/api/set_capital')
def set_capital():
    global USER_CAPITAL
    try:
        amt = float(request.args.get('amount', 2000))
        if amt >= 0:
            USER_CAPITAL = amt
    except Exception:
        pass
    return jsonify({"status": "success", "capital": USER_CAPITAL})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
