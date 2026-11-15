# WiFi Fixer

Find out why your internet is slow, fix what can be fixed, and see who is on your WiFi. Free, open source, no account, nothing leaves your computer.

## Download (Windows)

1. Open the **Releases** page of this repo (right-hand side of the repo's main page).
2. Under **WiFi Fixer (latest build)**, click **WiFiFixer.exe** to download it.
3. Double-click it and click **Yes** on the administrator prompt.

That is it. No install, no Python needed.

If Windows shows a blue "Windows protected your PC" box, click **More info**, then **Run anyway**. Small free apps are not code-signed, so Windows warns about them. You can read every line of the source in this repo.

## What it does

- **Speed test against your target.** Enter the speed you pay for. It measures download, upload, ping, jitter, packet loss and DNS speed.
- **Diagnosis in plain English.** It tells you whether the problem is weak WiFi signal, the crowded 2.4 GHz band, a bad link to your router, your internet provider, slow DNS, or your own computer (CPU, memory or disk full).
- **Fix it for me.** One button that flushes DNS, renews your IP address and switches to fast DNS when needed.
- **Device scanner.** Lists everything on your WiFi. Click "That's mine" on your own devices. Everything else shows as Unknown, and anything that appears for the first time is marked NEW.
- **Boost a download.** Pick the app that is downloading. It gets high priority, background sync and update apps (OneDrive, Dropbox, Steam and similar) are paused, and other heavy apps are slowed down. Click "Restore everything" when you are done.
- **History graph and report.** See your speed over time and save a text report to send to your internet provider.

## How to use it

1. Type the speed you should be getting (for example 100) and click **Run full check**. It takes about 30 seconds.
2. Read the **Diagnosis**. Each problem has a suggested fix. Click **Fix it for me** to apply the automatic ones.
3. Look at **Devices on your WiFi** and click **That's mine** next to every device you recognise. Anything left over is worth checking.
4. Downloading something big? Scroll to **Boost a download**, click **Show running apps**, then **Boost this** next to your download app.

## Other ways to get it

### Build the .exe yourself (Windows, double-click)

Download this repo as a ZIP, unzip it, and double-click **build_exe.bat**. It installs Python if needed, builds the app and puts **WiFiFixer.exe** in the same folder. If it installs Python for you, it will ask you to double-click it once more.

### Run from source (Windows, Mac, Linux)

1. Install Python 3.8 or newer from https://www.python.org/downloads (on Windows, tick "Add Python to PATH").
2. In the repo folder, run:
   ```
   pip install -r requirements.txt
   python wifi_fixer.py
   ```
   On Windows you can instead just double-click **Run_WiFi_Fixer.bat**.
3. For the automatic fixes and Boost, run it as administrator (Windows) or with `sudo` (Mac and Linux).

Options: `--port 9000` changes the port, `--no-window` runs it without opening a window (then visit http://localhost:8765).

On Linux you also need `ip`, `ping` and `nmcli` (usually pre-installed) and `arp` from net-tools (`sudo apt install net-tools`).

## Publishing your own copy on GitHub

This repo builds the Windows app for you automatically.

1. Create a new repository on GitHub (name it `wifi-fixer`).
2. Upload everything from this folder, including the `.github` folder. Dragging the whole unzipped folder contents into the upload page works, or use git:
   ```
   git init
   git add .
   git commit -m "WiFi Fixer"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/wifi-fixer.git
   git push -u origin main
   ```
3. Open the **Actions** tab and wait about two minutes for "Build Windows exe" to finish (you can also press **Run workflow**).
4. Open **Releases**. **WiFiFixer.exe** is there. Share that link with anyone.

Every time you push a change to `main`, the .exe is rebuilt automatically.

## Safety and privacy

- The app only talks to your own router and network, plus Cloudflare's speed test servers for the speed test.
- It cannot and does not read other people's browsing history or traffic. It only shows which devices are connected.
- Only scan networks you own or have permission to scan.
- Boost frees up CPU and disk and pauses background downloaders. It cannot give one app a bigger share of the WiFi itself. To limit other devices, use QoS in your router settings.
- If Boost paused anything, closing the app or clicking Restore resumes it.
- Your trusted-device list and history are saved in `.wifi_fixer.json` in your home folder.

## Troubleshooting

| Problem | Fix |
|---|---|
| Windows or antivirus warns about the .exe | Click More info, then Run anyway. Apps made with PyInstaller are sometimes flagged. Running from source avoids this. |
| "Couldn't flush or change DNS" | Run as administrator (Windows) or with sudo (Mac and Linux). |
| My own phone shows as Unknown | Phones use a private MAC address. Click "That's mine" on it once. |
| Device list is short or empty | Make sure you are on the WiFi (not a VPN) and scan again. Sleeping devices may not answer. |
| No WiFi signal info | It only shows when you are connected over WiFi, not a cable. |
| Running apps list is empty | Run `pip install psutil`, or use the .exe which includes it. |
| Port already in use | Run `python wifi_fixer.py --port 9000`. |

## Project files

```
wifi_fixer.py        the whole app
build_exe.bat        double-click to build WiFiFixer.exe on Windows
Run_WiFi_Fixer.bat   double-click to run from source on Windows
requirements.txt     dependencies
.github/workflows/   builds the .exe automatically on GitHub
```

## License

MIT. See the LICENSE file. Contributions and ideas are welcome.
