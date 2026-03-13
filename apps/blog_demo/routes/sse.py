from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.realtime import realtime

router = APIRouter()

CHANNEL = "blog_updates"


@router.get("/live")
async def live():
    """
    Server-Sent Events stream for blog updates.
    Receives a 'post_published' event whenever a post is created with published=true.
    Connect from the browser via:
        const es = new EventSource('/blog-demo/live');
    Or test with curl:
        curl -N http://localhost:8000/blog-demo/live
    """
    return StreamingResponse(
        realtime.sse_generator(CHANNEL),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
