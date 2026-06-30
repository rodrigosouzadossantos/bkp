#import petrobras

#for i in range(1, 19):
#    petrobras.run(f"Petro #{i:02d}")





import time
from collections import deque
from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, BarColumn, TimeElapsedColumn, SpinnerColumn, TextColumn

console = Console()

# Terminal output buffer (scrolling)
MAX_TERM_HEIGHT = 15  # fixed number of lines for terminal output
term_buffer = deque(maxlen=MAX_TERM_HEIGHT)

# Red box buffer for current step output
RED_BOX_HEIGHT = 5
current_step_lines = deque(maxlen=RED_BOX_HEIGHT)

# Progress bars
bar_items = ["Compile", "Simulate", "Generate Reports"]

step_prog = Progress(
    TimeElapsedColumn(),
    SpinnerColumn("dots"),
    TextColumn("Step {task.fields[step]}: [purple]{task.description}"),
)
step_id = step_prog.add_task("Starting", step=0)

all_prog = Progress(
    TimeElapsedColumn(),
    BarColumn(),
    TextColumn("{task.percentage:>3.0f}% ({task.completed}/{task.total})"),
    TextColumn("{task.description}"),
)
all_id = all_prog.add_task("Overall", total=len(bar_items))


def render_live():
    """Render terminal panel with fixed height + red box + progress bars"""
    term_panel = Panel(
        "\n".join(term_buffer),
        title="Terminal Output",
        border_style="white",
        height=MAX_TERM_HEIGHT
    )
    red_panel = Panel(
        "\n".join(current_step_lines),
        title="Step Output",
        border_style="red",
        height=RED_BOX_HEIGHT
    )
    return Group(term_panel, red_panel, step_prog, all_prog)


with Live(render_live(), console=console, refresh_per_second=10) as live:
    for idx, step in enumerate(bar_items):
        step_prog.update(step_id, description=f"Running {step}", step=idx)
        all_prog.update(all_id, advance=1, description=f"Completed {step}")

        # simulate terminal output for this step
        for i in range(20):
            line = f"[{step}] Command output line {i}"
            term_buffer.append(line)  # scrolls automatically when maxlen reached
            current_step_lines.append(line)  # red box shows last few lines
            live.update(render_live())
            time.sleep(0.15)
