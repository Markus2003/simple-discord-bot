# The Ruler of Server
A Discord Bot written in Python that can play Music from `YouTube` and `YouTube Music` (with a little twist😉)!<br>
It can also run custom services on Host Server through `System Contol` (A.K.A. `systemctl`)...
<br><br>

# Table of Content
- [Capabilities](#capabilities)
- [Bot Support](#bot-support)
- [Installation](#installation)
    - [Requirements](#requirements)
    - [Create a Bot Account](#create-a-bot-account)
    - [Download and Setup](#download-and-setup)
- [`settings.json` customization](#settingsjson-customization)
- [Features](#features)
    - [music_player](#music_player)
    - [pity](#pity)
    - [caching](#caching)
    - [minimal_mode](#minimal_mode)
    - [systemctl](#systemctl)
    - [logger](#logger)
- [Disclaimer](#disclaimer)
- [License](#license)
- [Credit](#credit)
<br><br>

# Capabilities
- Music Player control through `-join`, `-play`, `-pause`, `-resume`, `-skip`, `-loop`, `-stop` and `-leave`.
- Play music directly from `YouTube` or `YouTube Music` the first time you request a song, activating the feature `caching` (see [Features](#features) section) the second time you request the same song it will be streamed directly from the disk.
- Check you music pity with `-pity` (the higher it is, the higher is the probability to hear a song you didn't ask for).
- `System Control` (A.K.A. `systemctl`) integration.
- Can send some weird woobly `.webm` to revive the conversation.
- A `sudo` section to edit the Bot settings directly from Discord.
<br><br>

# Bot Support
| OS                   | 64-bit | 32-bit |  ARM   |
|----------------------|--------|--------|--------|
| Linux (Debian Based) |   ✓   |   ?    |   ✓   |
| Termux on Android    |    ?   |    ?   |    ✓  |
##### When running the bot on Termux be sure to activate the feature `minimal_mode`
<br><br>

# Installation
## Requirements
⚠️ Be sure to **NOT** write `sudo` if installing on Termux!⚠️<br>
You will need `Python3` with his `pip3`, `ffmpeg` and some additional libraries. To install everything just run:
```bash
sudo apt-get install python3 python3-pip python3-dev ffmpeg libffi-dev libnacl-dev -y
```
Now you have to install the required packges from `pip3`:
```python
pip3 install youtube-dl yt-dlp discord.py discord.py[voice] uuid requests
```
<br>

## Create a Bot Account
Good now you have to create your own Discord Application and make it a bot.<br>
- First of all go to the [Discord Developer Portal](https://discord.com/developers/applications) and login with your Discord credentials.
- Now click `Applications` (from the menu on the left) -> `New Application` (on the top right) and follow the instructions on screen.
- Now head for the `Bot` section (on the left), if present, click `Add Bot` (be sure to uncheck `Public Bot` under `Authorization Flow` and check `Presence Intent`, `Server Members Intent` and `Message Content Intent`, all under `Privilefed Gateway Intents`).
- Before leaving the `Bot` section hit `Reset Token` -> `Yes, do it!` -> `Copy` and save the Token somewhere, we will need it later.
- Feel free to customize the Bot in the `Bot` and `General Information` section, if you grab a photo from the Internet save the Link, it will be useful later.
- Once you are ready go to `OAuth2` Section -> `URL Generator` sub-section.
- Here in the first box check `bot` and then, in the new second box, check `Administator` to avoid any problem.
- At the bottom of the Page you should now see a generated URL, copy it and paste it in address bar, hit Enter and add it to your own Discord Server.
<br>

## Download and Setup
⚠️ Again Termux users: be sure to **NOT** write `sudo`!⚠️<br>
Now that you have the Token and the Bot in your Server we can download and set up the code.<br>
**Note: we will use a CLI approach so we will be server-friendly and termux-friendly**

### Step 1
Navigate to the installation folder (make sure it's empty) and write it down the path (if you don't know it type `pwd`)

### Step 2
Download the leatest release and extract it with:
```bash
wget "https://github.com/Markus2003/simpleDiscordBot/releases/latest/Bot Deployer.zip" -O "Bot Deployer.zip" && unzip "Bot Deployer.zip" && rm "Bot Deployer.zip"
```

### Step 3
Edit the `settings.json` and `resetSettings.json` by typing:
```bash
nano src/configs/resetSettings.json
```
```bash
nano src/configs/settings.json
```
If you are installing on Termux, you have finished the setup. Run `python3 main.py` to start the bot (see [Features](#features) for more goodies).<br>
If you are installing on Linux continue down here.

### Step 4 (Optional)
If you want you can make the bot as a service that start at boot and restart automatically when failing.<br>
To do so, type:
```bash
sudo nano /etc/systemd/system/nameOfBot.service
```
Now copy and paste the below box and edit `Description` (Optional), `User` (with your username, if you don't know it exit and type `whoami`) and `WorkingDirectory` (using the previous path took with the `pwd` command):
```service
[Unit]
Description=Discord Bot Written in Python3
After=network.target
Wants=network-online.target

[Service]
User=yourUserName
Type=simple
WorkingDirectory=/path/to/bot/folder/
ExecStart=/usr/bin/python3 'main.py'
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
```
then hit `CTRL+X` and enable and start the bot by typing:
```bash
sudo systemctl daemon-reload && sudo systemctl enable nameOfBot.service && sudo systemctl start nameOfBot.service
``` 

### Step 5 (Makes possible the use of the `System Control` Interface)
Now you can activate the `System Control` Interface by heading again in the bot folder. Once here type:
```bash
sudo chmod +x pythonSystemctl.sh
```
this will make the script executable. The bot will need this program in order to retrieve some systemctl information, but it require also `sudo` privileges to run this script (**and only this script**). To grant this privilege type:
```bash
sudo visudo
```
scroll down until you see these two lines:
```bash
# Allow members of group sudo to execute any command
%sudo   ALL=(ALL:ALL) ALL
```
create a new line right below these two and write:
```bash
yourUserName    ALL=(ALL)   NOPASSWD: /path/to/pythonSystemctl.sh
```
hit `CTRL+X`, Save and reboot everything. If you followed everything correctly you are now good to go!<br>
Congrats! Now go to [Features](#features) to see some goodies...
<br><br>

# `settings.json` customization
You can freely edit the follwing variables in the `settings.json` and `resetSettings.json` files:
- `BOT_NAME`: You can put the Bot name here
- `BOT_TOKEN`: Remember the Token you took from the `Discord Developer Portal`? This is a great place to put it
- `BOT_PREFIX`: Every message that start with what is inside here will invoke the Bot, so be careful... or not...
- `BOT_AVATAR`: Remember the link of the photo you put on the Bot's profile? That's a really good place to put it
- `BOT_ACCENT_COLOR`: The color that will be visualized the embeded messages (use hex notation and replace the `#` with `0x`)
- `BOT_ADMIN_ROLE`: Here you will need to put the role that can use the `sudo` privileges (do not include @, only the name)
- `GATCHA_MAX_PITY`: Feel free to raise or lower this number, the lower it is the more frequently you will not decide what song will be played...
- `GATCHA_50_50_LOOSE`: Add or remove how many song you want, just the example included
<br><br>

# Features
This Bot offers some features that you can enable and diasble when you want by typing in chat `sudo [enable | disable] feature <feature>` and save with `sudo settings update`.<br>
Some of these are:
## `music_player`
Conditions to use this feature: **None**<br>
This Feature enable all music-related commands
<br><br>

## `pity`
Conditions to use this feature: **`music_player` need to be enabled**<br>
This Feature enable the gatcha system of the music player
<br><br>

## `caching`
Conditions to use this feature: **`music_player` need to be enabled**<br>
This Feature enable the caching of all the request song.<br>
The first time you will request a song it will download it in backroud while streaming directly from `YouTube`.<br>
When you will request the same song again it will play the song directly from the local drive (this solution resolve a very annoying bug when streaming...)
<br><br>

## `minimal_mode`
Conditions to use this feature: **None**<br>
This Feature automatically block some Features that can be devastating for some Machines (yes Termux users, you should really activate thi feature now)
<br><br>

## `systemctl`
Conditions to use this feature: **[Step 5](#step-5-makes-possible-the-use-of-the-system-control-interface) and `minimal_mode` must be disabled**<br>
This Feature enable the Interface of `System Control`, you can start, restart and stop services directly from the Discord chat (really useful when you are hosting a Minecraft Server on the same Machine)<br>
Type `-help` in any chat to learn more about this command<br>
Type `-systemctl help` in any chat to learn more about the service that are enabled/dissabled
<br><br>

## `logger`
Conditions to use this feature: **None**<br>
If you need for some reason to keep track of every interaction in the server, this feature is for you. **Remember to not violate the others privacy!**
<br><br>

# Disclaimer
I am **NOT** responsible for any damage or data steal caused to your machine by using this program.<br>
**YOU** are choosing to use this program.
<br><br>

# License
Thi project use the [GNU GPLv3](https://github.com/Markus2003/simpleDiscordBot/blob/main/LICENSE) license.
<br><br>

# Credit
Made with ❤️ by [Markus2003](https://www.github.com/Markus2003)