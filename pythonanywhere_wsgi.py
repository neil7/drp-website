"""
WSGI file for PythonAnywhere.

On PythonAnywhere: Web tab -> WSGI configuration file -> replace its contents with this file,
after changing PROJECT_DIR to where you uploaded/cloned the repo
(e.g. /home/<your-username>/drp-website).
"""

import sys
from pathlib import Path

PROJECT_DIR = Path("/home/YOUR_USERNAME/drp-website")  # <-- change this

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# .env in PROJECT_DIR is loaded by create_app() via python-dotenv.
import os
os.chdir(PROJECT_DIR)

from app import app as application  # noqa: E402
