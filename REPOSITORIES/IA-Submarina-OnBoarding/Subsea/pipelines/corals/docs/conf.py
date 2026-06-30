
import os
import sys

# Path so Sphinx can import Subsea

sys.path.insert(
  0,
  os.path.abspath( '../../../..' )
)

project = 'Subsea Image Pipeline'
author = 'Subsea'
copyright = '2026, Subsea'

extensions = [
  'sphinx.ext.autodoc',
  'sphinx.ext.napoleon',
  'sphinx.ext.viewcode',
  'sphinx.ext.autosummary',
]

autosummary_generate = True

autodoc_typehints = 'description'

templates_path = [ '_templates' ]
exclude_patterns = [ '_build' ]

html_theme = 'sphinx_rtd_theme'

