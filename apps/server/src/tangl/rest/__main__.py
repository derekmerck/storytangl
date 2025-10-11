import asyncio

from uvicorn import Config, Server

from tangl.config import settings
from tangl.rest.app import app

async def async_main():
    config = Config(app=app, host="0.0.0.0", port=8000, log_level="info")
    server = Server(config)
    await server.serve()

def main():
    # have to wrap the async main method with a normal method
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
