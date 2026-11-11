from faster_whisper import WhisperModel

print("Loading Whisper model...")

model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8"
)

print("Whisper loaded successfully.")

audio_file = "meeting-test.webm"

print("Transcribing audio...")

segments, info = model.transcribe(
    audio_file,
    beam_size=5
)

print("\n--- TRANSCRIPT ---")

for segment in segments:
    print(segment.text)

print("\n--- END TRANSCRIPT ---")