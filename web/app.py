import sys
import os
import threading
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

from config import ANTHROPIC_API_KEY
from broker import AlpacaBroker
from agents.orchestrator import run_orchestrator
import anthropic

app = Flask(__name__)
broker = AlpacaBroker(paper=True)

bot_running = False
bot_log = []

HISTORY_FILE = Path(__file__).parent / "history.json"
portfolio_history = (
    json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else []
)

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "minimadoff")


def _save_history():
    HISTORY_FILE.write_text(json.dumps(portfolio_history[-500:]))


def _log(msg: str):
    bot_log.append({"t": datetime.now().strftime("%H:%M:%S"), "m": msg})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/portfolio")
def api_portfolio():
    try:
        acct = broker.get_account_info()
        positions = broker.get_positions()
        portfolio_history.append({
            "t": datetime.now().strftime("%H:%M"),
            "v": round(acct["portfolio_value"], 2),
        })
        _save_history()
        return jsonify({
            "account": acct,
            "positions": positions,
            "history": portfolio_history[-60:],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/log")
def api_log():
    since = int(request.args.get("since", 0))
    return jsonify({
        "messages": bot_log[since:],
        "total": len(bot_log),
        "running": bot_running,
    })


@app.route("/api/run", methods=["POST"])
def api_run():
    global bot_running
    data = request.get_json() or {}

    if data.get("password") != DASHBOARD_PASSWORD:
        return jsonify({"error": "Wrong password"}), 401
    if bot_running:
        return jsonify({"error": "Bot already running"}), 409

    dry_run = bool(data.get("dry_run", True))

    def _run():
        global bot_running
        bot_running = True
        mode = "DRY RUN" if dry_run else "PAPER TRADE"
        _log(f"{mode} session starting...")

        class Cap:
            def write(self, t):
                if t and t.strip():
                    _log(t.strip())
            def flush(self): pass

        orig = sys.stdout
        sys.stdout = Cap()
        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            run_orchestrator(broker, client, dry_run=dry_run)
        except Exception as e:
            _log(f"Error: {e}")
        finally:
            sys.stdout = orig
            bot_running = False
            _log("Session complete.")

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n  Mini Madoff Web Dashboard")
    print(f"  Open http://localhost:{port} in your browser\n")
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)
