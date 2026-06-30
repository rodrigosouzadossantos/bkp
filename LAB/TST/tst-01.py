import sys
import time
import atexit
import os

from typing import TextIO, List, Dict, Any, Optional
from collections import deque

from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live


MAX_TERM_HEIGHT = 15
term_buffer : deque = deque( maxlen = MAX_TERM_HEIGHT )

RED_BOX_HEIGHT = 5
current_step_lines : deque = deque( maxlen = RED_BOX_HEIGHT )


class RichIO :
  class RichStream :
    def __init__( self,
      console : Console,
      buffer : List[str],
      live : Live, 
      render_func,
      max_lines : int = 10,
    ) -> None :
      self.console = console
      self.buffer = buffer
      self.live = live
      self.max_lines = max_lines
      self.render_func = render_func

      self.count = 0

    def write( self, text: str ) -> None:
      # Avoid extra blank lines
      lines = text.splitlines( )
      for line in lines :
        if line.strip( ) :
          self.count += 1
          self.buffer.append( f'#{self.count:07d} │ { line }' )
      while len(self.buffer) > self.max_lines:
        self.buffer.pop(0)
      # Update the live panel
      self.live.update( self.render_func( ) )

    def flush( self ) -> None:
      pass # For compatibility

  def __init__( self,
    max_lines: int = 10,
    show_stderr: bool = True,
    panel_config : Optional[ Dict[ str, Any ] ] = None
  ) -> None:
    self.original_stdout: TextIO = sys.stdout
    self.original_stderr: TextIO = sys.stderr

    self.console_stdout: Console = Console( file = self.original_stdout,
                                           force_terminal = True )
    self.console_stderr: Console = Console( file = self.original_stderr )

    self.panels: Dict[str, List[str]] = {
      "trace": [],
      "stderr": [],
      "stdout": [],
    }
    self.buffer: List[ str ] = [ ]
    self.max_lines = max_lines
    self.show_stderr = show_stderr

    self.panel_config: Dict[str, Dict[str, Any]] = {
      "trace": {"height": 32},
      "stderr": {"border_style": "red", "height": max_lines + 2},
      "stdout": {"border_style": "green", "height": max_lines + 2},
    }
    if panel_config :
      for k, v in panel_config.items( ) :
        self.panel_config[k] = v

    # Start Live context
    self.live = Live(
      self.render_live( ),
      console = self.console_stdout,
      refresh_per_second = 10
    )
    self.live.__enter__( ) # Manually enter Live context

    self.enable( )

    atexit.register(self.disable)

  def render_live(self):
    panel_renders = [ ]
    for name, lines in self.panels.items( ) :
      if name == "stderr" and not self.show_stderr:
        continue

      config = self.panel_config.get( name, { } )

      lines = lines[ -config.get( 'height', self.max_lines ) : ]
      lines = [ '' ] * (
        config.get( 'height', self.max_lines ) - len( lines ) - 2
      ) + lines

      panel_renders.append(
        Panel(
          '\n'.join( lines ),
          title = f"{name.upper()} Panel",
          **config
        )
      )
    return Group( *panel_renders)


  def enable(self) -> None:
    sys.stdout = self.RichStream(
      self.console_stdout,
      self.panels["stdout"],
      self.live,
      self.render_live,
      self.max_lines,
    )
    sys.stderr = self.RichStream(
      self.console_stderr,
      self.panels["stderr"],
      self.live,
      self.render_live,
      self.max_lines,
    )
    trace_stream = self.RichStream(
      console=self.console_stdout,
      buffer=self.panels["trace"],
      live=self.live,
      render_func=self.render_live,
      max_lines=30
    )
    def trace_calls(frame, event, arg):
      if os.path.abspath(
        frame.f_code.co_filename
      ).startswith( os.getcwd( ) ) :
        if event != 'line' :#event in ( 'call', 'return', 'exception' ) :
          code = frame.f_code
          func_name = code.co_name
          filename = code.co_filename
          lineno = frame.f_lineno
          trace_stream.write(
            f"[yellow]{event}: {func_name} ({filename}:{lineno})[/yellow]"
          )
      return trace_calls
    self._trace_func = trace_calls
    sys.settrace(self._trace_func)

  def disable(self) -> None:
    sys.stdout = self.original_stdout
    sys.stderr = self.original_stderr
    sys.settrace( None )
    # Manually exit Live context
    self.live.__exit__( None, None, None )


  def __enter__(self):
    self.enable( )
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.disable( )

#if __name__ == "__main__":
with RichIO(max_lines=10) as rich_io:
  for i in range(25):
    print(f"[bold blue]Live message {i+1}[/bold blue]")
    print(f"[bold red]Now it works without freezing![/bold red]")
    print(f"Normal text also appears.")
    print(f"[bold green]This is standard output![/bold green]")
    print(f"[bold yellow]This is also standard output![/bold yellow]")
    time.sleep(0.2)
#rich_io.disable()
print("Back to normal output.")
