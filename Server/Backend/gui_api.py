from aiohttp import web, WSMsgType


class GuiApi:
    def __init__(self, backend_server):
        self.backend = backend_server
        self.websockets = set()

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websockets.add(ws)
        await ws.send_json({
            "type": "snapshot",
            "payload": self.backend.build_gui_snapshot()
        })

        async for msg in ws:
            if msg.type == WSMsgType.ERROR:
                print("WebSocket error:", ws.exception())

        self.websockets.discard(ws)
        return ws

    async def broadcast(self, payload):
        dead = []
        for ws in self.websockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.websockets.discard(ws)

    async def get_status(self, request):
        return web.json_response(self.backend.build_gui_snapshot())

    async def start_session(self, request):
        data = await request.json()
        p = int(data.get("p", 23))
        g = int(data.get("g", 5))

        await self.backend.start_session_from_gui(p, g)
        return web.json_response({"ok": True})

    async def reset_session(self, request):
        await self.backend.reset_session_from_gui()
        return web.json_response({"ok": True})


from aiohttp import web, WSMsgType


class GuiApi:
    def __init__(self, backend_server):
        self.backend = backend_server
        self.websockets = set()

    async def index(self, request):
        return web.Response(
            text="DH Simulator backend is running. Use /api/status or connect the GUI app.",
            content_type="text/plain"
        )

    async def ws_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.websockets.add(ws)
        await ws.send_json({
            "type": "snapshot",
            "payload": self.backend.build_gui_snapshot()
        })

        async for msg in ws:
            if msg.type == WSMsgType.ERROR:
                print("WebSocket error:", ws.exception())

        self.websockets.discard(ws)
        return ws

    async def broadcast(self, payload):
        dead = []
        for ws in self.websockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.websockets.discard(ws)

    async def get_status(self, request):
        return web.json_response(self.backend.build_gui_snapshot())

    async def start_session(self, request):
        data = await request.json()
        p = int(data.get("p", 23))
        g = int(data.get("g", 5))

        await self.backend.start_session_from_gui(p, g)
        return web.json_response({"ok": True})

    async def reset_session(self, request):
        await self.backend.reset_session_from_gui()
        return web.json_response({"ok": True})

def create_app(gui_api):
    app = web.Application()
    app.router.add_get("/", gui_api.index)
    app.router.add_get("/ws", gui_api.ws_handler)
    app.router.add_get("/api/status", gui_api.get_status)
    app.router.add_post("/api/session/start", gui_api.start_session)
    app.router.add_post("/api/session/reset", gui_api.reset_session)
    return app