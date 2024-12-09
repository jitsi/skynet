import asyncio
import math

from fastapi import FastAPI, Request
from pydantic import BaseModel

from skynet.env import whisper_max_connections

from skynet.logs import get_logger
from skynet.modules.monitoring import CONNECTIONS_METRIC, TRANSCRIBE_GRACEFUL_SHUTDOWN, TRANSCRIBE_STRESS_LEVEL_METRIC

log = get_logger(__name__)

# Bundles a REST API server used by the autoscaler with a TCP server that is queried by the HAProxy agent.
# The REST API is used to change and query the state of the system. The HAProxy agent server is closely
# bound to the REST API server as the latter will inform HAProxy if the system was set to drain mode.

autoscaler_rest_app = FastAPI()
TRANSCRIBE_GRACEFUL_SHUTDOWN.set(0)
haproxy_state = 'ready'


def get_haproxy_lb_percentage():
    conns = CONNECTIONS_METRIC._value.get()
    perc = int(math.floor(conns * 100 / whisper_max_connections))
    inverted = 100 - perc
    if inverted <= 0:
        return 1
    return int(inverted)


async def handle_tcp_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    response = f'up {haproxy_state} {get_haproxy_lb_percentage()}%\n'
    if writer is not None:
        try:
            writer.write(response.encode())
        except Exception as ex:
            log.warning('TCP exception during haproxy-agent check.', ex)
        finally:
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            log.debug('HAProxy agent socket closed.')


async def create_tcpserver(port):
    tcpserver = await asyncio.start_server(handle_tcp_request, '0.0.0.0', port)
    log.info(f'HaProxy Agent Check TCP Server listening on 0.0.0.0:{port}')
    try:
        await tcpserver.serve_forever()
    except KeyboardInterrupt:
        tcpserver.close()


# Endpoints for the autoscaler to query the current state of the system
class UpdateStateResponse(BaseModel):
    request_status: str
    old_state: str
    new_state: str


class CurrentStateResponse(BaseModel):
    state: str
    connections: int
    stress_level: float
    graceful_shutdown: bool


@autoscaler_rest_app.post('/state')
async def set_state(request: Request):
    global haproxy_state
    payload = await request.json()
    log.info(f'Received state change request: {payload}')
    old_state = haproxy_state

    if payload['state'] and payload['state'].strip() in ['drain', 'maint', 'ready']:
        haproxy_state = payload['state'].strip()

        if haproxy_state == 'drain':
            TRANSCRIBE_GRACEFUL_SHUTDOWN.set(1)

        return UpdateStateResponse(
            request_status='success',
            old_state=old_state,
            new_state=haproxy_state,
        )

    log.error(f'Invalid state change request: {payload}')
    return UpdateStateResponse(request_status='failed', old_state=old_state, new_state='invalid')


@autoscaler_rest_app.get('/state')
async def get_state(request: Request):
    return CurrentStateResponse(
        state=haproxy_state,
        connections=CONNECTIONS_METRIC._value.get(),
        stress_level=TRANSCRIBE_STRESS_LEVEL_METRIC._value.get(),
        graceful_shutdown=bool(TRANSCRIBE_GRACEFUL_SHUTDOWN._value.get()),
    )
