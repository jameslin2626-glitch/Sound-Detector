# Sound Detector

Lightweight Python sound notification bot that listens to your computer's audio  
and sends alerts to Discord when the detected volume passes a configurable threshold.

The bot can mention your Discord user, include the detected volume and a timestamp,  
and automatically delete alert messages after a set interval. An optional second webhook can report live volume levels.

## Features

* **Sound Detection:** Monitor audio input and trigger alerts above a configurable threshold.
* **Discord Notifications:** Send a message to a Discord channel and mention one or more users.
* **Live Volume (Optional):** Post volume readings through a second webhook, with readings above the threshold highlighted.
* **Automatic Cleanup:** Delete alert messages after 60 seconds and live volume messages after 20 seconds by default.
* **Cooldown:** Wait 5 seconds between user pings by default.

---

## Installation & Setup

### Requirements

* A macOS, Windows, or Linux computer
* The Sound Detector executable for your operating system
* A Discord server and webhook
* An audio input device that receives the sound you want to monitor
* A configured `.env` file (required for Discord notifications)

### Download and Run

Download the correct executable, depending on your OS from the project's Releases page.

#### macOS

Open the extracted folder and double-click the Sound Detector executable.  
If macOS blocks it, open **System Settings > Privacy & Security** and allow the app to run.  
Grant any requested microphone or audio input access so it can listen to the selected device.

#### Windows

Open the extracted folder and double-click the Sound Detector `.exe` file.  
If Windows SmartScreen displays a warning, confirm that the file came from the project's Releases page before choosing **More info > Run anyway**.  
Allow audio input access if Windows requests it.

#### Linux

Open a Terminal in the extracted folder and run:

```bash
chmod +x ./SoundDetector-Linux
./SoundDetector-Linux
```

Ensure your desktop session and selected audio input allow the program to capture the audio you want to monitor.

### Audio Device Setup

The program listens to an audio input device.  
To capture internal desktop or game audio, you may need a virtual audio device and must route the audio output to it.

On macOS, a virtual device such as BlackHole 2ch can route system audio to the program.  
On Windows, options can include VB-Cable or Stereo Mix / “What U Hear,” depending on the device and setup.  

Select and verify the appropriate input device in your system's audio settings.

---

## Configuration

Create a plain-text file named `.env` in the project directory (with no `.txt` extension).  
Add your webhook URL and Discord user ID:  

```dotenv
NOTIFY_USER_URL=your_webhook_url
FIRST_USER_ID=your_discord_user_id
```

For optional live volume reports, add a second webhook:

```dotenv
VOLUME_REPORT_URL=your_second_webhook_url
```

Keep webhook URLs private. You can configure additional user IDs in the script if you want other accounts to be mentioned.

### Script Settings

The sound threshold is adjustable in the script. A detected volume above the threshold triggers an alert;  
for example, a reading of `0.214` exceeds a threshold of `0.1`.  
Different devices and applications can produce very different readings,  
so adjust the threshold while checking the volume values from your input device.

The script's `NOISE_FLOOR` setting controls which volume readings are printed in the Terminal. Increase it to reduce output. `PING_COOLDOWN` and `AUTO_DELETE_DURATION` are also adjustable; their values are in seconds.

For more reliable readings, verify your input volume in system settings.  
On Windows, try a sample rate of 44,100 or 48,000 Hz if the device supports it.

---

## Running the Program

Before starting the executable, make sure the `.env` file is in the same folder and contains a valid Discord webhook URL and user ID.  
Without this file, Discord notification data will not be available and alerts will not work correctly.

Launch the downloaded executable for your operating system:

* **macOS:** Double-click the Sound Detector executable.
* **Windows:** Double-click the Sound Detector `.exe` file.
* **Linux:** Run the executable from Terminal as described under **Download and Run**.

The program sends a Discord alert when the monitored audio exceeds the configured threshold.  
Successful alerts include the detected volume and a timestamp in America/New_York time.  
If enabled, live volume readings are posted to the second webhook.

## Troubleshooting

| Error | Common cause | What to check |
| --- | --- | --- |
| `requests.exceptions.MissingSchema` or `InvalidURL` | Missing or malformed webhook URL | Confirm `.env` exists and `NOTIFY_USER_URL` begins with `https://discord.com/api/webhooks/`. |
| `requests.exceptions.RequestException` | Network connection or Discord service issue | Check your connection and Discord availability, then retry. |
| `requests.exceptions.JSONDecodeError` | Discord returned a non-JSON error response | Check the connection and response handling in `send_discord_ping()`. |
| `sounddevice.PortAudioError` | Input device disconnected, unavailable, or busy | Check that the selected input or virtual audio device is connected and active. |
| `zoneinfo.ZoneInfoNotFoundError` | Time zone database is unavailable | Install system time zone data; on some Windows Python setups, install `tzdata`. |
| `ModuleNotFoundError` | Required Python package is missing | Install the packages listed under **Requirements**. |

---

## Developer Notes

Made with love by @Crystallization (@crystallizationn).

Package Versions:

* `requests==2.34.2`
* `numpy==2.5.2`
* `sounddevice==0.5.6`
* `python-dotenv==1.2.3`
* `pytz==2026.3.post1` (for v1.08.8)

Discord Color Values:

* Red: `0xFF0000`
* Green: `0x57F287`
* Yellow: `0xFEE75C`
* Blurple: `0x5865F2`
