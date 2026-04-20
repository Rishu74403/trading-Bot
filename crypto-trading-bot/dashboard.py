#!/usr/bin/env python3
"""
Crypto Trading Bot — Web Dashboard
====================================
Flask-based dashboard to visualize backtest results.
Run: python dashboard.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template_string, jsonify, request
from config import load_config, get_strategy_params
from bot.data_fetcher import create_exchange, fetch_ohlcv
from bot.strategies import get_strategy, list_strategies
from bot.backtester import Backtester, compare_strategies
from utils.logger import get_logger

logger = get_logger(__name__)
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CryptoBot Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0a0e17; --surface: #111827; --card: #1a2332;
            --border: #1e293b; --text: #e2e8f0; --dim: #64748b;
            --cyan: #22d3ee; --green: #34d399; --red: #f87171;
            --purple: #a78bfa; --orange: #fbbf24; --blue: #60a5fa;
        }
        body {
            font-family: 'Inter', sans-serif; background: var(--bg);
            color: var(--text); min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            border-bottom: 1px solid var(--border); padding: 20px 40px;
            display: flex; align-items: center; gap: 16px;
        }
        .header h1 {
            font-size: 24px; font-weight: 700;
            background: linear-gradient(90deg, var(--cyan), var(--purple));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .header .badge {
            background: rgba(34,211,238,0.15); color: var(--cyan);
            padding: 4px 12px; border-radius: 20px; font-size: 12px;
            font-weight: 500;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
        .controls {
            display: flex; gap: 12px; flex-wrap: wrap;
            background: var(--surface); padding: 20px; border-radius: 12px;
            border: 1px solid var(--border); margin-bottom: 24px;
        }
        .controls select, .controls input, .controls button {
            font-family: 'Inter', sans-serif; font-size: 14px;
            padding: 10px 16px; border-radius: 8px; border: 1px solid var(--border);
            background: var(--card); color: var(--text); outline: none;
        }
        .controls select:focus, .controls input:focus {
            border-color: var(--cyan); box-shadow: 0 0 0 2px rgba(34,211,238,0.2);
        }
        .controls button {
            background: linear-gradient(135deg, #06b6d4, #8b5cf6);
            border: none; font-weight: 600; cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .controls button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 20px rgba(34,211,238,0.3);
        }
        .controls button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .controls label { color: var(--dim); font-size: 12px; font-weight: 500; }
        .control-group { display: flex; flex-direction: column; gap: 4px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .metric-card {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 20px; text-align: center;
            transition: border-color 0.2s;
        }
        .metric-card:hover { border-color: var(--cyan); }
        .metric-card .value { font-size: 28px; font-weight: 700; margin: 8px 0; }
        .metric-card .label { font-size: 12px; color: var(--dim); text-transform: uppercase; letter-spacing: 1px; }
        .positive { color: var(--green); }
        .negative { color: var(--red); }
        .chart-container {
            background: var(--card); border: 1px solid var(--border);
            border-radius: 12px; padding: 24px; margin-bottom: 24px;
        }
        .chart-container h3 {
            font-size: 16px; font-weight: 600; margin-bottom: 16px;
            color: var(--dim);
        }
        .chart-wrapper { position: relative; height: 350px; }
        .trades-table {
            width: 100%; border-collapse: collapse;
            background: var(--card); border-radius: 12px; overflow: hidden;
        }
        .trades-table th {
            background: var(--surface); padding: 12px 16px;
            text-align: left; font-size: 12px; color: var(--dim);
            text-transform: uppercase; letter-spacing: 1px;
            border-bottom: 1px solid var(--border);
        }
        .trades-table td {
            padding: 10px 16px; border-bottom: 1px solid var(--border);
            font-size: 13px; font-variant-numeric: tabular-nums;
        }
        .spinner { display: none; }
        .spinner.active { display: inline-block; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status { padding: 10px; text-align: center; color: var(--dim); }
    </style>
</head>
<body>
    <div class="header">
        <h1>⟠ CryptoBot Dashboard</h1>
        <span class="badge">v1.0.0</span>
    </div>
    <div class="container">
        <div class="controls">
            <div class="control-group">
                <label>Strategy</label>
                <select id="strategy">
                    {% for s in strategies %}<option value="{{ s }}">{{ s.replace('_',' ').title() }}</option>{% endfor %}
                </select>
            </div>
            <div class="control-group">
                <label>Pair</label>
                <input id="pair" value="BTC/USDT" style="width:120px">
            </div>
            <div class="control-group">
                <label>Timeframe</label>
                <select id="timeframe">
                    <option value="1h" selected>1h</option>
                    <option value="15m">15m</option>
                    <option value="4h">4h</option>
                    <option value="1d">1d</option>
                </select>
            </div>
            <div class="control-group">
                <label>Candles</label>
                <input id="limit" type="number" value="500" style="width:90px">
            </div>
            <div class="control-group" style="justify-content:flex-end">
                <button onclick="runBacktest()" id="runBtn">
                    <span class="spinner" id="spinner">⟳</span> Run Backtest
                </button>
            </div>
            <div class="control-group" style="justify-content:flex-end">
                <button onclick="runCompare()" id="cmpBtn" style="background:linear-gradient(135deg,#8b5cf6,#ec4899)">
                    Compare All
                </button>
            </div>
        </div>

        <div id="metrics" class="grid"></div>

        <div class="chart-container">
            <h3>Equity Curve</h3>
            <div class="chart-wrapper"><canvas id="equityChart"></canvas></div>
        </div>

        <div class="chart-container">
            <h3>Price & Signals</h3>
            <div class="chart-wrapper"><canvas id="priceChart"></canvas></div>
        </div>

        <div id="compareSection" style="display:none">
            <div class="chart-container">
                <h3>Strategy Comparison</h3>
                <div id="compareTable"></div>
            </div>
        </div>

        <div class="chart-container">
            <h3>Trade Log</h3>
            <div id="tradesSection"><p class="status">Run a backtest to see trades</p></div>
        </div>
    </div>

    <script>
        let equityChart = null, priceChart = null;

        async function runBacktest() {
            const btn = document.getElementById('runBtn');
            const spinner = document.getElementById('spinner');
            btn.disabled = true; spinner.classList.add('active');

            const params = new URLSearchParams({
                strategy: document.getElementById('strategy').value,
                pair: document.getElementById('pair').value,
                timeframe: document.getElementById('timeframe').value,
                limit: document.getElementById('limit').value,
            });

            try {
                const res = await fetch('/api/backtest?' + params);
                const data = await res.json();
                if (data.error) { alert(data.error); return; }
                renderMetrics(data.metrics);
                renderEquityChart(data.equity);
                renderPriceChart(data.signals);
                renderTrades(data.trades);
            } catch(e) { alert('Error: ' + e.message); }
            finally { btn.disabled = false; spinner.classList.remove('active'); }
        }

        async function runCompare() {
            const btn = document.getElementById('cmpBtn');
            btn.disabled = true;
            const params = new URLSearchParams({
                pair: document.getElementById('pair').value,
                timeframe: document.getElementById('timeframe').value,
                limit: document.getElementById('limit').value,
            });
            try {
                const res = await fetch('/api/compare?' + params);
                const data = await res.json();
                if (data.error) { alert(data.error); return; }
                renderCompare(data.results);
            } catch(e) { alert('Error: ' + e.message); }
            finally { btn.disabled = false; }
        }

        function renderMetrics(m) {
            const items = [
                { label: 'Total Return', value: m.total_return.toFixed(2)+'%', cls: m.total_return >= 0 ? 'positive' : 'negative' },
                { label: 'Sharpe Ratio', value: m.sharpe_ratio.toFixed(3), cls: m.sharpe_ratio >= 1 ? 'positive' : 'negative' },
                { label: 'Max Drawdown', value: m.max_drawdown.toFixed(2)+'%', cls: 'negative' },
                { label: 'Win Rate', value: m.win_rate.toFixed(1)+'%', cls: m.win_rate >= 50 ? 'positive' : 'negative' },
                { label: 'Total Trades', value: m.total_trades, cls: '' },
                { label: 'Profit Factor', value: m.profit_factor.toFixed(2), cls: m.profit_factor >= 1 ? 'positive' : 'negative' },
            ];
            document.getElementById('metrics').innerHTML = items.map(i =>
                `<div class="metric-card"><div class="label">${i.label}</div><div class="value ${i.cls}">${i.value}</div></div>`
            ).join('');
        }

        function renderEquityChart(eq) {
            if (equityChart) equityChart.destroy();
            const ctx = document.getElementById('equityChart').getContext('2d');
            equityChart = new Chart(ctx, {
                type: 'line',
                data: { labels: eq.map(e => e.t), datasets: [{
                    label: 'Equity', data: eq.map(e => e.v),
                    borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,0.1)',
                    fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2,
                }]},
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: { x: { type:'time', ticks:{color:'#64748b'}, grid:{color:'#1e293b'} },
                              y: { ticks:{color:'#64748b'}, grid:{color:'#1e293b'} } },
                    plugins: { legend: { labels: { color: '#e2e8f0' } } },
                }
            });
        }

        function renderPriceChart(signals) {
            if (priceChart) priceChart.destroy();
            const ctx = document.getElementById('priceChart').getContext('2d');
            const buys = signals.filter(s => s.sig === 1);
            const sells = signals.filter(s => s.sig === -1);
            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: signals.map(s => s.t),
                    datasets: [
                        { label:'Price', data: signals.map(s=>s.c), borderColor:'#60a5fa',
                          pointRadius:0, borderWidth:1.5, tension:0.1 },
                        { label:'Buy', data: buys.map(b=>({x:b.t,y:b.c})), type:'scatter',
                          backgroundColor:'#34d399', pointRadius:6, pointStyle:'triangle' },
                        { label:'Sell', data: sells.map(s=>({x:s.t,y:s.c})), type:'scatter',
                          backgroundColor:'#f87171', pointRadius:6, pointStyle:'triangle',
                          rotation: 180 },
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: { x: { type:'time', ticks:{color:'#64748b'}, grid:{color:'#1e293b'} },
                              y: { ticks:{color:'#64748b'}, grid:{color:'#1e293b'} } },
                    plugins: { legend: { labels: { color:'#e2e8f0' } } },
                }
            });
        }

        function renderTrades(trades) {
            if (!trades.length) { document.getElementById('tradesSection').innerHTML = '<p class="status">No trades</p>'; return; }
            let html = '<table class="trades-table"><thead><tr><th>#</th><th>Entry</th><th>Exit</th><th>Entry $</th><th>Exit $</th><th>P&L</th><th>Return</th></tr></thead><tbody>';
            trades.forEach((t, i) => {
                const cls = t.pnl >= 0 ? 'positive' : 'negative';
                html += `<tr><td>${i+1}</td><td>${t.entry.slice(0,19)}</td><td>${t.exit.slice(0,19)}</td><td>$${t.ep.toFixed(2)}</td><td>$${t.xp.toFixed(2)}</td><td class="${cls}">$${t.pnl.toFixed(2)}</td><td class="${cls}">${(t.ret*100).toFixed(2)}%</td></tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('tradesSection').innerHTML = html;
        }

        function renderCompare(results) {
            document.getElementById('compareSection').style.display = 'block';
            let html = '<table class="trades-table"><thead><tr><th>Rank</th><th>Strategy</th><th>Return</th><th>Sharpe</th><th>Max DD</th><th>Trades</th><th>Win Rate</th></tr></thead><tbody>';
            results.forEach((r, i) => {
                const cls = r.total_return >= 0 ? 'positive' : 'negative';
                html += `<tr><td>#${i+1}</td><td>${r.name}</td><td class="${cls}">${r.total_return.toFixed(2)}%</td><td>${r.sharpe.toFixed(3)}</td><td class="negative">${r.max_dd.toFixed(2)}%</td><td>${r.trades}</td><td>${r.win_rate.toFixed(1)}%</td></tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('compareTable').innerHTML = html;
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, strategies=list_strategies())


@app.route("/api/backtest")
def api_backtest():
    try:
        config = load_config()
        strategy_name = request.args.get("strategy", "sma_crossover")
        pair = request.args.get("pair", "BTC/USDT")
        timeframe = request.args.get("timeframe", "1h")
        limit = int(request.args.get("limit", 500))

        exchange = create_exchange(config.get("exchange", "binance"))
        params = get_strategy_params(config, strategy_name)
        strategy = get_strategy(strategy_name, params)
        df = fetch_ohlcv(exchange, pair, timeframe, limit=limit)

        if df.empty:
            return jsonify({"error": "No data returned"})

        bt = Backtester(strategy=strategy, df=df,
                        initial_capital=config.get("initial_capital", 10000),
                        fee_rate=config.get("fee_rate", 0.001),
                        symbol=pair, timeframe=timeframe)
        result = bt.run()

        eq_data = [{"t": str(r["timestamp"]), "v": round(r["equity"], 2)}
                   for _, r in result.equity_df.iterrows()]

        sig_data = []
        for _, r in result.signals_df.iterrows():
            ts = str(r.get("datetime", r.get("timestamp")))
            sig_data.append({"t": ts, "c": round(r["close"], 2),
                             "sig": int(r.get("signal", 0))})

        trades_data = []
        for _, r in result.trades_df.iterrows():
            trades_data.append({
                "entry": str(r["entry_time"]), "exit": str(r["exit_time"]),
                "ep": r["entry_price"], "xp": r["exit_price"],
                "pnl": round(r["pnl"], 2), "ret": round(r["return_pct"], 4),
            })

        return jsonify({
            "metrics": result.metrics,
            "equity": eq_data,
            "signals": sig_data,
            "trades": trades_data,
        })
    except Exception as e:
        logger.error(f"Backtest API error: {e}")
        return jsonify({"error": str(e)})


@app.route("/api/compare")
def api_compare():
    try:
        config = load_config()
        pair = request.args.get("pair", "BTC/USDT")
        timeframe = request.args.get("timeframe", "1h")
        limit = int(request.args.get("limit", 500))

        exchange = create_exchange(config.get("exchange", "binance"))
        df = fetch_ohlcv(exchange, pair, timeframe, limit=limit)

        if df.empty:
            return jsonify({"error": "No data returned"})

        strategies = []
        for name in list_strategies():
            params = get_strategy_params(config, name)
            strategies.append(get_strategy(name, params))

        results = compare_strategies(
            strategies, df,
            initial_capital=config.get("initial_capital", 10000),
            fee_rate=config.get("fee_rate", 0.001),
            symbol=pair, timeframe=timeframe)

        out = []
        for r in results:
            m = r.metrics
            out.append({
                "name": r.strategy_name,
                "total_return": m["total_return"],
                "sharpe": m["sharpe_ratio"],
                "max_dd": m["max_drawdown"],
                "trades": m["total_trades"],
                "win_rate": m["win_rate"],
            })

        return jsonify({"results": out})
    except Exception as e:
        logger.error(f"Compare API error: {e}")
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    config = load_config()
    dash = config.get("dashboard", {})
    app.run(
        host=dash.get("host", "127.0.0.1"),
        port=dash.get("port", 5000),
        debug=dash.get("debug", False),
    )
