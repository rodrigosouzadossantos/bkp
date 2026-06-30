#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom Python Code Formatter
Applies specific formatting rules based on analyzed project style.
"""

import re
import sys
from pathlib import Path


class CustomFormatter:
  """Formatter that applies custom spacing and quote rules."""
  
  def __init__( self, indent_size : int = 2 ):
    self.indent_size = indent_size
  
  def format_file( self, filepath : Path ) -> str :
    """Format a Python file according to custom rules."""
    with open( filepath, 'r', encoding = 'utf-8' ) as f :
      content = f.read( )
    
    formatted = self.format_code( content )
    return formatted
  
  def format_code( self, code : str ) -> str :
    """Apply all formatting rules to code string."""
    lines = code.split( '\n' )
    formatted_lines = []
    in_docstring = False
    docstring_delim = None
    
    for i, line in enumerate( lines ) :
      # Track docstrings (skip formatting inside)
      if '"""' in line or "'''" in line :
        if not in_docstring :
          delim = '"""' if '"""' in line else "'''"
          if line.count( delim ) >= 2 :
            # Single-line docstring
            formatted_lines.append( line )
            continue
          else :
            in_docstring = True
            docstring_delim = delim
            formatted_lines.append( line )
            continue
        else :
          if docstring_delim in line :
            in_docstring = False
            formatted_lines.append( line )
            continue
      
      if in_docstring :
        formatted_lines.append( line )
        continue
      
      # Skip empty lines and pure comments
      if not line.strip( ) or line.strip( ).startswith( '#' ) :
        formatted_lines.append( line )
        continue
      
      formatted_line = line
      
      # Apply rules carefully
      formatted_line = self._convert_quotes( formatted_line )
      formatted_line = self._format_function_signature( formatted_line )
      formatted_line = self._format_operators( formatted_line )
      
      formatted_lines.append( formatted_line )
    
    return '\n'.join( formatted_lines )
  
  def _convert_quotes( self, line : str ) -> str :
    """Convert double quotes to single quotes where safe."""
    # Skip f-strings
    if 'f"' in line or "f'" in line :
      return line
    
    # Find standalone strings with double quotes
    def replace_quotes( match ) :
      content = match.group( 1 )
      # Keep double quotes if string contains single quote
      if "'" in content or '\\' in content :
        return f'"{content}"'
      return f"'{content}'"
    
    # Simple pattern for isolated strings
    line = re.sub( r'"([^"\\]*)"', replace_quotes, line )
    
    return line
  
  def _format_function_signature( self, line : str ) -> str :
    """Format def lines with proper spacing."""
    # Match function definition
    match = re.match( r'^(\s*)def\s+(\w+)\s*\(([^)]*)\)\s*(->\s*[^:]+)?\s*:\s*$', line )
    if not match :
      return line
    
    indent = match.group( 1 )
    name = match.group( 2 )
    params = match.group( 3 )
    ret = match.group( 4 )
    
    # Format parameters
    if params.strip( ) :
      # Add spaces around colons in type hints
      params = re.sub( r'(\w+)\s*:\s*(\w+)', r'\1 : \2', params )
      params_formatted = f' {params.strip( )} '
    else :
      params_formatted = ' '
    
    result = f'{indent}def {name}({params_formatted})'
    
    if ret :
      ret = re.sub( r'->\s*(.+)', r'-> \1', ret ).strip( )
      result += f' {ret} '
    
    result += ':'
    
    return result
  
  def _format_operators( self, line : str ) -> str :
    """Add spacing around operators."""
    # Assignment (not ==, !=, etc)
    line = re.sub( r'(\w)\s*=\s*(?!=)', r'\1 = ', line )
    
    # Comparison operators
    line = re.sub( r'\s*(==|!=|<=|>=)\s*', r' \1 ', line )
    
    # Space before colon in control structures
    if re.match( r'^\s*(if|elif|while|for|with)\s+', line ) :
      line = re.sub( r':\s*$', ' :', line )
    elif re.match( r'^\s*(else|try|except|finally)\s*:\s*$', line ) :
      line = re.sub( r':\s*$', ' :', line )
    
    # Clean multiple spaces
    line = re.sub( r'  +', ' ', line )
    
    return line
  
  def save_formatted( self, filepath : Path, formatted_code : str, backup : bool = True ) :
    """Save formatted code to file."""
    if backup :
      backup_path = filepath.with_suffix( '.py.bak' )
      if filepath.exists( ) :
        import shutil
        shutil.copy2( filepath, backup_path )
        print( f'✓ Backup created: {backup_path}' )
    
    with open( filepath, 'w', encoding = 'utf-8' ) as f :
      f.write( formatted_code )
    
    print( f'✓ Formatted: {filepath}' )


def show_usage( ) :
  """Display usage guide."""
  print( '''
╔════════════════════════════════════════════════════════════════════╗
║          Custom Python Code Formatter - Usage Guide                ║
╚════════════════════════════════════════════════════════════════════╝

📋 USAGE:
  python custom_formatter.py [OPTIONS] file1.py [file2.py ...]

🔧 OPTIONS:
  --check          Check if files need formatting (dry-run)
  --no-backup      Format without creating .bak files
  -h, --help       Show this help

📝 EXAMPLES:
  Format single file:
    $ python custom_formatter.py script.py
  
  Check multiple files:
    $ python custom_formatter.py --check *.py
  
  Format without backup:
    $ python custom_formatter.py --no-backup script.py

✨ RULES APPLIED:
  • Spacing in function signatures: def func( x : int ) :
  • Quote conversion: "text" → 'text'
  • Operator spacing: x=1 → x = 1
  • Colon spacing: if x: → if x :
''' )


def main( ) :
  """CLI entry point."""
  import argparse
  
  parser = argparse.ArgumentParser(
    description = 'Format Python code',
    add_help = False
  )
  parser.add_argument( 'files', nargs = '*', type = Path )
  parser.add_argument( '--check', action = 'store_true' )
  parser.add_argument( '--no-backup', action = 'store_true' )
  parser.add_argument( '-h', '--help', action = 'store_true' )
  
  args = parser.parse_args( )
  
  if args.help :
    show_usage( )
    return
  
  if not args.files :
    print( 'Error: no files specified' )
    print( 'Use -h or --help for usage' )
    sys.exit( 1 )
  
  formatter = CustomFormatter( )
  
  for filepath in args.files :
    if not filepath.exists( ) :
      print( f'✗ Not found: {filepath}' )
      continue
    
    if filepath.suffix != '.py' :
      print( f'⚠ Skipping: {filepath}' )
      continue
    
    print( f'\nProcessing: {filepath}' )
    
    try :
      original = filepath.read_text( encoding = 'utf-8' )
      formatted = formatter.format_file( filepath )
      
      if args.check :
        if original != formatted :
          print( f'✗ Would reformat: {filepath}' )
        else :
          print( f'✓ Already formatted: {filepath}' )
      else :
        if original != formatted :
          formatter.save_formatted( filepath, formatted, not args.no_backup )
        else :
          print( f'✓ No changes: {filepath}' )
    
    except Exception as e :
      print( f'✗ Error: {e}' )


if __name__ == '__main__' :
  main( )