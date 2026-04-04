import asyncio
from aiohttp import web

from server import BackendServer
from gui_api import GuiApi, create_app


TCP_HOST = "0.0.0.0"
TCP_PORT = 5050

GUI_HOST = "0.0.0.0"
GUI_PORT = 5051


async def main():
    backend = BackendServer(TCP_HOST, TCP_PORT)
    gui_api = GuiApi(backend)
    backend.attach_gui_api(gui_api)

    tcp_task = asyncio.create_task(backend.start())

    app = create_app(gui_api)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, GUI_HOST, GUI_PORT)
    await site.start()

    print(f"GUI API available at http://localhost:{GUI_PORT}")

    await tcp_task


if __name__ == "__main__":
    asyncio.run(main())