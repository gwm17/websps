import sys

PROJECT_DIR = "/path/to/websps"
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)

from websps import create_app

application = create_app()