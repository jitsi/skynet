import asyncio
import math

from skynet.logs import get_logger

log = get_logger(__name__)

from skynet.env import whisper_max_connections
from skynet.modules.monitoring import CONNECTIONS_METRIC

async def calc_percentage():
    conns = CONNECTIONS_METRIC._value.get()
    perc = int(math.floor(conns * 100 / whisper_max_connections))
    inverted = 100 - perc
    if inverted <= 0:
        return 1
    return int(inverted)


async def handle_tcp_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    percentage = await calc_percentage()
    status = 'up ready '
    response = f'{status}{percentage}%\n'
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
            return
    log.debug('The TCP writer is null!')

async def create_tcpserver(port):
    tcpserver = await asyncio.start_server(
        handle_tcp_request, '0.0.0.0', port)
    log.info(f'HaProxy Agent Check TCP Server listening on 0.0.0.0:{port}')
    try:
        await tcpserver.serve_forever()
    except KeyboardInterrupt:
        tcpserver.close()
