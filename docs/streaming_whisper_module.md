# Streaming Whisper Module

Performs live transcriptions using [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) via a websocket connection.

Enable the module by setting the `ENABLED_MODULES` env var to `streaming_whisper`.

> Here the JWT (see [Authorization](auth.md)) needs to be provided as a GET parameter. Please make sure to make it 
> _very_ short-lived.

## Requirements

- Poetry
- ffmpeg < 7 (required by pytorch)

If you have multiple versions of ffmpeg installed, make sure to update the `DYLD_LIBRARY_PATH` with the path to the 
ffmpeg libraries, e.g. `export DYLD_LIBRARY_PATH=/Users/MyUser/ffmpeg/6.1.2/lib:$DYLD_LIBRARY_PATH`.

## Quickstart

```bash
mkdir -p "$HOME/my-models-folder/streaming-whisper"
export WHISPER_MODEL_NAME="tiny.en"
export BYPASS_AUTHORIZATION=1
export ENABLED_MODULES="streaming_whisper"
export WHISPER_MODEL_PATH="$HOME/my-models-folder/streaming-whisper"

poetry install
./run.sh
```

Go to [demos/streaming-whisper/](../demos/streaming-whisper/) and start a Python http server.

```bash
python3 -m http.server 8080
```

Open http://127.0.0.1:8080.

## Websocket connection string

```
wss|ws://{DOMAIN}:8000/streaming-whisper/ws/{UNIQUE_MEETING_ID}?auth_token={short-lived JWT}
```

Omit the `auth_token` parameter if authorization is disabled.

## Authorization

We pass the JWT as part of the connection string, so please make it as short lived as possible. Refer to 
[Authorization](auth.md) for more details regarding the generation of JWTs.

## Data format

The payload sent by the client should be a binary blob. Where the first 60 bytes must be a header composed by a unique 
speaker id plus the language in short ISO format separated by a pipe `|`.

> E.G. `some_unique_speaker_id|en`

If the header is not fully filled, it must be padded with nulls. The rest of the payload must be a raw, single-channel, 
16khz, WAV array of bytes. **The audio chunk must not contain a WAV header**. Each audio chunk should be at least 1 
second long.

## Building the payload

### Javascript client implementation

```js
ws = new WebSocket('wss://' + host + '/streaming-whisper/ws/' + MEETINGID + '?auth_token=' + jwt.value)
ws.binaryType = 'blob'


function preparePayload(data) {
    let lang = "ro"
    let str = CLIENTID + "|" + lang
    if (str.length < 60) {
        str = str.padEnd(60, " ")
    }
    let utf8Encode = new TextEncoder()
    let buffer = utf8Encode.encode(str)

    let headerArr = new Uint16Array(buffer.buffer)

    const payload = []

    headerArr.forEach(i => payload.push(i))
    data.forEach(i => payload.push(i))

    return Uint16Array.from(payload)
}

recorder.port.onmessage = (e) => {
    const audio = convertFloat32To16BitPCM(e.data)
    const payload = preparePayload(audio)
    ws.send(payload)
}
```

### Java client implementation

```java
private ByteBuffer buildPayload(Participant participant, ByteBuffer audio) {
    ByteBuffer header = ByteBuffer.allocate(60);
    int lenAudio = audio.remaining();
    ByteBuffer fullPayload = ByteBuffer.allocate(lenAudio + 60);
    String headerStr = participant.getDebugName() + "|" + this.getLanguage(participant);
    header.put(headerStr.getBytes()).rewind();
    fullPayload.put(header).put(audio).rewind();
    return fullPayload;
}

public void sendAudio(Participant participant, ByteBuffer audio) {
    String participantId = participant.getDebugName();
    try
    {
        logger.debug("Sending audio for " + participantId);
        session.getRemote().sendBytes(buildPayload(participant, audio));
    }
    catch (NullPointerException e)
    {
        logger.error("Failed sending audio for " + participantId + ". " + e);
        if (!session.isOpen())
        {
            try
            {
                connect();
            }
            catch (Exception ex)
            {
                logger.error(ex.toString());
            }
        }
    }
    catch (IOException e)
    {
        logger.error("Failed sending audio for " + participantId + ". " + e);
    }
}
```

## Build image

```bash
make build
```

When running the resulting image, make sure to mount a faster-whisper model under `/models` on the container fs and 
reference it in the `WHISPER_MODEL_PATH` environment variable.

## Download models

```bash
git clone git@hf.co:guillaumekln/faster-whisper-base.en "$HOME/my-models-folder/streaming-whisper"
```

or download any other whisper model with huggingface-cli

```bash
pip install huggingface_hub
echo "export PATH=\$PATH:/home/$(whoami)/.local/bin" >> ~/.bashrc
source ~/.bashrc
huggingface-cli login
huggingface-cli download openai/whisper-tiny.en --repo-type model --cache-dir $HOME/my-models-folder/streaming-whisper
```

## Run

```bash
docker run -p 8000:8000 \
-u $(id -u):$(id -g) \
-e "BEAM_SIZE=1" \
-e "WHISPER_MODEL_PATH=/models/streaming-whisper" \
-e "ENABLED_MODULES=streaming_whisper" \
-e "BYPASS_AUTHORIZATION=1" \
-v "$HOME/my-models-folder":"/models" \
your-registry/skynet:your-tag
```

### Using GPU

In order to allow docker access GPU, install nvidia container toolkit from 
[https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-with-apt](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-with-apt)
Restart docker with `systemctl restart docker.service`
When running the resulting image, pass `--gpus all` and look for `CUDA device found.` in log.

## Demo

Check [/demos/streaming-whisper](../demos/streaming-whisper/) for a client implementation in Javascript. **Only works in Chrome-based browsers.**
