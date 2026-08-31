import os
import sys
import threading
import time
import requests
import numpy as np
import sounddevice as sd
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# REx:R Sound Detector Script
# v2.6.2-alpha

load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
FIRST_USER_ID = os.getenv("FIRST_USER_ID")
SECOND_USER_ID = os.getenv("SECOND_USER_ID")
THIRD_USER_ID = os.getenv("THIRD_USER_ID")

# Highest to Lowest Thresholds
SOUNDS = {
    "IMAGINARY": {
        "IMAGINARY_THRESHOLD": 0.70,
        "IMAGINARY_MESSAGE": (
            "***Reality bends before you... (Imaginary)***"
        ),
    },
    "OTHERWORLDLY": {
        "OTHERWORLDLY_THRESHOLD": 0.645,
        "OTHERWORLDLY_MESSAGE": (
            "***An indefinite number of hallucinations reaves your mind... "
            "(Otherworldly)***"
        ),
    },
    "UNFATHOMABLE": {
        "UNFATHOMABLE_THRESHOLD": 0.60,
        "UNFATHOMABLE_MESSAGE": (
            "***The ground shakes below your feet... (Unfathomable)***"
        ),
    },
    "TRANSCENDENT": {
        "TRANSCENDENT_THRESHOLD": 0.48,
        "TRANSCENDENT_MESSAGE": (
            "***You hear a ringing in your ears... (Transcendent)***"
        ),
    },
    "ZENITH": {
        "ZENITH_THRESHOLD": 0.466,
        "ZENITH_MESSAGE": (
            "***An unusual force materializes upon the surface of "
            "this world... (Zenith)***"
        ),
    },
    "ENIGMATIC": {
        "ENIGMATIC_THRESHOLD": 0.375,
        "ENIGMATIC_MESSAGE": (
            "***Your vision begins to blur... (Enigmatic)***"
        ),
    },
    "EXQUISITE": {
        "EXQUISITE_THRESHOLD": 0.35,
        "EXQUISITE_MESSAGE": (
            "***Your heart skips a beat... (Exquisite)***"
        ),
    },
    "EXOTIC": {
        "EXOTIC_THRESHOLD": 0.30,
        "EXOTIC_MESSAGE": "***A chill goes down your spine... (Exotic)***",
    },
}

imaginary_val = SOUNDS["IMAGINARY"]["IMAGINARY_THRESHOLD"]
otherworldly_val = SOUNDS["OTHERWORLDLY"]["OTHERWORLDLY_THRESHOLD"]
unfathomable_val = SOUNDS["UNFATHOMABLE"]["UNFATHOMABLE_THRESHOLD"]
transcendent_val = SOUNDS["TRANSCENDENT"]["TRANSCENDENT_THRESHOLD"]
zenith_val = SOUNDS["ZENITH"]["ZENITH_THRESHOLD"]
enigmatic_val = SOUNDS["ENIGMATIC"]["ENIGMATIC_THRESHOLD"]
exquisite_val = SOUNDS["EXQUISITE"]["EXQUISITE_THRESHOLD"]
exotic_val = SOUNDS["EXOTIC"]["EXOTIC_THRESHOLD"]

NOISE_FLOOR = 0.01
SAMPLE_RATE = 22050
PING_COOLDOWN = 12
AUTO_DELETE_DURATION = 300
WINDOW_DURATION = 1.0

nyc_tz = ZoneInfo("America/New_York")


def time_report():
    now = datetime.now(nyc_tz)
    return now.strftime("%d/%m/%Y %H:%M:%S")


def find_audio_device():
    try:
        devices = sd.query_devices()
    except Exception:
        print("[ERROR] Cannot query audio devices.")
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

    print("[ERROR] No valid audio input device found.")
    sys.exit(1)


DEVICE_INDEX, INPUT_CHANNELS = find_audio_device()
last_ping_time = 0

is_collecting = False
collected_samples = []
lock = threading.Lock()


def auto_delete_msg(msg_id, delay):
    time.sleep(delay)
    delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{msg_id}"
    requests.delete(delete_url)


def send_discord_ping(text):
    data = {
        "content": f"<@{THIRD_USER_ID}> {text}",
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


def evaluate_peak_volume():
    global is_collecting, collected_samples, last_ping_time

    time.sleep(WINDOW_DURATION)

    with lock:
        if collected_samples:
            peak_volume = max(collected_samples)
        else:
            peak_volume = 0
        collected_samples = []
        is_collecting = False

    current_time = time.time()
    if current_time - last_ping_time <= PING_COOLDOWN or peak_volume <= 0:
        return

    # HIGHEST TO LOWEST THRESHOLDS
    # 0.70
    if (
        imaginary_val is not None
        and peak_volume > imaginary_val
    ):
        print(f"Imaginary Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['IMAGINARY']['IMAGINARY_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {imaginary_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time

    # 0.645
    elif (
        otherworldly_val is not None
        and peak_volume > otherworldly_val
    ):
        print(f"Otherworldly Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['OTHERWORLDLY']['OTHERWORLDLY_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {otherworldly_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time

    # 0.60
    elif (
        unfathomable_val is not None
        and peak_volume > unfathomable_val
    ):
        print(f"Unfathomable Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['UNFATHOMABLE']['UNFATHOMABLE_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {unfathomable_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time

    # 0.48
    elif (
        transcendent_val is not None
        and peak_volume > transcendent_val
    ):
        print(f"Transcendent Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['TRANSCENDENT']['TRANSCENDENT_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {transcendent_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time

    # 0.466
    elif (
        zenith_val is not None
        and peak_volume > zenith_val
    ):
        print(f"Zenith Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['ZENITH']['ZENITH_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {zenith_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time

    # 0.375
    elif (
        enigmatic_val is not None
        and peak_volume > enigmatic_val
    ):
        print(f"Enigmatic Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['ENIGMATIC']['ENIGMATIC_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {enigmatic_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time

    # 0.34
    elif (
        exquisite_val is not None
        and peak_volume > exquisite_val
    ):
        print(f"Exquisite Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['EXQUISITE']['EXQUISITE_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {exquisite_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time

    # 0.33
    elif (
        exotic_val is not None
        and peak_volume > exotic_val
    ):
        print(f"Exotic Detected! | Volume Level: {peak_volume:.3f}")
        send_discord_ping(
            f"{SOUNDS['EXOTIC']['EXOTIC_MESSAGE']}\n"
            f"-# TIME: {time_report()}\n"
            f"-# Threshold: {exotic_val}\n"
            f"-# Distance: {peak_volume:.3f}"
        )
        last_ping_time = current_time


def audio_callback(indata, frames, time_info, status):
    global is_collecting, collected_samples

    volume_norm = float(np.sqrt(np.mean(indata**2)))

    if volume_norm > NOISE_FLOOR:
        print(f"Volume: {volume_norm:.3f}")

    active_thresholds = [
        val for val in [
            imaginary_val,
            otherworldly_val,
            unfathomable_val,
            transcendent_val,
            zenith_val,
            enigmatic_val,
            exquisite_val,
            exotic_val,
        ]
        if val is not None
    ]
    min_trigger = min(active_thresholds) if active_thresholds else 0.30

    if volume_norm > min_trigger:
        with lock:
            collected_samples.append(volume_norm)
            if not is_collecting:
                is_collecting = True
                threading.Thread(
                    target=evaluate_peak_volume, daemon=True
                ).start()


print(f"Listening for REx:R spawn sounds on device index {DEVICE_INDEX}...")
with sd.InputStream(
    device=DEVICE_INDEX,
    callback=audio_callback,
    channels=INPUT_CHANNELS,
    samplerate=SAMPLE_RATE,
):
    while True:
        time.sleep(1)