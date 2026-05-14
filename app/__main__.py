import asyncio

from app.main import main

try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass  # graceful exit on Windows where SIGINT is delivered as KeyboardInterrupt
