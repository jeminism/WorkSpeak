"""WorkSpeak CDP Overlay entry point."""
from .main import main
import sys

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
