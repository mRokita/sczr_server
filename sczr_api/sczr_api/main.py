from typing import List

import aioredis
import orjson
from fastapi import (
    FastAPI,
    WebSocket, Depends,
)
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from starlette.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiModel(BaseModel):
    class Config:
        json_loads = orjson.loads
        json_dumps = lambda v, default: orjson.dumps(v, default=default).decode()


class Face(ApiModel):
    image_src: str


class FacesFrame(ApiModel):
    faces: List[Face]
    timestamp_taken: str
    timestamp_processed: str


async def get_redis_pool():
    redis: aioredis.Redis = await aioredis.create_redis_pool('redis://redis')
    try:
        yield redis
    finally:
        redis.close()
        await redis.wait_closed()

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<html>
<body>
<div id="faces">

</div>
<script type="text/javascript">
let socket = new WebSocket("ws://localhost:8082/watch_frames");
let facesDiv = document.getElementById('faces');
socket.onmessage = function(event) {
    let msg = JSON.parse(event.data);
    console.log(msg.timestamp_taken);  
    facesDiv.innerHTML = msg.faces.map((frame) => `<img src=${frame.image_src} />`).join(" ");
};

socket.onclose = function(event) {
  if (event.wasClean) {
    alert(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
  } else {
    // e.g. server process killed or network down
    // event.code is usually 1006 in this case
    alert('[close] Connection died');
  }
};

socket.onerror = function(error) {
  alert(`[error] ${error.message}`);
};
</script>
</body>
</html>
    """


@app.websocket("/watch_frames")
async def watch_frames(websocket: WebSocket,
                         redis: aioredis.Redis = Depends(get_redis_pool)):
    await websocket.accept()
    try:
        (ch, ) = await redis.subscribe('channel:frames')
        async for msg in ch.iter():
            frame = FacesFrame.parse_raw(msg)
            logger.info(f'Sending frame taken at {frame.timestamp_taken} to {websocket.client.port}')
            await websocket.send_json(frame.dict())
    except WebSocketDisconnect:
        pass
    else:
        await websocket.close()


@app.websocket("/send_frames")
async def watch_progress(websocket: WebSocket,
                         redis: aioredis.Redis = Depends(get_redis_pool)):
    await websocket.accept()
    try:
        while msg := FacesFrame.parse_raw(await websocket.receive_text()):
            logger.info(msg.timestamp_taken)
            await redis.publish('channel:frames', msg.json().encode())
    except WebSocketDisconnect:
        pass
    else:
        await websocket.close()
