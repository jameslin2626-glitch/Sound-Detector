import os
import threading
import time
import numpy as np
import requests
import sounddevice as sd
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
USER_ID = os.getenv("THIRD_USER_ID")

NOISE_THRESHOLD = 0.25
NOISE_FLOOR = 0.01

PING_COOLDOWN = 15
DEVICE_INDEX = 0
AUTO_DELETE_DURATION = 300

last_ping_time = 0
nyc_tz = ZoneInfo("America/New_York")


def time_report():
    now = datetime.now(nyc_tz)
    return now.strftime("%d/%m/%Y %H:%M:%S")


def auto_delete_msg(msg_id, delay):
    time.sleep(delay)
    if not WEBHOOK_URL:
        return
    delete_url = f"{WEBHOOK_URL}/messages/{msg_id}"
    requests.delete(delete_url)


def send_discord_ping(text):
    if not WEBHOOK_URL:
        print("Error: Webhook URL is missing.")
        return

    data = {
        "content": f"<@{USER_ID}> {text}",
        "allowed_mentions": {"parse": ["users"]},
    }
    response = requests.post(
        f"{WEBHOOK_URL}?wait=true", json=data
    )

    if response.status_code in (200, 201):
        msg_id = response.json().get("id")
        threading.Thread(
            target=auto_delete_msg,
            args=(msg_id, AUTO_DELETE_DURATION),
            daemon=True,
        ).start()


def audio_callback(indata, frames, time_info, status):
    global last_ping_time

    volume_norm = np.linalg.norm(indata) / np.sqrt(len(indata))

    if volume_norm > NOISE_FLOOR:
        print(f"Live Volume: {volume_norm:.2f}")

    current_time = time.time()
    if volume_norm > NOISE_THRESHOLD and (
        current_time - last_ping_time > PING_COOLDOWN
    ):
        print(f"*** Threshold exceeded! Volume: {volume_norm:.2f} ***")
        msg = (
            "***A sound in REx:R was detected***\n"
            f"-# TIME {time_report()}"
        )
        threading.Thread(
            target=send_discord_ping, args=(msg,), daemon=True
        ).start()
        last_ping_time = current_time


print(f"Listening for sound cues on device index {DEVICE_INDEX}...")
with sd.InputStream(
    device=DEVICE_INDEX,
    callback=audio_callback,
    channels=2,
    samplerate=22050,
):
    while True:
        time.sleep(1)