import asyncio

import pybase64

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from skynet.logs import get_logger
from skynet.modules.stt.streaming_whisper.utils import utils
from skynet.modules.stt.vox.connection_manager import ConnectionManager
from skynet.modules.stt.vox.decoder import PcmaDecoder
from skynet.modules.stt.vox.resampler import PcmResampler

log = get_logger(__name__)

ws_connection_manager = ConnectionManager()
app = FastAPI()
running_tasks = set()
whisper_sampling_rate = 16000


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, auth_token: str | None = None):
    decoder = PcmaDecoder()
    resampler = PcmResampler()
    session_id = utils.Uuid7().get()
    await ws_connection_manager.connect(websocket, session_id, auth_token)

    data_map = dict()
    resampler = None
    sampling_rate = 8000

    while True:
        try:
            ws_data = await websocket.receive_json()

            event = ws_data.get('event')

            if event == 'start':
                try:
                    sampling_rate = ws_data['start']['mediaFormat']['sampleRate']
                except KeyError:
                    pass

            if event == 'media':
                media = ws_data['media']
                participant_id: str = media['tag']

                if participant_id not in data_map:
                    header = (participant_id.encode() + '|en'.encode()).ljust(60, b'\0')
                    data_map[participant_id] = dict(raw=b'', chunks=0, header=header)

                payload = pybase64.b64decode(media['payload'])
                participant = data_map[participant_id]

                participant['raw'] += payload
                participant['chunks'] += 1

                if participant['chunks'] == 50:  # 50 chunks = 1 second
                    frames = decoder.decode(participant['raw'], media['timestamp'])

                    decoded_raw = b''

                    resampler = resampler or PcmResampler(
                        format='s16',
                        layout='mono',
                        rate=whisper_sampling_rate,
                    )

                    for frame in frames:
                        decoded_raw += resampler.resample(frame)

                    task = asyncio.create_task(
                        ws_connection_manager.process(
                            session_id, participant['header'] + decoded_raw, media['timestamp'], participant_id
                        )
                    )

                    running_tasks.add(task)
                    task.add_done_callback(running_tasks.remove)

                    participant['chunks'] = 0
                    participant['raw'] = b''

        except WebSocketDisconnect:
            ws_connection_manager.disconnect(session_id)
            data_map.clear()
            log.info(f'Session {session_id} has ended')
            break


__all__ = ['app']
