"""Mini Madoff -- AI Trading Dashboard"""

import sys
import io
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Button, RichLog, Static
from textual.containers import Horizontal
from textual import work

import anthropic
from config import ANTHROPIC_API_KEY
from broker import AlpacaBroker
from agents.orchestrator import run_orchestrator

TCSS = """
Screen {
    background: #0a0a0a;
    layout: vertical;
}

/* Header */
#app-header {
    height: 9;
    background: #0d0900;
    color: #FFB300;
    text-style: bold;
    text-align: center;
    content-align: center middle;
    border-bottom: heavy #FFB300;
    padding: 1 0;
}

/* Stat cards */
#stats-bar {
    height: 5;
    layout: horizontal;
    background: #0d0d0d;
    border-bottom: solid #1e1e1e;
}

.stat-box {
    width: 1fr;
    height: 5;
    border-right: solid #1e1e1e;
    content-align: center middle;
    padding: 0 2;
}

/* Section labels */
.section-label {
    height: 1;
    padding: 0 2;
    text-style: bold;
}

#positions-label {
    background: #110e00;
    color: #FFB300;
}

#log-label {
    background: #001100;
    color: #00cc66;
}

/* Positions table */
DataTable {
    height: 1fr;
    background: #0a0a0a;
    border: none;
    border-bottom: solid #1e1e1e;
}

DataTable > .datatable--header {
    background: #111111;
    color: #FFB300;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #1a1400;
    color: white;
}

DataTable > .datatable--odd-row {
    background: #0d0d0d;
}

DataTable > .datatable--even-row {
    background: #0a0a0a;
}

/* Bot log */
RichLog {
    height: 8;
    background: #080808;
    padding: 0 1;
    border-bottom: solid #1e1e1e;
    color: #999999;
}

/* Button bar */
#button-bar {
    height: 6;
    layout: horizontal;
    align: center middle;
    background: #0d0d0d;
    border-top: solid #2a2a2a;
    padding: 0 4;
}

Button {
    margin: 0 2;
    min-width: 22;
    height: 4;
    text-style: bold;
    border: outer white;
}

#btn-run {
    background: #004d00;
    color: #ccffcc;
    border: outer #00cc55;
}
#btn-run:hover    { background: #006600; color: white; }
#btn-run:focus    { background: #006600; }
#btn-run:disabled { background: #1a1a1a; color: #444444; border: outer #2a2a2a; }

#btn-dry {
    background: #002255;
    color: #cce0ff;
    border: outer #3399ff;
}
#btn-dry:hover    { background: #003377; color: white; }
#btn-dry:focus    { background: #003377; }
#btn-dry:disabled { background: #1a1a1a; color: #444444; border: outer #2a2a2a; }

#btn-refresh {
    background: #2a1c00;
    color: #fff0cc;
    border: outer #FFB300;
}
#btn-refresh:hover { background: #3d2800; color: white; }
#btn-refresh:focus { background: #3d2800; }

#btn-quit {
    background: #3d0000;
    color: #ffcccc;
    border: outer #ff3333;
}
#btn-quit:hover { background: #550000; color: white; }
#btn-quit:focus { background: #550000; }
"""


class MiniMadoff(App):
    CSS = TCSS
    TITLE = "Mini Madoff"

    def compose(self) -> ComposeResult:
        yield Static(
            '==========================================================\n'
            '\n'
            'MINI MADOFF\n'
            '\n'
            '==========================================================\n'
            '\n'
            '[dim]AI-Powered Paper Trading System[/dim]',
            id="app-header",
        )

        with Horizontal(id="stats-bar"):
            yield Static("", id="stat-portfolio", classes="stat-box")
            yield Static("", id="stat-cash",      classes="stat-box")
            yield Static("", id="stat-invested",  classes="stat-box")
            yield Static("", id="stat-pl",        classes="stat-box")

        yield Static("  POSITIONS", id="positions-label", classes="section-label")
        yield DataTable(id="positions-table", cursor_type="row", zebra_stripes=True)

        yield Static("  BOT ACTIVITY", id="log-label", classes="section-label")
        yield RichLog(id="bot-log", highlight=True, markup=True, wrap=True)

        with Horizontal(id="button-bar"):
            yield Button("RUN BOT",  id="btn-run")
            yield Button("DRY RUN",  id="btn-dry")
            yield Button("REFRESH",  id="btn-refresh")
            yield Button("QUIT",     id="btn-quit")

    def on_mount(self) -> None:
        self.broker = AlpacaBroker(paper=True)
        self.bot_running = False

        table = self.query_one("#positions-table", DataTable)
        table.add_columns(
            "Symbol", "Qty", "Entry", "Current", "Mkt Value", "P&L $", "P&L %"
        )

        self.refresh_portfolio()
        self.add_log("Connected to Alpaca paper account.")

    # ── Data ──────────────────────────────────────────────────────────

    def refresh_portfolio(self) -> None:
        try:
            acct = broker_data = self.broker.get_account_info()
            positions = self.broker.get_positions()
            self._update_stats(acct, positions)
            self._update_table(positions)
        except Exception as e:
            self.add_log("[red]Refresh error: {}[/red]".format(e))

    def _update_stats(self, acct: dict, positions: list) -> None:
        pv       = acct["portfolio_value"]
        cash     = acct["cash"]
        invested = pv - cash
        total_pl = sum(p["unrealized_pl"] for p in positions)
        c = "green" if total_pl >= 0 else "red"
        s = "+" if total_pl >= 0 else ""

        self.query_one("#stat-portfolio", Static).update(
            "[dim]Portfolio Value[/dim]\n[bold white]${:,.2f}[/bold white]".format(pv)
        )
        self.query_one("#stat-cash", Static).update(
            "[dim]Cash[/dim]\n[bold cyan]${:,.2f}[/bold cyan]".format(cash)
        )
        self.query_one("#stat-invested", Static).update(
            "[dim]Invested[/dim]\n[bold magenta]${:,.2f}[/bold magenta]".format(invested)
        )
        self.query_one("#stat-pl", Static).update(
            "[dim]Unrealized P&L[/dim]\n[bold {c}]{s}${pl:,.2f}[/bold {c}]".format(
                c=c, s=s, pl=total_pl
            )
        )

    def _update_table(self, positions: list) -> None:
        table = self.query_one("#positions-table", DataTable)
        table.clear()
        if not positions:
            table.add_row("-", "-", "-", "-", "No open positions", "-", "-")
            return
        for p in positions:
            pl  = p["unrealized_pl"]
            pct = p["unrealized_plpc"] * 100
            c   = "green" if pl >= 0 else "red"
            s   = "+" if pl >= 0 else ""
            table.add_row(
                p["symbol"],
                str(int(float(p["qty"]))),
                "${:.2f}".format(p["avg_entry_price"]),
                "${:.2f}".format(p["current_price"]),
                "${:,.2f}".format(p["market_value"]),
                "[{c}]{s}${pl:,.2f}[/{c}]".format(c=c, s=s, pl=pl),
                "[{c}]{s}{pct:.2f}%[/{c}]".format(c=c, s=s, pct=pct),
            )

    # ── Logging ───────────────────────────────────────────────────────

    def add_log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#bot-log", RichLog).write(
            "[dim]{}[/dim]  {}".format(ts, msg)
        )

    # ── Buttons ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "btn-quit":
            self.exit()
        elif bid == "btn-refresh":
            self.refresh_portfolio()
            self.add_log("[yellow]Portfolio refreshed.[/yellow]")
        elif bid == "btn-run" and not self.bot_running:
            self._start_bot(dry=False)
        elif bid == "btn-dry" and not self.bot_running:
            self._start_bot(dry=True)
        elif self.bot_running:
            self.add_log("[dim]Bot is already running...[/dim]")

    # ── Bot worker ────────────────────────────────────────────────────

    def _set_buttons_disabled(self, state: bool) -> None:
        self.query_one("#btn-run", Button).disabled = state
        self.query_one("#btn-dry", Button).disabled = state

    @work(thread=True)
    def _start_bot(self, dry: bool) -> None:
        self.bot_running = True
        mode = "DRY RUN" if dry else "PAPER TRADE"
        self.call_from_thread(
            self.add_log, "[yellow]{} session starting...[/yellow]".format(mode)
        )
        self.call_from_thread(self._set_buttons_disabled, True)

        outer = self

        class UILogger:
            def write(self, text):
                if text and text.strip():
                    outer.call_from_thread(outer.add_log, text.strip())
            def flush(self):
                pass

        original = sys.stdout
        sys.stdout = UILogger()
        try:
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            run_orchestrator(self.broker, client, dry_run=dry)
        except Exception as e:
            self.call_from_thread(self.add_log, "[red]Error: {}[/red]".format(e))
        finally:
            sys.stdout = original
            self.bot_running = False
            self.call_from_thread(
                self.add_log, "[green]Session complete.[/green]"
            )
            self.call_from_thread(self.refresh_portfolio)
            self.call_from_thread(self._set_buttons_disabled, False)


if __name__ == "__main__":
    app = MiniMadoff()
    app.run()
