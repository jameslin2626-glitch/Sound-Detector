import sys
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import librosa
import numpy as np
import requests
import sounddevice as sd

WEBHOOK_URL = (
    "https:/Vjr-GOl-BwELFxjf7ET4iQqDJXOjOT76qYZn920_KL"
)#stop it

USER_ID = ""

# Sound File Definitions & Thresholds
SOUNDS = {
    "chill": {
        "file": "LoudChill.wav",
        "threshold": 0.6,
        "message": "***A chill goes down your spine... (Exotic)***",
    },
    #"vision_blur": {
    #    "file": "VisionBlur.wav",
    #    "threshold": 0.8,
    #    "message": "***Your vision begins to blur... (Enigmatic)***",
    #},
    "unfathomable": {
        "file": "Unfathomable.wav",
        "threshold": 1.0,
        "message": "***The ground shakes below your feet... (Unfathomable)***",
    },
    #"otherworldly": {
    #    "file": "Otherworldly.wav",
    #    "threshold": 0.8,
    #    "message": "***Divine forces emanate from a heavenly cave... (Otherworldly)***",
    #},
    #"zenith": {
    #    "file": "Zenith.wav",
    #    "threshold": 0.8,
    #    "message": "***An unusual force materializes upon the surface of this world... (Zenith)***",
    #},
    #"imaginary": {
    #    "file": "Imaginary.wav",
    #    "threshold": 0.8,
    #    "message": "***Reality bends before you... (Imaginary)***",
    #},
}

PING_COOLDOWN = 15
AUTO_DELETE_DURATION = 300

SAMPLE_RATE = 22050

nyc_tz = ZoneInfo("America/New_York")


def time_report():
    now = datetime.now(nyc_tz)
    timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
    return f"-# TIME: {timestamp}"


def get_macos_device():
    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            name = dev["name"].lower()
            if dev["max_input_channels"] > 0 and any(
                k in name for k in ("blackhole", "soundflower", "existential")
            ):
                return i, dev["max_input_channels"]

        default_in = sd.default.device[0]
        if default_in is not None and default_in >= 0:
            dev = devices[default_in]
            if dev["max_input_channels"] > 0:
                return default_in, dev["max_input_channels"]

        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                return i, dev["max_input_channels"]
    except Exception as err:
        print(f"Error querying devices: {err}")

    print("No audio input devices found.")
    sys.exit(1)


DEVICE_INDEX, INPUT_CHANNELS = get_macos_device()

max_buffer_samples = 0
for key, sound in SOUNDS.items():
    audio, _ = librosa.load(sound["file"], sr=SAMPLE_RATE)
    mfcc = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
    sound["mfcc"] = librosa.util.normalize(mfcc, axis=1)

    if len(audio) > max_buffer_samples:
        max_buffer_samples = len(audio)

audio_buffer = np.zeros(max_buffer_samples)
last_ping_time = 0


def auto_delete_msg(msg_id, delay):
    time.sleep(delay)
    delete_url = f"{WEBHOOK_URL}/messages/{msg_id}"
    requests.delete(delete_url)


def send_discord_ping(text):
    data = {
        "content": f"<@{USER_ID}> {text}",
        "allowed_mentions": {"parse": ["users"]},
    }
    response = requests.post(f"{WEBHOOK_URL}?wait=true", json=data)

    if response.status_code in (200, 201):
        msg_id = response.json().get("id")
        threading.Thread(
            target=auto_delete_msg,
            args=(msg_id, AUTO_DELETE_DURATION),
            daemon=True,
        ).start()


def compute_score(live_mfcc, target_mfcc):
    min_cols = min(live_mfcc.shape[1], target_mfcc.shape[1])
    diff = live_mfcc[:, :min_cols] - target_mfcc[:, :min_cols]
    return float(np.mean(np.abs(diff)))


def audio_callback(indata, frames, time_info, status):
    global last_ping_time, audio_buffer

    chunk = np.mean(indata, axis=1)
    if np.max(np.abs(chunk)) < 0.005:
        return

    audio_buffer = np.roll(audio_buffer, -len(chunk))
    audio_buffer[-len(chunk) :] = chunk

    live_mfcc = librosa.feature.mfcc(
        y=audio_buffer, sr=SAMPLE_RATE, n_mfcc=13
    )
    live_mfcc = librosa.util.normalize(live_mfcc, axis=1)

    current_time = time.time()
    if current_time - last_ping_time <= PING_COOLDOWN:
        return

    best_key = None
    best_score = float("inf")

    for key, sound in SOUNDS.items():
        score = compute_score(live_mfcc, sound["mfcc"])
        if score < sound["threshold"] and score < best_score:
            best_score = score
            best_key = key

    if best_key is not None:
        matched_sound = SOUNDS[best_key]
        print(f"*** {best_key.title()} detected! Distance: {best_score:.3f} ***")
        send_discord_ping(
            f"{matched_sound['message']}\n"
            f"{time_report()}\n"
            f"-# Distance: {best_score:.3f}"
        )
        last_ping_time = current_time
        audio_buffer.fill(0)


print(f"Listening for sound cues on device index {DEVICE_INDEX}...")
with sd.InputStream(
    device=DEVICE_INDEX,
    callback=audio_callback,
    channels=INPUT_CHANNELS,
    samplerate=SAMPLE_RATE,
):
    while True:
        time.sleep(1)