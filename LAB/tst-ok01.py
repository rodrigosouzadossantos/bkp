#import petrobras

#for i in range(1, 19):
#    petrobras.run(f"Petro #{i:02d}")





import time
from rich.live import Live
from rich.table import Table
from rich.console import Console

console = Console()

# The table will be the live-updating element at the bottom
table = Table(title="Live Progress", border_style="blue")
table.add_column("Row ID")
table.add_column("Description")
table.add_column("Status")

# Use a 'with Live(...)' context manager to manage the live display area
# redirect_stdout is True by default, allowing standard print() to work as well
with Live(table, refresh_per_second=4, console=console) as live:
    # Use live.console.print() for standard, non-live scrolling output
    live.console.print("[bold green]Starting work on all rows...[/bold green]") #

    for row_id in range(12):
        # This output scrolls up in the console history
        live.console.print(f"Working on row #{row_id}...")

        # Update the live table at the bottom of the screen
        status_text = "[yellow]Processing[/yellow]" if row_id < 11 else "[green]Done[/green]"
        table.add_row(f"{row_id}", f"description {row_id}", status_text)

        # The Live context automatically refreshes the display
        time.sleep(0.4)

    live.console.print("[bold green]Finished processing![/bold green]")
