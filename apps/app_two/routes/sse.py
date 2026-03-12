from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from core.realtime import realtime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CHANNEL = "app_two_updates"


@router.get("/")
async def index(request: Request):
    """Renders the SSE test page for app_two."""
    return templates.TemplateResponse(
        "sse_test.html",
        {"request": request, "app_name": "app_two", "channel": CHANNEL, "sse_url": "/app-two/sse"},
    )


@router.get("/sse")
async def sse():
    """
    Server-Sent Events stream for app_two.
    Connect from the browser via:
        const es = new EventSource('/app-two/sse');
    Or test with curl:
        curl -N http://localhost:8000/app-two/sse
    """
    return StreamingResponse(
        realtime.sse_generator(CHANNEL),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
