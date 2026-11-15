#!/usr/bin/env python3
"""WiFi Fixer - no installs needed. Run:  python wifi_fixer.py  (Windows: py wifi_fixer.py)
Opens a local app at http://localhost:8765. Works on Windows, macOS and Linux."""
import ipaddress, json, os, platform, re, socket, statistics, subprocess, threading, time, urllib.request, uuid, webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
try:
    import psutil
except ImportError:
    psutil = None

OS, PORT = platform.system(), 8765
NOWIN = 0x08000000 if OS == "Windows" else 0
LAST, BOOST = [time.time()], {"target": None, "lowered": [], "paused": []}
HOGS = ("onedrive", "dropbox", "googledrivefs", "icloud", "megasync", "steam", "epicgames", "battle.net", "qbittorrent", "utorrent", "bittorrent", "backgroundtransfer", "tiworker", "musnotification", "creative cloud")
PROTECT = {"system", "idle", "system idle process", "explorer.exe", "svchost.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "lsass.exe", "registry"}
DB = os.path.join(os.path.expanduser("~"), ".wifi_fixer.json")
UA = {"User-Agent": "Mozilla/5.0 WiFiFixer"}
JOB = {"running": False, "step": "", "result": None, "error": None}

def load():
    try: return json.load(open(DB))
    except Exception: return {"trusted": {}, "target": 100, "history": []}
def save(d): json.dump(d, open(DB, "w"))
def run(cmd, t=15):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t, creationflags=NOWIN).stdout
    except Exception: return ""
def step(s): JOB["step"] = s

def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    except Exception: return "127.0.0.1"
    finally: s.close()

def gateway():
    if OS == "Windows": m = re.search(r"Default Gateway[ .]*:\s*(\d+\.\d+\.\d+\.\d+)", run("ipconfig"))
    elif OS == "Darwin": m = re.search(r"gateway:\s*(\S+)", run("route -n get default"))
    else: m = re.search(r"default via (\S+)", run("ip route"))
    return m.group(1) if m else None

def ping(host, n=6):
    out = run(f"ping -n {n} {host}" if OS == "Windows" else f"ping -c {n} {host}", n * 3 + 5)
    ts = [float(x) for x in re.findall(r"time[=<]\s*([\d.]+)\s*ms", out)]
    if not ts: return {"avg": None, "jitter": 0, "loss": 100}
    return {"avg": statistics.mean(ts), "jitter": statistics.pstdev(ts), "loss": round(100 * (n - len(ts)) / n)}

def dns_ms():
    ts = []
    for _ in range(3):
        t = time.time()
        try: socket.getaddrinfo(f"wf{os.urandom(4).hex()}.example.com", 80)
        except Exception: pass
        ts.append((time.time() - t) * 1000)
    return sum(ts) / 3

def wifi():
    d = {}
    if OS == "Windows":
        o = run("netsh wlan show interfaces")
        for k, p in (("ssid", r"^\s*SSID\s*:\s*(.+)$"), ("signal", r"Signal\s*:\s*(\d+)%"), ("channel", r"Channel\s*:\s*(\d+)"), ("rate", r"Receive rate.*?:\s*([\d.]+)")):
            m = re.search(p, o, re.M)
            if m: d[k] = m.group(1).strip()
        if "signal" in d: d["signal"] = int(d["signal"])
    elif OS == "Darwin":
        o = run("system_profiler SPAirPortDataType", 40)
        cur = o.split("Current Network Information:")[-1][:700] if "Current Network Information:" in o else ""
        m = re.search(r"Signal / Noise:\s*(-\d+)", cur)
        if m: d["signal"] = max(0, min(100, 2 * (int(m.group(1)) + 100)))
        m = re.search(r"Channel:\s*(\d+)", cur)
        if m: d["channel"] = m.group(1)
        m = re.search(r"Transmit Rate:\s*(\d+)", cur)
        if m: d["rate"] = m.group(1)
    else:
        for l in run("nmcli -t -f ACTIVE,SSID,SIGNAL,CHAN,RATE dev wifi").splitlines():
            if l.startswith("yes:"):
                p = l.split(":")
                try: d = {"ssid": p[1], "signal": int(p[2]), "channel": p[3], "rate": re.sub(r"[^\d.]", "", p[4])}
                except Exception: pass
    return d

def download(secs=8, threads=4):
    total, stop = [0], time.time() + secs
    def w():
        while time.time() < stop:
            try:
                with urllib.request.urlopen(urllib.request.Request("https://speed.cloudflare.com/__down?bytes=25000000", headers=UA), timeout=10) as r:
                    while time.time() < stop:
                        b = r.read(65536)
                        if not b: break
                        total[0] += len(b)
            except Exception: time.sleep(.2)
    t0 = time.time(); ths = [threading.Thread(target=w) for _ in range(threads)]
    [t.start() for t in ths]; [t.join() for t in ths]
    return total[0] * 8 / 1e6 / (time.time() - t0) if total[0] else None

def upload(secs=6, threads=3):
    sent, stop, data = [0], time.time() + secs, os.urandom(1_000_000)
    def w():
        while time.time() < stop:
            try:
                urllib.request.urlopen(urllib.request.Request("https://speed.cloudflare.com/__up", data=data, headers=UA), timeout=10).read(); sent[0] += len(data)
            except Exception: time.sleep(.2)
    t0 = time.time(); ths = [threading.Thread(target=w) for _ in range(threads)]
    [t.start() for t in ths]; [t.join() for t in ths]
    return sent[0] * 8 / 1e6 / (time.time() - t0) if sent[0] else None

def norm(mac): return ":".join(x.zfill(2).lower() for x in re.split(r"[:-]", mac))

def scan():
    ip, gw, db = local_ip(), gateway(), load()
    net = ipaddress.ip_network(ip + "/24", strict=False)
    def poke(h):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: s.sendto(b"x", (str(h), 9))
        except Exception: pass
        finally: s.close()
    for _ in range(2):  # sending any packet makes the OS ARP-resolve live devices
        with ThreadPoolExecutor(64) as ex: list(ex.map(poke, net.hosts()))
        time.sleep(1.2)
    found = {}
    for l in (run("arp -a") + "\n" + (run("ip neigh") if OS == "Linux" else "")).splitlines():
        m = re.search(r"(\d+\.\d+\.\d+\.\d+).*?\b([0-9a-fA-F]{1,2}(?:[:-][0-9a-fA-F]{1,2}){5})\b", l)
        if not m: continue
        a, mac = m.group(1), norm(m.group(2))
        try: inside = ipaddress.ip_address(a) in net and not a.endswith(".255")
        except Exception: continue
        if inside and mac != "ff:ff:ff:ff:ff:ff": found[a] = mac
    me = norm(":".join(f"{(uuid.getnode() >> s) & 255:02x}" for s in range(40, -1, -8)))
    found[ip] = me
    def host(a):
        try: return socket.gethostbyaddr(a)[0]
        except Exception: return ""
    ips = sorted(found, key=lambda x: ipaddress.ip_address(x))
    with ThreadPoolExecutor(16) as ex: names = list(ex.map(host, ips))
    out = []
    for a, hn in zip(ips, names):
        mac = found[a]
        out.append({"ip": a, "mac": mac, "host": hn, "me": a == ip, "router": a == gw, "name": db["trusted"].get(mac),
                    "random": bool(int(mac[:2], 16) & 2)})
    db = load(); seen = db.setdefault("seen", {}); first = not seen
    for d in out:
        d["new"] = (not first) and d["mac"] not in seen
        seen.setdefault(d["mac"], time.strftime("%d %b %H:%M"))
    save(db)
    return out

def diagnose(r):
    F = []
    def add(lv, t, d, f=""): F.append({"level": lv, "title": t, "detail": d, "fix": f})
    gw, net, w, down, t = r["gw_ping"], r["net_ping"], r["wifi"], r["down"], r["target"]
    unknown = [d for d in r["devices"] if not (d["me"] or d["router"] or d["name"])]
    if not down:
        if gw and gw["avg"] is None: add("bad", "Can't reach your router", "This device isn't getting through to the router at all.", "Check you're on the right network, move closer, then unplug the router for 30 seconds and plug it back in.")
        else: add("bad", "Router reachable, but no internet", "Your WiFi is fine; the connection out to the internet is down.", "Restart the modem/router. If it stays down, check your ISP's outage page or call them.")
        return F
    pct = down / t
    if pct >= .85: add("ok", "Speed is on target", f"{down:.0f} Mbps vs the {t:.0f} Mbps you expect.")
    else: add("bad" if pct < .5 else "warn", f"Slower than expected ({pct*100:.0f}% of target)", f"Got {down:.0f} Mbps, you expected {t:.0f}. Causes found below.")
    cause = False
    if gw and gw["avg"] is not None and (gw["avg"] > 15 or gw["loss"] > 0 or gw["jitter"] > 10):
        cause = True; add("warn", "Weak or congested link to your router", f"Router ping {gw['avg']:.0f} ms, {gw['loss']}% loss. The slowdown is inside your home WiFi, not your ISP.", "Move closer or remove walls/obstacles, use the 5 GHz band, keep the router off the floor and away from microwaves, or try a different channel.")
    if w.get("signal") is not None and w["signal"] < 50:
        cause = True; add("warn", "Low WiFi signal", f"Signal is {w['signal']}%.", "Get closer to the router or add a mesh node/extender.")
    try: ch = int(w.get("channel", 0))
    except Exception: ch = 0
    if 0 < ch <= 14:
        cause = True; add("warn", "You're on the crowded 2.4 GHz band", f"Channel {ch}. 2.4 GHz is slower and shared with neighbours and gadgets.", "Connect to the 5 GHz network if you have one." + (" Also set the router's 2.4 GHz channel to 1, 6 or 11." if ch not in (1, 6, 11) else ""))
    try:
        if w.get("rate") and float(w["rate"]) < t:
            cause = True; add("warn", "WiFi link speed is below your target", f"Your device is linked to the router at {w['rate']} Mbps, so it can't reach {t:.0f} Mbps.", "Get closer, switch to 5 GHz, or use an Ethernet cable.")
    except ValueError: pass
    if net["avg"] is not None and (net["avg"] > 100 or net["loss"] >= 2 or net["jitter"] > 30):
        cause = True; add("warn", "Unstable internet connection", f"Latency {net['avg']:.0f} ms, jitter {net['jitter']:.0f} ms, {net['loss']}% loss to the internet.", "If your router link looked fine, this points at your ISP or modem. Restart them and retest.")
    if r["dns"] > 150:
        cause = True; add("warn", "Slow DNS", f"Looking up addresses takes about {r['dns']:.0f} ms.", "Use the Flush DNS button, then set DNS to 1.1.1.1 or 8.8.8.8 in your router or device.")
    if unknown:
        cause = True; add("warn", f"{len(unknown)} device(s) not marked as yours", "Unknown devices can eat bandwidth. Check the list below and mark the ones you recognise.", "Anything you don't recognise: change your WiFi password.")
    s = r.get("sys")
    if s:
        if s["cpu"] > 85: cause = True; add("warn", "Your computer's CPU is maxed out", f"CPU is at {s['cpu']:.0f}%. That slows downloads and browsing however good the WiFi is.", "Close heavy apps (see the running apps list) or use Boost.")
        if s["ram"] > 90: cause = True; add("warn", "Your computer is almost out of memory", f"RAM is {s['ram']:.0f}% full, so everything swaps to disk and crawls.", "Close tabs/apps you're not using.")
        if s["disk"] > 95: cause = True; add("warn", "Your disk is nearly full", f"{s['disk']:.0f}% used. Downloads and the system slow down when there's no free space.", "Delete or move big files.")
        if s["hogs"]: cause = True; add("warn", "Background apps may be eating bandwidth", ", ".join(s["hogs"]) + " running. Sync, game and update apps download in the background.", "Use Boost to pause them while you download.")
    if pct < .85 and not cause:
        add("warn", "WiFi and router look healthy", "Nothing local is wrong, so the limit is probably your internet plan or ISP.", "Plug a cable straight into the router and retest. If it's still slow, contact your ISP.")
    return sorted(F, key=lambda f: {"bad": 0, "warn": 1, "ok": 2}[f["level"]])

def sh(cmd, t=30): return subprocess.run(cmd, shell=True, capture_output=True, timeout=t, creationflags=NOWIN).returncode

def sysinfo():
    if not psutil: return None
    hogs = sorted({p.info["name"] for p in psutil.process_iter(["name"]) if any(h in (p.info["name"] or "").lower() for h in HOGS)})
    return {"cpu": psutil.cpu_percent(interval=.7), "ram": psutil.virtual_memory().percent, "disk": psutil.disk_usage(os.path.abspath(os.sep)).percent, "hogs": hogs}

def procs(n=30):
    if not psutil: return []
    ps = []
    for p in psutil.process_iter(["pid", "name"]):
        try: p.cpu_percent(None); ps.append(p)
        except Exception: pass
    conns = {}
    try:
        for c in psutil.net_connections("inet"):
            if c.pid and c.status == "ESTABLISHED": conns[c.pid] = conns.get(c.pid, 0) + 1
    except Exception: pass
    time.sleep(.8); out = []
    for p in ps:
        try:
            nm = p.info["name"] or "?"
            out.append({"pid": p.pid, "name": nm, "cpu": p.cpu_percent(None) / (psutil.cpu_count() or 1), "mem": p.memory_info().rss / 1e6, "conns": conns.get(p.pid, 0), "hog": any(h in nm.lower() for h in HOGS)})
        except Exception: pass
    out.sort(key=lambda x: (x["hog"], x["conns"] > 0, x["cpu"], x["mem"]), reverse=True)
    return out[:n]

def restore():
    msgs = []
    if psutil:
        for pid in BOOST["paused"]:
            try: q = psutil.Process(pid); q.resume(); msgs.append(f"Resumed {q.name()}")
            except Exception: pass
        for pid, old in BOOST["lowered"]:
            try: psutil.Process(pid).nice(old)
            except Exception: pass
        if BOOST["target"]:
            try: psutil.Process(BOOST["target"][0]).nice(BOOST["target"][1]); msgs.append("Priorities back to normal")
            except Exception: pass
    BOOST.update(target=None, lowered=[], paused=[])
    return msgs or ["Nothing to restore, everything is already normal."]

def boost(pid, pause=True):
    if not psutil: raise RuntimeError("psutil isn't installed (pip install psutil, or use the .exe)")
    restore(); p = psutil.Process(pid); msgs = []
    tname = (p.name() or "").lower().split(".")[0]; kids = {c.pid for c in p.children(recursive=True)}
    BOOST["target"] = (pid, p.nice())
    try: p.nice(psutil.HIGH_PRIORITY_CLASS if OS == "Windows" else -10); msgs.append(f"{p.name()} set to high priority")
    except Exception: msgs.append(f"Couldn't raise {p.name()}'s priority (run as administrator / sudo)")
    for q in psutil.process_iter(["pid", "name"]):
        n = (q.info["name"] or "").lower()
        if pause and q.pid != pid and q.pid not in kids and tname not in n and any(h in n for h in HOGS):
            try: q.suspend(); BOOST["paused"].append(q.pid); msgs.append(f"Paused {q.info['name']}")
            except Exception: pass
    for x in procs(15):
        if x["cpu"] > 10 and x["pid"] not in kids | {pid, os.getpid()} and x["name"].lower() not in PROTECT:
            try:
                q = psutil.Process(x["pid"]); old = q.nice()
                q.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if OS == "Windows" else 10)
                BOOST["lowered"].append((x["pid"], old)); msgs.append(f"Slowed {x['name']} ({x['cpu']:.0f}% CPU)")
            except Exception: pass
    return msgs + ["Done. Hit Restore when your download finishes. Note: this frees CPU/disk and pauses background downloaders; other devices hogging the WiFi are fixed with QoS in your router."]

def autofix():
    r = JOB.get("result") if isinstance(JOB.get("result"), dict) else {}
    steps = [flushdns()["msg"]]
    if OS == "Windows":
        steps.append("Renewed your IP address." if sh("ipconfig /renew", 40) == 0 else "Couldn't renew IP (needs admin).")
        m = re.search(r"^\s*Name\s*:\s*(.+)$", run("netsh wlan show interfaces"), re.M)
        if r.get("dns", 0) > 150 and m:
            n = m.group(1).strip().replace('"', "")
            ok = sh(f'netsh interface ip set dns name="{n}" static 1.1.1.1') == 0 and sh(f'netsh interface ip add dns name="{n}" 8.8.8.8 index=2') == 0
            steps.append("Switched DNS to Cloudflare 1.1.1.1 / Google 8.8.8.8." if ok else "Couldn't change DNS (needs admin).")
    else: steps.append("On Mac/Linux only the DNS flush is automatic. Renew/DNS changes are in your network settings.")
    hogs = (r.get("sys") or {}).get("hogs")
    if hogs: steps.append("Background apps found: " + ", ".join(hogs) + ". Use Boost below to pause them.")
    if r.get("gw_ping") and r["gw_ping"].get("avg") and r["gw_ping"]["avg"] > 15: steps.append("Your link to the router is weak. I can't fix that in software: move closer, use 5 GHz, or restart the router.")
    return {"steps": steps}

def open_app(url):
    for c in ([r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"] if OS == "Windows" else []):
        if os.path.exists(c): subprocess.Popen([c, "--app=" + url, "--window-size=1000,820"]); return
    webbrowser.open(url)

def watchdog():
    while True:
        time.sleep(5)
        if time.time() - LAST[0] > 120 and not JOB["running"]: restore(); os._exit(0)

def full(target):
    gw = gateway(); r = {"target": target, "gateway": gw}
    step("Reading WiFi signal…"); r["wifi"] = wifi()
    step("Pinging your router…"); r["gw_ping"] = ping(gw) if gw else None
    step("Pinging the internet…"); r["net_ping"] = ping("1.1.1.1", 8)
    step("Testing DNS…"); r["dns"] = dns_ms()
    step("Testing download speed…"); r["down"] = download()
    step("Testing upload speed…"); r["up"] = upload()
    step("Scanning devices on your network…"); r["devices"] = scan()
    step("Checking your computer…"); r["sys"] = sysinfo()
    r["findings"] = diagnose(r)
    db = load(); db["target"] = target
    db["history"] = (db.get("history", []) + [{"t": time.strftime("%d %b %H:%M"), "down": r["down"], "up": r["up"], "ping": r["net_ping"]["avg"]}])[-20:]
    save(db); return r

def start(kind, fn):
    JOB.update(running=True, kind=kind, step="Starting…", result=None, error=None)
    def w():
        try: JOB["result"] = fn()
        except Exception as e: JOB["error"] = str(e)
        JOB["running"] = False
    threading.Thread(target=w, daemon=True).start()

def flushdns():
    cmd = {"Windows": "ipconfig /flushdns", "Darwin": "dscacheutil -flushcache"}.get(OS, "resolvectl flush-caches")
    ok = sh(cmd) == 0
    return {"msg": "DNS cache flushed." if ok else "Couldn't flush - try running the app as administrator (sudo on Mac/Linux)."}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def reply(self, obj, ct="application/json", code=200):
        b = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", ct); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        LAST[0] = time.time()
        if self.path == "/": self.reply(PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/api/state": db = load(); self.reply({"target": db.get("target", 100), "history": db.get("history", [])[-20:]})
        elif self.path == "/api/job": self.reply(JOB)
        elif self.path == "/api/ping": self.reply({})
        elif self.path == "/api/procs": self.reply(procs())
        else: self.reply({}, code=404)
    def do_POST(self):
        if self.headers.get("X-WF") != "1": return self.reply({}, code=403)
        b = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        db = load()
        if self.path == "/api/run":
            if JOB["running"]: return self.reply({"busy": True})
            if b.get("mode") == "scan": start("scan", scan)
            else: start("full", lambda: full(float(b.get("target") or 100)))
            return self.reply({"ok": True})
        if self.path == "/api/trust": db["trusted"][b["mac"]] = (b.get("name") or "My device")[:40]
        elif self.path == "/api/untrust": db["trusted"].pop(b["mac"], None)
        elif self.path == "/api/flushdns": return self.reply(flushdns())
        elif self.path in ("/api/boost", "/api/restore", "/api/fix", "/api/quit"):
            try:
                if self.path == "/api/quit": restore(); threading.Timer(.3, lambda: os._exit(0)).start(); return self.reply({})
                if self.path == "/api/boost": return self.reply({"msgs": boost(int(b["pid"]), b.get("pause", True))})
                if self.path == "/api/restore": return self.reply({"msgs": restore()})
                return self.reply(autofix())
            except Exception as e: return self.reply({"msgs": [f"Couldn't do that: {e}"], "steps": [f"Couldn't do that: {e}"]})
        save(db); self.reply({"ok": True})

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>WiFi Fixer</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#0f1420;--card:#192034;--tx:#e8ecf6;--mu:#8b95b0;--ok:#34d399;--warn:#fbbf24;--bad:#f87171;--ac:#6366f1}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px system-ui,sans-serif}
main{max-width:880px;margin:0 auto;padding:24px 16px 60px}h1{margin:0 0 4px}p.sub{color:var(--mu);margin:0 0 20px}
.card{background:var(--card);border-radius:14px;padding:16px;margin-bottom:16px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}label{font-size:12px;color:var(--mu);display:block;margin-bottom:4px}
input{background:#0f1420;border:1px solid #2b3552;color:var(--tx);border-radius:8px;padding:10px;font-size:16px;width:140px}
button{background:var(--ac);color:#fff;border:0;border-radius:8px;padding:10px 16px;font-size:15px;cursor:pointer}button.g{background:#2b3552}button:disabled{opacity:.5}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}.tile{background:#0f1420;border-radius:10px;padding:12px;border-left:4px solid #2b3552}
.tile.ok{border-color:var(--ok)}.tile.warn{border-color:var(--warn)}.tile.bad{border-color:var(--bad)}.lbl{font-size:12px;color:var(--mu)}.val{font-size:28px;font-weight:700}.unit{font-size:12px;color:var(--mu)}
.f{border-left:4px solid;padding:8px 12px;margin:8px 0;background:#0f1420;border-radius:6px}.f.ok{border-color:var(--ok)}.f.warn{border-color:var(--warn)}.f.bad{border-color:var(--bad)}.f b{display:block}.f small{color:var(--mu)}.f i{display:block;margin-top:4px;font-style:normal;color:#c7d2fe}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px 6px;border-bottom:1px solid #2b3552;font-size:13px}th{color:var(--mu);font-weight:500}
.tag{padding:2px 8px;border-radius:99px;font-size:12px}.tag.ok{background:#064e3b}.tag.unk{background:#78350f}.tag.me{background:#312e81}
#bar{color:var(--warn);margin-top:10px;min-height:20px}.hint{color:var(--mu);font-size:13px;margin-top:10px}[hidden]{display:none}
</style></head><body><main>
<h1>📶 WiFi Fixer <small style="font-size:12px;color:var(--mu)">v2.1</small></h1><p class="sub">Test your speed, find out why it's slow, and see who's on your network.</p>
<div class="card"><div class="row"><div><label>Speed you SHOULD be getting (Mbps)</label><input id="target" type="number" min="1" value="100"></div>
<button id="go" onclick="run('full')">Run full check</button><button class="g" id="sc" onclick="run('scan')">Scan devices only</button><button class="g" onclick="flush()">Flush DNS</button><button onclick="fix()" style="background:#059669">🔧 Fix it for me</button><button class="g" onclick="report()">📄 Save report</button><button class="g" onclick="api('/api/quit',{});document.body.textContent='WiFi Fixer closed. You can close this window.'">Quit</button></div>
<div id="bar"></div><div class="hint" id="out" style="white-space:pre-line"></div><div class="hint" id="hist"></div></div>
<div id="res" hidden><div class="card"><div class="tiles" id="stats"></div></div>
<div class="card" id="fcard"><h3 style="margin-top:0">Diagnosis</h3><div id="finds"></div></div>
<div class="card"><h3 style="margin-top:0">Devices on your WiFi <span id="dc" class="sub"></span></h3><div style="overflow-x:auto"><table id="dev"></table></div>
<div class="hint">Phones often use a private/random MAC address, so your own phone can show up as "unknown" until you mark it. Mark every device you recognise; anything left over is worth investigating. This tool shows devices that are connected, not what they're doing online.</div>
<div class="hint" id="adv" hidden>⚠️ Found something you don't recognise? Log into your router (usually 192.168.0.1 or 192.168.1.1), change the WiFi password to a strong WPA2/WPA3 one, turn off WPS, then reconnect your own devices.</div></div></div>
<div class="card"><h3 style="margin-top:0">⚡ Boost a download</h3><div class="hint" style="margin:0 0 10px">Pick the app that's downloading. It gets high priority, background sync/update apps (OneDrive, Dropbox, Steam…) are paused and other heavy apps are slowed. Hit Restore when you're done.</div>
<div class="row" style="margin-bottom:10px"><button class="g" onclick="loadProcs()">Show running apps</button><label style="margin:0 8px"><input type="checkbox" id="pz" checked style="width:auto"> Pause background hogs</label><button class="g" onclick="restore()">↩️ Restore everything</button></div>
<div style="overflow-x:auto"><table id="pr"></table></div></div>
<div class="hint" style="text-align:center;margin-top:28px">Made by <a href="https://averybeuth.xyz" target="_blank" style="color:#a5b4fc">averybeuth.xyz</a></div>
</main><script>
const $=s=>document.querySelector(s),h=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e};
const api=(p,b)=>fetch(p,b===undefined?{}:{method:"POST",headers:{"X-WF":"1","Content-Type":"application/json"},body:JSON.stringify(b)}).then(r=>r.json());
let DEV=[],timer,LASTR=null;
function loadState(){api("/api/state").then(s=>{if(!$("#target").dataset.set){$("#target").value=s.target;$("#target").dataset.set=1}spark(s.history)})}
function spark(H){const el=$("#hist");el.replaceChildren();H=H.filter(x=>x.down);if(H.length<2){el.textContent=H.length?"Last test: "+H[0].down.toFixed(0)+" Mbps":"";return}
 const m=Math.max(...H.map(x=>x.down),1),W=300,T=50,pts=H.map((x,i)=>(i*W/(H.length-1)).toFixed(0)+","+(T-x.down/m*(T-4)-2).toFixed(0)).join(" ");
 const NS="http://www.w3.org/2000/svg",sv=document.createElementNS(NS,"svg"),pl=document.createElementNS(NS,"polyline");sv.setAttribute("viewBox","0 0 "+W+" "+T);sv.setAttribute("width","300");
 pl.setAttribute("points",pts);pl.setAttribute("fill","none");pl.setAttribute("stroke","#6366f1");pl.setAttribute("stroke-width","2");sv.append(pl);
 el.append("Download history (last "+H.length+" tests, best "+m.toFixed(0)+" Mbps)",document.createElement("br"),sv)}
loadState();
function report(){if(!LASTR){out("Run a full check first, then save the report.");return}const r=LASTR,f=(x,n=0)=>x==null?"n/a":x.toFixed(n);
 const L=["WiFi Fixer report - "+new Date().toLocaleString(),"","Download: "+f(r.down,1)+" Mbps (target "+r.target+")","Upload: "+f(r.up,1)+" Mbps","Internet ping: "+f(r.net_ping.avg)+" ms, loss "+r.net_ping.loss+"%","","Diagnosis:",...r.findings.map(x=>"- ["+x.level+"] "+x.title+": "+x.detail+(x.fix?" Fix: "+x.fix:"")),"","Devices:",...DEV.map(d=>"- "+d.ip+"  "+d.mac+"  "+(d.name||d.host||"?")+(d.me||d.router||d.name?"":"  (UNKNOWN)"))];
 const a=h("a");a.href=URL.createObjectURL(new Blob([L.join("\n")],{type:"text/plain"}));a.download="wifi-report.txt";a.click()}
async function run(mode){const r=await api("/api/run",{mode,target:$("#target").value});if(r.busy)return;
 $("#go").disabled=$("#sc").disabled=true;timer=setInterval(poll,700)}
async function poll(){const j=await api("/api/job");$("#bar").textContent=j.running?"⏳ "+j.step:"";
 if(j.running)return;clearInterval(timer);$("#go").disabled=$("#sc").disabled=false;
 if(j.error){$("#bar").textContent="Error: "+j.error;return}
 if(j.kind==="scan"){$("#res").hidden=false;$("#stats").parentElement.hidden=$("#fcard").hidden=true;DEV=j.result;devs()}
 else{$("#stats").parentElement.hidden=$("#fcard").hidden=false;render(j.result);loadState()}}
function tile(l,v,u,c){const d=h("div","tile "+(c||""));d.append(h("div","lbl",l),h("div","val",v),h("div","unit",u));$("#stats").append(d)}
function render(r){LASTR=r;$("#res").hidden=false;$("#stats").replaceChildren();const f=(x,n=0)=>x==null?"–":x.toFixed(n),pct=r.down?r.down/r.target:0;
 tile("Download",f(r.down),"Mbps · target "+r.target,pct>=.85?"ok":pct>=.5?"warn":"bad");tile("Upload",f(r.up),"Mbps");
 tile("Internet ping",f(r.net_ping.avg),"ms · jitter "+f(r.net_ping.jitter)+" · loss "+r.net_ping.loss+"%");
 tile("Router ping",r.gw_ping?f(r.gw_ping.avg):"–","ms"+(r.gw_ping?" · loss "+r.gw_ping.loss+"%":""));
 tile("WiFi signal",r.wifi.signal!=null?r.wifi.signal+"%":"–",(r.wifi.channel?"channel "+r.wifi.channel:"")+(r.wifi.rate?" · "+r.wifi.rate+" Mbps link":""));
 tile("DNS lookup",f(r.dns),"ms");
 if(r.sys){tile("CPU",f(r.sys.cpu),"% used",r.sys.cpu>85?"bad":"ok");tile("Memory",f(r.sys.ram),"% used",r.sys.ram>90?"bad":"ok");tile("Disk",f(r.sys.disk),"% full",r.sys.disk>95?"bad":"ok")}
 const F=$("#finds");F.replaceChildren();for(const x of r.findings){const d=h("div","f "+x.level);d.append(h("b","",x.title),h("small","",x.detail));if(x.fix)d.append(h("i","","🔧 "+x.fix));F.append(d)}
 DEV=r.devices;devs()}
function devs(){const t=$("#dev");t.replaceChildren();const hr=h("tr");["IP","Device","MAC","Status",""].forEach(x=>hr.append(h("th","",x)));t.append(hr);let unk=0;
 for(const d of DEV){const tr=h("tr");const trusted=d.me||d.router||d.name;if(!trusted)unk++;
  const st=h("span","tag "+(d.me?"me":trusted?"ok":"unk"),d.me?"This computer":d.router?"Router":d.name?"Yours":d.new?"NEW device":"Unknown");
  const td=h("td");st.title=d.random?"Uses a private/random MAC":"";td.append(st);
  const b=h("button","g",d.name?"Untrust":"That's mine");b.style.padding="4px 10px";b.onclick=async()=>{if(d.name){await api("/api/untrust",{mac:d.mac});d.name=null}else{const n=prompt("Name this device (e.g. Mum's phone)");if(n===null)return;await api("/api/trust",{mac:d.mac,name:n});d.name=n||"My device"}devs()};
  tr.append(h("td","",d.ip),h("td","",d.name||d.host||"—"),h("td","",d.mac+(d.random?" (private)":"")),td,h("td"));if(!d.me&&!d.router)tr.lastChild.append(b);t.append(tr)}
 $("#dc").textContent="· "+DEV.length+" found, "+unk+" unknown";$("#adv").hidden=!unk}
async function flush(){const r=await api("/api/flushdns",{});$("#bar").textContent=r.msg}
const out=t=>$("#out").textContent=t;
async function fix(){out("Applying fixes…");const r=await api("/api/fix",{});out("🔧 "+r.steps.join("\n🔧 ")+"\n\nRun the full check again to see if it helped.")}
async function restore(){const r=await api("/api/restore",{});out("↩️ "+r.msgs.join("\n↩️ "))}
async function loadProcs(){out("Looking at running apps…");const P=await api("/api/procs");out(P.length?"":"Can't list apps (psutil missing). Use the .exe or pip install psutil.");const t=$("#pr");t.replaceChildren();
 const hr=h("tr");["App","CPU %","RAM MB","Connections",""].forEach(x=>hr.append(h("th","",x)));t.append(hr);
 for(const p of P){const tr=h("tr"),td=h("td"),b=h("button","g","Boost this");b.style.padding="4px 10px";
  b.onclick=async()=>{out("Boosting…");const r=await api("/api/boost",{pid:p.pid,pause:$("#pz").checked});out("⚡ "+r.msgs.join("\n⚡ "))};
  td.append(b);tr.append(h("td","",p.name+(p.hog?"  ⚠️ background hog":"")),h("td","",p.cpu.toFixed(0)),h("td","",p.mem.toFixed(0)),h("td","",p.conns),td);t.append(tr)}}
setInterval(()=>api("/api/ping"),5000);
</script></body></html>"""

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="WiFi Fixer")
    ap.add_argument("--port", type=int, default=PORT); ap.add_argument("--no-window", action="store_true", help="don't open the app window")
    A = ap.parse_args(); PORT = A.port
    try: srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    except OSError: open_app(f"http://localhost:{PORT}"); raise SystemExit
    print(f"WiFi Fixer running at http://localhost:{PORT}  (Ctrl+C to quit)")
    if not A.no_window: threading.Timer(.8, lambda: open_app(f"http://localhost:{PORT}")).start(); threading.Thread(target=watchdog, daemon=True).start()
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
