# Speech Recognition (OpenAI Whisper STT PoC)

Minimal microphone -> transcription CLI using OpenAI's transcription API.

## Setup (uv)

```bash
uv venv
source .venv/bin/activate
uv pip install -r speech-recognition/requirements.txt
```

## Run (CLI demo)

Start the program, speak, and it prints your words to stdout.

```bash
python speech-recognition/stt_module.py --api-key "$OPENAI_API_KEY"
```

Optional:

```bash
python speech-recognition/stt_module.py --api-key "$OPENAI_API_KEY" --seconds 5
python speech-recognition/stt_module.py --api-key "$OPENAI_API_KEY" --language ko
python speech-recognition/stt_module.py --list-devices
python speech-recognition/stt_module.py --api-key "$OPENAI_API_KEY" --device 2
```

## Integrate as a module

```python
from stt_module import AudioConfig, record_until_enter, transcribe_wav_bytes

config = AudioConfig(samplerate=16000, channels=1)
wav_bytes = record_until_enter(config)
text = transcribe_wav_bytes(api_key="YOUR_KEY", wav_bytes=wav_bytes)
print(text)
```

## Notes

- Default model: `gpt-4o-mini-transcribe`
- Default language hint: `ko` (Korean)
- Output is plain text
