# WiFi Fixer

Slow internet? WiFi Fixer finds out why, fixes what it can, and shows you who is connected to your WiFi. It is free, needs no account, and nothing leaves your computer.

## Download (Windows)

1. Go to the [latest release](../../releases/latest).
2. Click **WiFiFixer.exe** to download it.
3. Double-click it and click **Yes** when Windows asks for permission.

That is it. No install and no extra software needed.

**Windows says "Windows protected your PC"?** Click **More info**, then **Run anyway**. Small free apps are not code-signed, so Windows warns about them. The full source code is in this repo if you want to check it.

**Why does it ask for administrator permission?** The one-click fixes (clearing DNS, changing DNS) and Boost mode need it to work.

Using a Mac or Linux? See [Mac and Linux](#mac-and-linux) below.

## What it does

- **Speed test against your target.** Enter the speed you pay for. It measures download, upload, ping, jitter, packet loss and DNS speed.
- **Plain-English diagnosis.** It tells you if the problem is weak WiFi signal, the crowded 2.4 GHz band, a bad link to your router, your internet provider, slow DNS, or your own computer running out of CPU, memory or disk space.
- **Fix it for me.** One button that clears your DNS cache, renews your IP address, and switches to faster DNS when yours is slow.
- **See who is on your WiFi.** Lists every connected device. Mark your own with "That's mine". Anything else shows as Unknown, and brand-new devices are marked NEW.
- **Boost a download.** Pick the app that is downloading. It gets high priority, background sync and update apps (OneDrive, Dropbox, Steam and similar) are paused, and other heavy apps are slowed down. Click "Restore everything" when you are done.
- **Live network monitor.** Watch your real download and upload speed second by second, and watch the speed test run live with a progress checklist.
- **Network allocation by app.** See which apps are using your connection right now, with a bar for each. Windows does not give exact per-app numbers, so these are estimates.
- **History and reports.** See your speed over time and save a text report to send to your internet provider.

## How to use it

1. Type the speed you should be getting (for example 100) and click **Run full check**. It takes about 30 seconds.
2. Read the **Diagnosis**. Every problem comes with a suggested fix. Click **Fix it for me** to apply the automatic ones.
3. Look at **Devices on your WiFi** and click **That's mine** next to each device you recognise. Anything left over is worth checking.
4. Downloading something big? Scroll to **Network allocation by app** and click **Boost** next to the app that is downloading.

## What the results mean

| You see | What it means | What to do |
|---|---|---|
| Weak or congested link to your router | The slowdown is inside your home | Move closer to the router, use the 5 GHz network, or restart the router |
| Router fine but internet slow or unstable | The problem is past your router | Restart your modem, then contact your internet provider and send them the saved report |
| Slow DNS | Websites take a long time to start loading | Click Fix it for me |
| CPU, memory or disk warning | Your computer is the bottleneck | Close heavy apps or free up disk space |
| Unknown or NEW device | A device you have not marked as yours is connected | Mark it if it is yours. If not, change your WiFi password |

## Mac and Linux

1. Install Python 3.8 or newer from https://www.python.org/downloads
2. On this page click the green **Code** button, then **Download ZIP**, and unzip it.
3. Open a terminal in the unzipped folder and run:
   ```
   pip3 install -r requirements.txt
   python3 wifi_fixer.py
   ```
4. For the automatic fixes and Boost, run it with `sudo python3 wifi_fixer.py`.

On Linux you also need `ping`, `ip` and `nmcli` (usually already installed) and `arp` from net-tools (`sudo apt install net-tools`).

Windows users who prefer not to use the .exe can install Python and double-click **Run_WiFi_Fixer.bat** instead.

## Privacy and safety

- The app only talks to your own router and network, plus Cloudflare's speed test servers when you run the speed test.
- It cannot read other people's browsing history or traffic. It only shows which devices are connected.
- Only scan networks you own or have permission to scan.
- Boost frees up CPU and disk and pauses background downloaders. It cannot give one app a bigger share of the WiFi itself. To limit other devices, use QoS in your router settings.
- If Boost paused anything, clicking Restore or closing the app resumes it.
- Your trusted-device list and history are saved in a file called `.wifi_fixer.json` in your home folder.

## Troubleshooting

| Problem | Fix |
|---|---|
| Windows or antivirus warns about the file | Click More info, then Run anyway. Apps built with PyInstaller are sometimes flagged by mistake. |
| "Couldn't flush or change DNS" | Run the app as administrator (Windows) or with sudo (Mac and Linux). |
| My own phone shows as Unknown | Phones use a private address that changes. Click "That's mine" on it once. |
| Device list is short or empty | Make sure you are connected to the WiFi (not a VPN) and scan again. Sleeping devices may not answer. |
| No WiFi signal info | It only shows when you are connected over WiFi, not a cable. |
| Running apps list is empty | Use the .exe, or run `pip install psutil` if you are running from source. |
| Port already in use | Run `python wifi_fixer.py --port 9000` |

Found a bug or have an idea? Open an issue on this repo.

## For developers

`wifi_fixer.py` is the whole app (Python standard library, plus optional `psutil`). Run `build_exe.bat` on Windows to build `WiFiFixer.exe` yourself. Options: `--port 9000`, `--no-window`.

## Made by

Check out more of my projects at **[averybeuth.xyz](https://averybeuth.xyz)**.

## License

MIT. See the LICENSE file.
