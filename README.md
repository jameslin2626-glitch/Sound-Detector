# Sound Notification Bot (`sound-detector.py`)

Sound Detector Script  
v1.07.6  

Sound Notification Bot is a bot that is connected to a Discord Webhook URL.  

The bot detects for device audio that is above the SOUND_THRESHOLD (0.1).  
If it successfully detects audio that is above that, it will ping the user's Discord ID  
in their Discord server in their selected webhook channel, alerting them of the sound's presence.  

Successful Discord pings display America/New_York Time and the Volume Distance of which it detected,  
and will have a cooldown of 5 seconds before the Discord user can be pinged again.  

Messages from the Webhook Bot will automatically be deleted  
after 60 seconds unless the Terminal session ends early.  

*OPTIONAL:*  
In the other URL, your live volume detection will be shown in the channel it is connected to.  
If the Live Volume is above SOUND_THRESHOLD, it's volume will be in Bold & Italic.  
The live volume messages will be deleted after 20 seconds.  

This bot is great at knowing if a special sound cue occurred while  
you were idling on a video game, or if you're deaf or whatever and need this for accessibility.  

## Discord Server Setup

To use this script and connect to Discord, follow the instructions here:  
* Create your own Discord Server  
* Find Integrations  
* Go to Webhooks  
* Create new Webhook(s)  
* Copy the Webhook URL(s) and put it inside your .env file along with your Discord User ID(s)  

If you want to get your Discord User ID(s), go to settings, enable Developer Mode,  
right-click your name after sending a message, and click on Copy User ID.  

## Audio Device Setup

Note that macOS requires a virtual audio device (like BlackHole 2ch)  
to route internal desktop/game audio to sounddevice as an actual input source.  
(Pro Tip: For some game settings, you can set the Output Device to the virtual audiodevice you want to use)  

I use macOS, and while I believe Windows has its own audio device router, you still may need something  
like VB-Cable, What U Hear, etc.  

## .env Configuration

Sensitive data like the Discord Webhook URL should ALWAYS be hidden inside an .env file.  
This is to keep your server safe from malicious activities from untrusted users who might be in it.   

Inside your .env file should contain the following:  
* NOTIFY_USER_URL=your_webhook_url  
* FIRST_USER_ID=your_discord_user_id   

*OPTIONAL:*  
* VOLUME_REPORT_URL=your_second_webhook_url  

Ultimately, you can also add more discord_user_ids if you want to have alternate accounts be pinged as well.  

To create a .env file, create a new plain text file named exactly .env  
(with no text before the dot and no .txt extension) in the root directory of your project.  

Doing this process in a code editor (like Visual Studio Code or PyCharm)  
is a lot smoother and way easier to set up.  

## Package Installation

The script uses 5 third-party Python packages to function correctly.  
You need to install the following third-party Python packages:  
* requests  
* numpy  
* sounddevice  
* python-dotenv  
* pytz

Run this command in your Terminal:  
* pip install numpy requests sounddevice python-dotenv pytz  

On macOS / Linux, standard system Python often requires pip3 instead of pip. If you hit an  
externally-managed-environment error, use a virtual environment, or run this command in your Terminal:  
* python3 -m pip install numpy requests sounddevice python-dotenv pytz  

If you use Windows, and run into permission errors when installing globally,  
open Command Prompt as Administrator, or run this command in your Terminal:  
* py -m pip install numpy requests sounddevice python-dotenv pytz  

OPTIONAL:
* pip install -r requirements.txt

To avoid path issues across any operating system, always create and activate  
a Python virtual environment (.venv) before installing dependencies.  

## Script Configuration

NOTE:  
* Different devices, pieces of software, and video games might process sound differently.  
* Use 44100 or 48000 Hz (Hertz) rate if you're on Windows for more accuracy.
* Make sure you always verify your input volume levels in System Settings.

NOISE_THRESHOLD = 0.1 can be adjustable. Some sounds will be as low as 0.05 while some will be as high as 3.0+  
All you need to know is that if the volume it detects is "bigger" than the NOISE_THRESHOLD, it will send a Discord ping  
(e.g: Volume: 0.214 > NOISE_THRESHOLD (0.1) → send_discord_ping()).

If you want to only print out volume that is above something like 0.2 to prevent bloating, increase NOISE_FLOOR to that value.  
If you do not want to see all the volume prints in the Terminal,  
you can just remove the 'if' statement and the indented print() inside it at Ln 93.  

PING_COOLDOWN and AUTO_DELETE_DURATION are adjustable. Their values are always in seconds  

## Troubleshooting Exceptions

Some common exceptions you may run into are:  
* requests.exceptions.MissingSchema / InvalidURL  
* requests.exceptions.RequestException  
* requests.exceptions.JSONDecodeError  
* sounddevice.PortAudioError  
* zoneinfo.ZoneInfoNotFoundError  
* ModuleNotFoundError  

*requests.exceptions.MissingSchema / InvalidURL:*  
* FIRST_DISCORD_WEBHOOK_URL is None (missing from .env) or missing https://.  
* Location of Exception: send_discord_ping() / auto_delete_msg()   
* Fix: Verify .env exists and that FIRST_DISCORD_WEBHOOK_URL contains [https://discord.com/api/webhooks/] at the start.  

*requests.exceptions.RequestException:*  
* Connection drops, local network offline, or Discord server outages  
* Location of Exception: requests.post() / requests.delete()  
* Fix: Wrap API requests in a try/except requests.exceptions.RequestException: block  

*requests.exceptions.JSONDecodeError:*  
* Discord returns an error page (like a 502 Bad Gateway) instead of JSON, making response.json() crash  
* Location of Exception: send_discord_ping()  
* Fix: Safely handle parsing or check response.headers.get("content-type") before calling .json()  

*sounddevice.PortAudioError:*  
* The selected audio device drops, disconnects, or is locked by another process  
* Location of Exception: sd.InputStream()  
* Fix: Ensure virtual audio routing (e.g., BlackHole or Stereo Mix) remains connected and active in system sound settings  

*zoneinfo.ZoneInfoNotFoundError:*  
* The host system lacks standard IANA timezone database data  
* Location of Exception: ZoneInfo("America/New_York")  
* Fix: Install system timezone data (tzdata via pip on Windows/Python setups)  

*ModuleNotFoundError:*  
* The third-party packages weren't installed via Terminal  
* Location of Exception: Module imports on Ln 5, 6, 7, 8
* Fix: Make sure you have all 4 third-party packages installed. Head back to ## Package Installation for more info  

## Developer Notes

Made with love by @Crystallization (@crystallizationn)  

requests==2.34.2  
numpy==2.5.2  
sounddevice==0.5.6  
python-dotenv==1.2.3  
pytz==2026.3.post1  

Red: 0xFF0000  
Green: 0x57F287  
Yellow: 0xFEE75C  
Blurple: 0x5865F2  