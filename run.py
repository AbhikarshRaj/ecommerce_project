import sys
from pathlib import Path

# Ensure application directory is in sys.path regardless of execution working directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
