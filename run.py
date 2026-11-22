import sys
import os

# Add backend to python path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.chdir(backend_dir)

import asyncio
from run import main

if __name__ == "__main__":
    asyncio.run(main())
