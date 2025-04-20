# conftest.py

import sys
import os

# Add the absolute path of `src/` to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
