import asyncio
import math

from fastapi import FastAPI, Request
from pydantic import BaseModel

from skynet.env import whisper_max_connections

from skynet.logs import get_logger
from skynet.modules.monitoring import CONNECTIONS_METRIC, TRANSCRIBE_GRACEFUL_SHUTDOWN, TRANSCRIBE_STRESS_LEVEL_METRIC

log = get_logger(__name__)
app = FastAPI()

STATE_FILE = '/tmp/streaming-whisper-connections-state'
haproxy_state = 'ready'
haproxy_check_state_task = None


async def get_haproxy_percentage():
    conns = CONNECTIONS_METRIC._value.get()
    perc = int(math.floor(conns * 100 / whisper_max_connections))
    inverted = 100 - perc
    if inverted <= 0:
        return 1
    return int(inverted)


async def handle_tcp_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global haproxy_state
    percentage = await get_haproxy_percentage()
    response = f'up {haproxy_state} {percentage}%\n'
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
class StateResponse(BaseModel):
    request_status: str
    current_state: str
    desired_state: str


class CurrentStateResponse(BaseModel):
    current_state: str
    active_connections: int
    stress_level: float


async def get_current_state():
    try:
        with open(STATE_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        log.error(f'The state file does not exist')
        with open(STATE_FILE, 'w') as f:
            f.write('ready')
        return 'ready'
    except Exception as e:
        log.error(f'Failed to read the state file: {e}')
        return 'unknown'


@app.post('/state')
async def set_state(request: Request):
    global haproxy_check_state_task
    payload = await request.json()
    log.info(f'Received state change request: {payload}')
    current_state = await get_current_state()

    if haproxy_check_state_task is None:
        loop = asyncio.get_running_loop()
        haproxy_check_state_task = loop.create_task(update_haproxy_state())

    if payload['state'] and payload['state'] in ['drain', 'maint', 'ready']:
        with open(STATE_FILE, 'w') as f:
            f.write(payload['state'].strip())
        return StateResponse(request_status='success', current_state=current_state, desired_state=payload['state'])

    log.error(f'Invalid state change request: {payload}')
    return StateResponse(request_status='failed', current_state=current_state, desired_state=payload['state'])


@app.get('/state')
async def get_state(request: Request):
    return CurrentStateResponse(
        current_state=await get_current_state(),
        active_connections=CONNECTIONS_METRIC._value.get(),
        stress_level=TRANSCRIBE_STRESS_LEVEL_METRIC._value.get(),
    )


# Updates the HAProxy state if it changes via the API
# so that the load balancer can react to the changes
async def update_haproxy_state():
    global haproxy_state
    while True:
        new_state = await get_current_state()
        if new_state != haproxy_state:
            log.info(f'HAProxy state changed from {haproxy_state} to {new_state}')
            haproxy_state = new_state
        if new_state in ('drain', 'maint'):
            TRANSCRIBE_GRACEFUL_SHUTDOWN.set(1)
        else:
            TRANSCRIBE_GRACEFUL_SHUTDOWN.set(0)
        await asyncio.sleep(1)
