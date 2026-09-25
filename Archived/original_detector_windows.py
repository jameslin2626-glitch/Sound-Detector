import sys
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import librosa
import numpy as np
import requests
import sounddevice as sd
import os
from dotenv import load_dotenv

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
USER_ID = os.getenv("FIRST_USER_ID")
SECOND_USER_ID = os.getenv("SECOND_USER_ID")

CHILL_SOUND = "Exotic.wav"
HEART_SKIP_SOUND = "Exquisite.wav"

CHILL_THRESHOLD = 0.6
HEART_SKIP_THRESHOLD = 0.3
PING_COOLDOWN = 6
AUTO_DELETE_DURATION = 300
SAMPLE_RATE = 22050

nyc_tz = ZoneInfo("America/New_York")


def get_report():
    now = datetime.now(nyc_tz)
    timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
    return f"-# TIME: {timestamp}"


def get_windows_device():
    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            name = dev["name"].lower()
            if dev["max_input_channels"] > 0 and (
                "cable" in name or "stereo mix" in name
            ):
                return i, dev["max_input_channels"]
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                return i, dev["max_input_channels"]
    except Exception as err:
        print(f"Error querying devices: {err}")

    print("No audio input devices found.")
    sys.exit(1)

 
DEVICE_INDEX, INPUT_CHANNELS = get_windows_device()

# Chill
chill_audio, _ = librosa.load(CHILL_SOUND, sr=SAMPLE_RATE)
chill_mfcc = librosa.feature.mfcc(y=chill_audio, sr=SAMPLE_RATE, n_mfcc=13)
chill_mfcc = librosa.util.normalize(chill_mfcc, axis=1)

# Exquisite
heart_audio, _ = librosa.load(HEART_SKIP_SOUND, sr=SAMPLE_RATE)
heart_mfcc = librosa.feature.mfcc(
    y=heart_audio, sr=SAMPLE_RATE, n_mfcc=13
)
heart_mfcc = librosa.util.normalize(heart_mfcc, axis=1)

max_buffer_samples = max(len(chill_audio), len(heart_audio))
audio_buffer = np.zeros(max_buffer_samples)
last_ping_time = 0


def delete_message_after_delay(msg_id, delay):
    time.sleep(delay)
    delete_url = f"{WEBHOOK_URL}/messages/{msg_id}"
    requests.delete(delete_url)


def send_discord_ping(text):
    data = {
        "content": f"<@{USER_ID}> <@{SECOND_USER_ID}> {text}",
        "allowed_mentions": {"parse": ["users"]},
    }
    response = requests.post(f"{WEBHOOK_URL}?wait=true", json=data)

    if response.status_code in (200, 201):
        msg_id = response.json().get("id")
        threading.Thread(
            target=delete_message_after_delay,
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

    chill_score = compute_score(live_mfcc, chill_mfcc)
    heart_score = compute_score(live_mfcc, heart_mfcc)

    current_time = time.time()
    if current_time - last_ping_time <= PING_COOLDOWN:
        return

    if chill_score < CHILL_THRESHOLD and chill_score <= heart_score:
        print(f"*** Chill detected! Distance: {chill_score:.3f} ***")
        send_discord_ping(
            "***A chill goes down your spine... (Exotic)***\n"
            f"{get_report()}\n-# Distance: {chill_score:.3f}"
        )
        last_ping_time = current_time
        audio_buffer.fill(0)

    elif heart_score < HEART_SKIP_THRESHOLD and heart_score < chill_score:
        print(f"*** Exquisite detected! Distance: {heart_score:.3f} ***")
        send_discord_ping(
            "***Your heart skips a beat... (Exquisite)***\n"
            f"{get_report()}\n-# Distance: {heart_score:.3f}"
        )
        last_ping_time = current_time
        audio_buffer.fill(0)


print(f"Listening on device index {DEVICE_INDEX}...")
with sd.InputStream(
    device=DEVICE_INDEX,
    callback=audio_callback,
    channels=INPUT_CHANNELS,
    samplerate=SAMPLE_RATE,
):
    while True:
        time.sleep(1)