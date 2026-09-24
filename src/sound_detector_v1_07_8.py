import os
import sys
import threading
import time
import requests
import numpy as np
import sounddevice as sd
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from datetime import datetime

# Sound Detector Script
# v1.07.8

load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("NOTIFY_USER_URL")
FIRST_USER_ID = os.getenv("FIRST_USER_ID")

NOISE_THRESHOLD = 0.1
PING_COOLDOWN = 4
SAMPLE_RATE = 44100  # Use 44100 or 48000 if on Windows
AUTO_DELETE_DURATION = 300
NOISE_FLOOR = 0.01

nyc_tz = ZoneInfo("America/New_York")


def time_report():
    now = datetime.now(nyc_tz)
    return now.strftime("%d/%m/%Y %H:%M:%S")


def find_audio_device():
    try:
        devices = sd.query_devices()
    except Exception:
        print("[ERROR] Cannot query audio devices")
        sys.exit(1)

    for i, dev in enumerate(devices):
        name = dev["name"].lower()
        if dev["max_input_channels"] > 0 and (
            "cable" in name or "stereo mix" in name or "what u hear" in name
        ):
            return i, dev["max_input_channels"]

    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            return i, dev["max_input_channels"]

    print("[ERROR] No valid audio input device found")
    sys.exit(1)


DEVICE_INDEX, INPUT_CHANNELS = find_audio_device()
last_ping_time = 0

is_collecting = False


def auto_delete_msg(msg_id, delay):
    time.sleep(delay)
    delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{msg_id}"
    requests.delete(delete_url)


def send_discord_ping(text):
    data = {
        "content": f"<@{FIRST_USER_ID}> {text}",
        "allowed_mentions": {"parse": ["users"]},
    }
    response = requests.post(f"{DISCORD_WEBHOOK_URL}?wait=true", json=data)

    if response.status_code in (200, 201):
        msg_id = response.json().get("id")
        threading.Thread(
            target=auto_delete_msg,
            args=(msg_id, AUTO_DELETE_DURATION),
            daemon=True,
        ).start()


def audio_callback(indata, frames, time_info, status):
    """
    Processes the device audio, monitor volume levels, and report spikes.

    Sends a Discord notification if live volume exceeds the threshold and the
    cooldown period has elapsed.
    """
    global last_ping_time

    volume_norm = float(np.sqrt(np.mean(indata**2)))

    if volume_norm > NOISE_FLOOR:
        print(f"Volume: {volume_norm:.3f}")

    current_time = time.time()
    if volume_norm > NOISE_THRESHOLD:
        if current_time - last_ping_time > PING_COOLDOWN:
            print(f"*** Noise Detected! Volume Level: {volume_norm:.3f} ***")

            delete_time = int(current_time)

            send_discord_ping(
                f"***A sound was detected!***\n"
                f"-# Time: {time_report()}\n"
                f"-# Threshold: {NOISE_THRESHOLD}\n"
                f"-# Live Volume: ***{volume_norm:.3f}***\n"
            )
            last_ping_time = current_time


print(f"Listening for noise on device index {DEVICE_INDEX}...")
with sd.InputStream(
    device=DEVICE_INDEX,
    callback=audio_callback,
    channels=INPUT_CHANNELS,
    samplerate=SAMPLE_RATE,
):
    while True:
        time.sleep(1)