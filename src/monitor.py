import time
from pathlib import Path
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich.live import Live
from .config import Config, VERSION
from .scanner import ProjectScanner

COST_PER_M_TOKENS = 3.0
SCAN_INTERVAL_SECONDS = 30

class Monitor:
    def __init__(self, root: Path):
        self.root = root
        self.scanner = ProjectScanner(root)
        self.cfg = Config.get()

    def _generate_layout(self) -> Layout:
        stats = self.scanner.get_stats()
        layout = Layout()
        layout.split(Layout(name="header", size=3), Layout(name="body", ratio=1))
        layout["body"].split_row(Layout(name="stats", ratio=1), Layout(name="info", ratio=1))

        layout["header"].update(
            Panel(f"👻 [bold]Ghost Protocol v{VERSION}[/bold] | Status: [bold green]ACTIVE[/bold green]", style="white on blue")
        )

        table = Table(box=None, expand=True, show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold green")
        
        tokens = stats.get('total_tokens', 0)
        table.add_row("Total Tokens", f"{tokens:,}")
        table.add_row("Files Tracked", str(stats.get('files_count', 0)))
        table.add_row("Est. Cost ($3/M)", f"${(tokens / 1_000_000) * COST_PER_M_TOKENS:.4f}")
        
        layout["stats"].update(Panel(table, title="📊 Project Stats"))

        info_text = (
            "[bold cyan]System Status:[/bold cyan]\n"
            "• Writer: IgnoreManager (DRY)\n"
            "• Scanner: Auto-updating (30s)\n"
            "• Config: Cached & Valid\n\n"
            "[dim]Press Ctrl+C to exit.[/dim]"
        )
        layout["info"].update(Panel(info_text, title="🧠 The Brain"))
        return layout

    def start(self):
        console = Console()
        
        # Initial scan on startup to ensure we have data
        self.scanner.scan_full_project()
        
        with Live(self._generate_layout(), console=console, refresh_per_second=1) as live:
            last_scan = time.time()
            try:
                while True:
                    now = time.time()
                    if now - last_scan > SCAN_INTERVAL_SECONDS:
                        self.scanner.scan_full_project()
                        last_scan = now
                    
                    live.update(self._generate_layout())
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Ghost monitor paused.[/yellow]")