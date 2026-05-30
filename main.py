import argparse
import sys
import io
import anthropic

# Force UTF-8 output so emoji in agent summaries don't crash on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from config import ANTHROPIC_API_KEY, ALPACA_API_KEY, ALPACA_SECRET_KEY
from broker import AlpacaBroker
from agents.orchestrator import run_orchestrator


def main():
    parser = argparse.ArgumentParser(description="Multi-agent AI trading bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and plan trades but do not submit any orders",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live trading (default is paper trading)",
    )
    args = parser.parse_args()

    # Validate credentials
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not ALPACA_API_KEY:
        missing.append("ALPACA_API_KEY")
    if not ALPACA_SECRET_KEY:
        missing.append("ALPACA_SECRET_KEY")
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)

    if args.live:
        confirm = input("WARNING: Live trading mode. Type 'yes' to confirm: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    paper = not args.live
    broker = AlpacaBroker(paper=paper)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    run_orchestrator(broker, client, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
