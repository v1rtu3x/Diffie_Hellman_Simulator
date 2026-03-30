import asyncio
from server import BackendServer


HOST = "0.0.0.0"
PORT = 5050


async def main() -> None:
    server = BackendServer(HOST, PORT)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())