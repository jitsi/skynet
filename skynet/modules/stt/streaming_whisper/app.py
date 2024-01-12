import os

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, BaseLoader
from starlette.websockets import WebSocketDisconnect
from .ConnectionManager import ConnectionManager
from skynet.logs import get_logger


ws_connection_manager = ConnectionManager()
app = FastAPI()
log = get_logger(__name__)

html_test_ui_path = f'{os.getcwd()}/test/client'

with open(f'{html_test_ui_path}/index.html', 'r') as f:
    index_html = f.read()
j2_template = Environment(loader=BaseLoader()).from_string(index_html)
index = j2_template.render({})
app.mount('/client', StaticFiles(directory=html_test_ui_path), name='static')


@app.get('/')
async def get():
    return HTMLResponse(index)


@app.get('/healthz')
async def get():
    health_response = {'status': 'UP'}
    return JSONResponse(content=health_response)


@app.websocket('/ws/{meeting_id}')
async def websocket_endpoint(websocket: WebSocket, meeting_id: str, auth_token: str):
    await ws_connection_manager.connect(websocket, meeting_id, auth_token)
    try:
        while True:
            try:
                chunk = await websocket.receive_bytes()
            except KeyError as err:
                log.warning(f'Expected bytes, received something else, disconnecting {meeting_id}. Error: \n{err}')
                ws_connection_manager.disconnect(meeting_id)
                break
            if len(chunk) == 1 and ord(b'' + chunk) == 0:
                log.info(f'Received disconnect message for {meeting_id}')
                ws_connection_manager.disconnect(meeting_id)
                break
            await ws_connection_manager.process(meeting_id, chunk)
    except WebSocketDisconnect:
        ws_connection_manager.disconnect(meeting_id)
        log.info(f'{meeting_id} has disconnected')

