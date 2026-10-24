#!/usr/bin/env python3

Kali XFCE Desktop 
python3 kali.py → http://localhost:8080

import http.server, socketserver, subprocess, os, threading, json, uuid
import socket, platform, pwd
from urllib.parse import urlparse, parse_qs

PORT = 8080
SESSIONS = {}
LOCK = threading.Lock()
HOME = os.path.expanduser("~")

def spawn_shell(cmd_list, cwd):
sid = uuid.uuid4().hex[:12]
try:
proc = subprocess.Popen(" && ".join(cmd_list), shell=True, cwd=cwd,
stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
stdin=subprocess.DEVNULL, text=True, bufsize=1,
preexec_fn=os.setsid)
except Exception as ex:
return None, str(ex)
entry = {"proc": proc, "lines": [], "done": False, "exit": None, "cwd": cwd}
with LOCK: SESSIONS[sid] = entry

def reader():
try:
for line in proc.stdout:
with LOCK: entry["lines"].append(line.rstrip("\n"))
except Exception: pass
proc.wait()
with LOCK:
entry["exit"] = proc.returncode
entry["done"] = True
threading.Thread(target=reader, daemon=True).start()
return sid, None

class H(http.server.BaseHTTPRequestHandler):
protocol_version = "HTTP/1.1"
def _send(self, code, ctype, body, extra=None):
self.send_response(code)
self.send_header("Content-Type", ctype)
self.send_header("Content-Length", str(len(body)))
self.send_header("Cache-Control", "no-store")
if extra:
for k, v in extra.items(): self.send_header(k, v)
self.end_headers()
try: self.wfile.write(body)
except Exception: pass

def _json(self, obj, code=200):
self._send(code, "application/json", json.dumps(obj).encode())

def do_GET(self):
p = urlparse(self.path); path = p.path; q = parse_qs(p.query)
if path in ("/", "/index.html"):
return self._send(200, "text/html; charset=utf-8", HTML.encode())
if path == "/api/tail":
sid = q.get("sid", [""])[0]
off = int(q.get("off", ["0"])[0] or "0")
with LOCK:
e = SESSIONS.get(sid)
if not e: return self._json({"error": "no session"}, 404)
return self._json({"lines": e["lines"][off:], "done": e["done"],
"exit": e["exit"], "total": len(e["lines"])})
if path == "/api/sysinfo":
try: user = pwd.getpwuid(os.getuid()).pw_name
except Exception: user = os.environ.get("USER", "user")
return self._json({
"hostname": socket.gethostname(), "user": user,
"kernel": platform.release(), "arch": platform.machine(),
"python": platform.python_version(), "home": HOME,
"uid": os.getuid(), "pid": os.getpid(),
})
if path == "/api/wallpaper":
url = "https://www.kali.org/wallpapers/images/2024/kali-purple-whirlwind.jpg"
return self._send(302, "text/plain", b"", {"Location": url})
self._json({"error": "not found"}, 404)

def do_POST(self):
p = urlparse(self.path); path = p.path
ln = int(self.headers.get("Content-Length", "0") or "0")
try: body = json.loads(self.rfile.read(ln) or b"{}")
except Exception: body = {}

if path == "/api/exec":
cmds = body.get("cmds") or []
if isinstance(cmds, str): cmds = [cmds]
cwd = body.get("cwd") or HOME
if not cmds: return self._json({"error": "empty"}, 400)
if not os.path.isdir(cwd): cwd = HOME
sid, err = spawn_shell(cmds, cwd)
if err: return self._json({"error": err}, 500)
return self._json({"sid": sid})
if path == "/api/cd":
cwd = body.get("cwd") or HOME
tgt = (body.get("path") or "").replace("~", HOME)
if not tgt.startswith("/"): tgt = os.path.join(cwd, tgt)
tgt = os.path.normpath(tgt)
if os.path.isdir(tgt): return self._json({"cwd": tgt})
return self._json({"error": "not a dir"}, 400)
if path == "/api/ls":
pth = body.get("path") or HOME
try:
out = []
with os.scandir(pth) as it:
for e in it:
try: is_dir = e.is_dir(); sz = 0 if is_dir else e.stat().st_size
except Exception: is_dir, sz = False, 0
out.append({"name": e.name, "isDir": is_dir, "size": sz})
out.sort(key=lambda x: (not x["isDir"], x["name"].lower()))
return self._json({"path": pth, "files": out})
except Exception as ex: return self._json({"error": str(ex)}, 400)
if path == "/api/read":
fp = body.get("path") or ""
try:
with open(fp, "r", errors="replace") as f: data = f.read(200000)
return self._json({"content": data})
except Exception as ex: return self._json({"error": str(ex)}, 400)
if path == "/api/save":
fp = body.get("path") or ""; content = body.get("content") or ""
try:
d = os.path.dirname(fp)
if d and not os.path.isdir(d): os.makedirs(d, exist_ok=True)
with open(fp, "w") as f: f.write(content)
return self._json({"ok": True, "bytes": len(content)})
except Exception as ex: return self._json({"error": str(ex)}, 400)
if path == "/api/rename":
old = body.get("old") or ""; new = body.get("new") or ""
try:
os.rename(old, new)
return self._json({"ok": True})
except Exception as ex: return self._json({"error": str(ex)}, 400)
if path == "/api/run":
fp = body.get("path") or ""
ext = os.path.splitext(fp)[1].lower()
d = os.path.dirname(fp)
cmds = []
if ext == ".py":
cmds = [f"python3 '{fp}'"]
elif ext == ".cpp":
cmds = [f"g++ '{fp}' -o '{d}/out' && '{d}/out'"]
elif ext == ".c":
cmds = [f"gcc '{fp}' -o '{d}/out' && '{d}/out'"]
elif ext == ".jsx" or ext == ".js":
cmds = [f"node '{fp}'"]
elif ext == ".sh":
cmds = [f"bash '{fp}'"]
else:
cmds = [f"cat '{fp}'"]
sid, err = spawn_shell(cmds, d)
if err: return self._json({"error": err}, 500)
return self._json({"sid": sid})
self._json({"error": "not found"}, 404)

def log_message(self, *a): pass

class Threaded(socketserver.ThreadingMixIn, http.server.HTTPServer):
daemon_threads = True; allow_reuse_address = True

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Kali Linux — localhost</title>
<style>
:root {
--kali-bg: #1a1b26;
--accent: #4fa3d1;
--panel-bg: rgba(20, 22, 32, 0.92);
--text: #d0d0e0;
--border: #0f111a;
}
• { box-sizing: border-box; margin: 0; padding: 0; -webkit-user-select: none; user-select: none; }
html, body { height: 100%; overflow: hidden; cursor: none; }
body {
background: var(--kali-bg) url('/api/wallpaper') center/cover no-repeat fixed;
color: var(--text);
font-family: 'Cantarell', 'Segoe UI', 'Roboto', sans-serif;
height: 100vh; width: 100vw;
transition: background 0.5s ease;
}

/* === CUSTOM MOUSE CURSOR === */
#custom-cursor {
position: fixed; top: 0; left: 0;
width: 24px; height: 24px;
pointer-events: none; z-index: 9999;
background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="black" stroke="white" stroke-width="1.5"><path d="M3,2 L3,18 L8,13 L12,22 L14.5,20.5 L10.5,12 L18,12 Z"/></svg>');
background-size: contain; background-repeat: no-repeat;
transform: translate(-4px, -4px);
transition: transform 0.05s;
}
#custom-cursor.clicking { transform: translate(-4px, -4px) scale(0.85); }
.click-ripple {
position: fixed; pointer-events: none; z-index: 9998;
width: 30px; height: 30px; border: 2px solid white;
border-radius: 50%; transform: translate(-50%, -50%);
animation: ripple 0.4s ease-out forwards;
}
@keyframes ripple {
0% { opacity: 1; width: 10px; height: 10px; }
100% { opacity: 0; width: 40px; height: 40px; border-width: 0px; }
}

#top-panel {
position: fixed; top: 0; left: 0; right: 0; height: 32px;
background: var(--panel-bg); backdrop-filter: blur(12px);
border-bottom: 1px solid var(--border);
display: flex; align-items: center; padding: 0 12px;
z-index: 1000; font-size: 12px; color: #ddd;
box-shadow: 0 1px 8px rgba(0,0,0,0.6);
}
#start-btn {
display: flex; align-items: center; gap: 8px;
padding: 2px 8px; border-radius: 3px;
cursor: pointer; color: #fff; font-weight: 600;
}
#start-btn:hover { background: rgba(255,255,255,0.15); }
#start-btn .kali-logo { font-size: 16px; color: var(--accent); }

#panel-center { flex: 1; display: flex; gap: 6px; padding: 0 12px; }
.task-item {
padding: 4px 10px; border-radius: 3px;
background: rgba(255,255,255,0.05); color: #ccc;
font-size: 11px; cursor: pointer; white-space: nowrap;
border-bottom: 2px solid transparent;
}
.task-item:hover { background: rgba(255,255,255,0.12); }
.task-item.active { border-bottom-color: var(--accent); background: rgba(79,163,209,0.2); color: #fff; }

#panel-right { display: flex; align-items: center; gap: 14px; font-size: 11px; color: #ccc; }
#panel-clock { font-family: monospace; font-weight: 600; }

#start-menu {
position: fixed; top: 32px; left: 0;
width: 560px; max-height: calc(100vh - 80px);
background: #1e2029; border: 1px solid #0f1118;
box-shadow: 0 12px 40px rgba(0,0,0,0.85);
z-index: 999; display: none; overflow: hidden;
color: #ddd; font-size: 12px;
}
#start-menu.open { display: flex; flex-direction: column; }
.sm-top {
padding: 10px 16px; display: flex; gap: 10px; align-items: center;
border-bottom: 1px solid #111;
}
.sm-top .avatar { width: 32px; height: 32px; border-radius: 50%; background: #444; }
.sm-top .user { font-weight: bold; font-size: 13px; color: #fff; }
.sm-top .sub { font-size: 10px; color: #888; }
.sm-content { display: flex; flex: 1; min-height: 320px; max-height: 500px; }
.sm-sidebar { width: 130px; background: #181a22; padding: 8px 0; overflow-y: auto; }
.sm-side-item {
padding: 8px 16px; cursor: pointer; display: flex; align-items: center; gap: 8px;
font-size: 11px; color: #aaa;
}
.sm-side-item:hover { background: #222533; color: #fff; }
.sm-side-item.active { background: #2a2d3a; color: #fff; border-left: 3px solid var(--accent); }
.sm-side-item .dot { width: 6px; height: 6px; border-radius: 50%; background: #555; }
.sm-apps { flex: 1; padding: 12px; display: flex; flex-wrap: wrap; align-content: flex-start; gap: 8px; overflow-y: auto; background: #1b1d26; }

.sm-app {
width: 80px; height: 80px; display: flex; flex-direction: column; align-items: center; justify-content: center;
border-radius: 6px; cursor: pointer; gap: 6px; transition: background 0.1s;
}
.sm-app:hover { background: rgba(255,255,255,0.08); }
.sm-app .ic { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; }
.sm-app .ic img { width: 100%; height: 100%; object-fit: contain; }
.sm-app .nm { font-size: 10px; color: #ddd; text-align: center; width: 76px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.window {
position: absolute; min-width: 300px; min-height: 200px;
background: #1b1d26; border: 1px solid #0f1118;
box-shadow: 0 12px 40px rgba(0,0,0,0.85);
display: flex; flex-direction: column; z-index: 100; overflow: hidden;
resize: both;
}
.window.focused { box-shadow: 0 16px 50px rgba(0,0,0,0.95); }
.window.minimized { display: none; }
.titlebar {
height: 32px; background: #252836;
display: flex; align-items: center; padding: 0 10px;
cursor: move; border-bottom: 1px solid #0f1118;
font-size: 12px; color: #ccc; font-weight: 500;
touch-action: none;
}
.window.focused .titlebar { background: #2d3142; color: #fff; }
.titlebar .title { flex: 1; display: flex; align-items: center; gap: 6px; }
.titlebar .title::before { content: '□'; color: #888; font-size: 14px; }
.titlebar .btns { display: flex; gap: 4px; }
.titlebar .btn {
width: 22px; height: 22px; border-radius: 4px;
display: flex; align-items: center; justify-content: center;
font-size: 11px; cursor: pointer; color: #aaa;
}
.titlebar .btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
.btn-close:hover { background: #e53935 !important; color: #fff !important; }
.window .body { flex: 1; overflow: auto; background: #1b1d26; position: relative; }

.term-body {
padding: 10px 12px; font-family: 'JetBrains Mono', monospace;
font-size: 12px; line-height: 1.5; color: #d0d0e0;
white-space: pre-wrap; height: 100%; overflow-y: auto;
background: #14161d !important;
}
.term-body .pu { color: #5c9e6e; }
.term-body .pp { color: #4fa3d1; }
.term-body .ps { color: #c85555; }
.term-body .err { color: #e06c75; }
.term-body .ok { color: #98c379; }
.term-body .dim { color: #5c6370; }
.term-input {
background: transparent; border: none; outline: none;
color: #d0d0e0; font-family: inherit; font-size: inherit;
width: 60%; caret-color: #4fa3d1;
}

.fm-body { display: flex; flex-direction: column; height: 100%; background: #1b1d26; }
.fm-path {
padding: 8px 12px; background: #20232e; border-bottom: 1px solid #0f1118;
font-size: 12px; color: #ccc; font-family: monospace;
display: flex; gap: 8px; align-items: center;
}
.fm-path input {
flex: 1; background: #14161d; color: #ccc; border: 1px solid #2a2d3a;
border-radius: 3px; padding: 5px 8px; font-family: monospace; font-size: 12px; outline: none;
}
.fm-path button {
background: #4fa3d1; color: #000; border: none; padding: 5px 10px;
border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 11px;
}
.fm-list { flex: 1; overflow-y: auto; padding: 4px; }
.fm-item {
padding: 7px 10px; border-radius: 3px;
display: flex; align-items: center; gap: 8px;
cursor: pointer; font-size: 13px;
}
.fm-item:hover { background: rgba(80,140,220,0.2); }
.fm-item .fm-ico { font-size: 16px; width: 22px; text-align: center; }
.fm-item .fm-size { margin-left: auto; font-size: 11px; color: #666; }

.editor-body { display: flex; flex-direction: column; height: 100%; }
.editor-toolbar {
padding: 6px 10px; background: #20232e;
border-bottom: 1px solid #0f1118;
display: flex; gap: 8px; align-items: center; font-size: 12px;
}
.editor-toolbar input {
flex: 1; background: #14161d; color: #ccc; border: 1px solid #2a2d3a;
border-radius: 3px; padding: 5px 8px; font-family: monospace; font-size: 12px; outline: none;
}
.editor-toolbar button {
background: #98c379; color: #000; border: none; padding: 5px 12px;
border-radius: 3px; cursor: pointer; font-weight: bold; font-size: 11px;
}
.editor-body textarea {
flex: 1; width: 100%; background: #14161d; color: #d0d0d0;
border: none; outline: none; font-family: monospace;
font-size: 12px; padding: 12px; resize: none; line-height: 1.5;
}

.settings-body { padding: 16px; font-size: 12px; color: #ccc; display: flex; height: 100%; background: #1e2029; }
.set-sidebar { width: 140px; border-right: 1px solid #2a2d3a; padding-right: 10px; }
.set-side-item { padding: 8px; cursor: pointer; border-radius: 4px; color: #aaa; margin-bottom: 4px; }
.set-side-item:hover { background: #2a2d3a; color: #fff; }
.set-side-item.active { background: #2d3142; color: #fff; }
.set-content { flex: 1; padding-left: 16px; overflow-y: auto; }
.set-content h3 { color: #fff; font-size: 14px; margin-bottom: 10px; border-bottom: 1px solid #2a2d3a; padding-bottom: 6px; }
.set-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }

.wp-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px; }
.wp-item { width: 100%; height: 80px; border-radius: 4px; background-size: cover; background-position: center; border: 2px solid transparent; cursor: pointer; transition: border 0.2s; }
.wp-item:hover { border-color: rgba(255,255,255,0.5); }
.wp-item.active { border-color: var(--accent); box-shadow: 0 0 10px rgba(79,163,209,0.5); }

.google-body {
background: #202124; color: #e8eaed; height: 100%;
display: flex; flex-direction: column; align-items: center; padding-top: 80px;
}
.g-logo { font-size: 40px; font-weight: bold; letter-spacing: -2px; margin-bottom: 24px; }
.g-logo span:nth-child(1) { color: #4285F4; }
.g-logo span:nth-child(2) { color: #EA4335; }
.g-logo span:nth-child(3) { color: #FBBC05; }
.g-logo span:nth-child(4) { color: #4285F4; }
.g-logo span:nth-child(5) { color: #34A853; }
.g-logo span:nth-child(6) { color: #EA4335; }
.g-search { width: 100%; max-width: 500px; display: flex; gap: 8px; }
.g-search input {
flex: 1; padding: 10px 16px; border: 1px solid #5f6368; background: #202124;
border-radius: 20px; outline: none; font-size: 14px; color: #e8eaed;
}
.g-search input:focus { border-color: #8ab4f8; }
.g-search button {
background: #303134; color: #e8eaed; border: 1px solid #303134; padding: 0 20px; border-radius: 20px; cursor: pointer;
}

.cal-body { padding: 12px; height: 100%; background: #1e2029; display: flex; flex-direction: column; }
.cal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.cal-header button { background: transparent; border: none; color: #ccc; cursor: pointer; font-size: 16px; }
.cal-month { font-size: 16px; font-weight: 600; color: #fff; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; flex: 1; }
.cal-day-name { text-align: center; font-size: 11px; color: #888; padding-bottom: 6px; }
.cal-day { text-align: center; padding: 6px 0; border-radius: 50%; font-size: 12px; color: #ccc; aspect-ratio: 1; display: flex; align-items: center; justify-content: center; }
.cal-day.dim { color: #444; }
.cal-day.today { background: #4fa3d1; color: #000; font-weight: bold; }

.pkg-body { padding: 16px; background: #1b1d26; height: 100%; overflow-y: auto; }
.pkg-card {
background: #20232e; border: 1px solid #2a2d3a;
border-radius: 6px; padding: 12px; margin-bottom: 10px;
display: flex; align-items: center; gap: 12px;
}
.pkg-ico { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 26px; }
.pkg-ico img { width: 100%; height: 100%; object-fit: contain; }
.pkg-info { flex: 1; }
.pkg-name { font-weight: 700; color: #4fa3d1; font-size: 14px; }
.pkg-cmd { font-family: monospace; font-size: 11px; color: #888; margin-top: 3px; }
.pkg-btn {
background: #98c379; color: #000; border: none;
padding: 8px 16px; border-radius: 4px; font-weight: bold;
cursor: pointer; font-size: 12px;
}

#dock {
position: fixed; bottom: 0; left: 0; right: 0; height: 48px;
background: rgba(20, 22, 32, 0.85); backdrop-filter: blur(10px);
border-top: 1px solid #0f1118; z-index: 1000;
display: flex; justify-content: center; align-items: center; gap: 6px; padding: 0 16px;
}
.dock-app {
width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;
border-radius: 8px; cursor: pointer; font-size: 20px; color: #fff;
transition: transform 0.1s, background 0.1s;
}
.dock-app:hover { background: rgba(255,255,255,0.1); transform: translateY(-2px); }
.dock-app img { width: 28px; height: 28px; object-fit: contain; }
.dock-sep { width: 1px; height: 24px; background: #2a2d3a; margin: 0 6px; }

#ctx-menu {
position: fixed; background: #1e2029;
border: 1px solid #0f1118; border-radius: 4px;
box-shadow: 0 4px 16px rgba(0,0,0,0.8);
z-index: 2000; display: none; min-width: 180px;
}
#ctx-menu.open { display: block; }
.ctx-item { padding: 8px 16px; color: #ddd; font-size: 12px; cursor: pointer; }
.ctx-item:hover { background: rgba(79,163,209,0.3); color: #fff; }
.ctx-sep { height: 1px; background: #2a2d3a; margin: 4px 0; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #14161d; }
::-webkit-scrollbar-thumb { background: #3a4050; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #5c6370; }
</style>
</head>
<body>

<div id="custom-cursor"></div>

<div id="top-panel">
<div id="start-btn"><span class="kali-logo">🐉</span> Applications</div>
<div id="panel-center"></div>
<div id="panel-right">
<span>🌐</span><span>🔊</span><span>🔋</span>
<span id="panel-clock">00:00</span>
</div>
</div>

<div id="start-menu">
<div class="sm-top">
<div class="avatar"></div>
<div>
<div class="user">kali</div>
<div class="sub">root@kali</div>
</div>
</div>
<div class="sm-content">
<div class="sm-sidebar">
<div class="sm-side-item active"><span class="dot"></span> All Applications</div>
<div class="sm-side-item"><span class="dot"></span> Favorites</div>
</div>
<div class="sm-apps" id="sm-apps-container"></div>
</div>
</div>

<div id="desktop"></div>

<div id="ctx-menu">
<div class="ctx-item" onclick="openApp('terminal')">Open Terminal Here</div>
<div class="ctx-item" onclick="openApp('files')">Open in Files</div>
<div class="ctx-sep"></div>
<div class="ctx-item" onclick="openApp('settings')">System Info</div>
<div class="ctx-item" onclick="document.body.style.background = 'url(/api/wallpaper) center/cover no-repeat fixed'">Change Wallpaper</div>
</div>

<div id="dock">
<div class="dock-app" data-app="terminal" title="Terminal"><img src="https://cdn.freebiesupply.com/logos/large/2x/terminal-1-logo-png-transparent.png"></div>
<div class="dock-app" data-app="files" title="Files">📁</div>
<div class="dock-app" data-app="notepad" title="Notepad">📝</div>
<div class="dock-app" data-app="pkg" title="Packages">📦</div>
<div class="dock-app" data-app="google" title="Google">🌐</div>
<div class="dock-sep"></div>
<div class="dock-app" data-app="settings" title="Settings">⚙</div>
</div>

<script>
const API = "";
async function api(path, method="GET", body=null) {
const opt = { method, headers: {"Content-Type":"application/json"} };
if (body) opt.body = JSON.stringify(body);
const r = await fetch(API + path, opt);
return r.json();
}

// === CUSTOM CURSOR JS ===
const cursor = document.getElementById('custom-cursor');

function moveCursor(e) {
let x, y;
if (e.touches) {
x = e.touches[0].clientX;
y = e.touches[0].clientY;
} else {
x = e.clientX;
y = e.clientY;
}
cursor.style.left = x + 'px';
cursor.style.top = y + 'px';
}

document.addEventListener('mousemove', moveCursor);
document.addEventListener('touchmove', moveCursor, {passive: false});
document.addEventListener('touchstart', moveCursor, {passive: false});

function doClickEffect(e) {
cursor.classList.add('clicking');
setTimeout(() => cursor.classList.remove('clicking'), 150);

let x, y;
if (e.touches) { x = e.touches[0].clientX; y = e.touches[0].clientY; }
else { x = e.clientX; y = e.clientY; }

const ripple = document.createElement('div');
ripple.className = 'click-ripple';
ripple.style.left = x + 'px';
ripple.style.top = y + 'px';
document.body.appendChild(ripple);
setTimeout(() => ripple.remove(), 400);
}

document.addEventListener('mousedown', doClickEffect);
document.addEventListener('touchstart', (e) => { moveCursor(e); doClickEffect(e); }, {passive: false});

// ========== APPS ==========
const APPS = {
terminal: { name:"Terminal", icon:"<img src='https://cdn.freebiesupply.com/logos/large/2x/terminal-1-logo-png-transparent.png'>", w:760, h:480, render:renderTerminal },
rootterm: { name:"Root Terminal", icon:"<img src='https://www.kali.org/tools/shellnoob/images/shellnoob-logo.svg'>", w:760, h:480, render:(b,a)=>renderTerminal(b,a,true) },
files: { name:"Files", icon:"📁", w:720, h:500, render:renderFiles },
notepad: { name:"Text Editor", icon:"📝", w:640, h:460, render:renderNotepad },
google: { name:"Firefox", icon:"🌐", w:720, h:480, render:renderGoogle },
settings: { name:"Settings", icon:"⚙", w:600, h:450, render:renderSettings },
calendar: { name:"Calendar", icon:"📅", w:400, h:420, render:renderCalendar },
pkg: { name:"Packages", icon:"📦", w:600, h:500, render:renderPkg },

// Tools with Real Logos
msf: { name:"Metasploit", icon:"<img src='https://www.kali.org/tools/metasploit-framework/images/metasploit-framework-logo.svg'>", tool:true, cmds:["sudo apt update", "sudo apt install metasploit-framework -y"] },
edb: { name:"ExploitDB", icon:"<img src='https://gitlab.com/uploads/-/system/group/avatar/8033162/edb-spider-orange.png'>", tool:true, cmds:["sudo apt install exploitdb -y"] },
nmap: { name:"Nmap", icon:"<img src='https://nmap.org/images/nmap-logo-256x256.png'>", tool:true, cmds:["sudo apt update", "sudo apt install nmap -y"] },
fatrat: { name:"TheFatRat", icon:"🐀", tool:true, cmds:["git clone https://github.com/Screetsec/TheFatRat.git", "cd TheFatRat", "chmod +x setup.sh", "sudo ./setup.sh", "thefatrat"] },
pegasus: { name:"Pegasus-Xploit", icon:"🦅", tool:true, cmds:["git clone https://github.com/sobri3195/Pegasus-Xploit.git", "cd Pegasus-Xploit", "chmod +x install.sh", "./install.sh"] },

// Yeni Eklenen Toollar
maltego: { name:"Maltego", icon:"<img src='https://livengel.de/wp-content/uploads/2022/03/Maltego-Logo-Icon-Yellow-1.png'>", tool:true, cmds:["sudo apt install maltego"] },
reconng: { name:"Recon-NG", icon:"<img src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQsk9M6t_jkogQY4uEqymfyjeUBu-VPREEX-S6xUt3Mog&s'>", tool:true, cmds:["sudo apt install recon-ng"] },
netcat: { name:"Net-Cat", icon:"<img src='https://www.kali.org/tools/netcat/images/netcat-logo.svg'>", tool:true, cmds:["sudo apt install netcat-traditional"] },
hydra: { name:"Hydra", icon:"<img src='https://kryptera.se/wp-content/uploads/2016/06/hydra.png'>", tool:true, cmds:["sudo apt install hydra"] },
set: { name:"SEToolkit", icon:"<img src='https://www.kali.org/tools/set/images/set-logo.svg'>", tool:true, cmds:["git clone https://github.com/trustedsec/social-engineer-toolkit/ setoolkit", "cd setoolkit"] }
};

const SM_APPS = [
"terminal","rootterm","files","notepad","google","settings","calendar","pkg",
"msf","edb","nmap","fatrat","pegasus","maltego","reconng","netcat","hydra","set"
];

// ========== WINDOW MANAGER ==========
let winZ = 100;
const WIN = {};

function openApp(id) {
if (!APPS[id]) return;

if (APPS[id].tool) {
runTool(id);
return;
}

if (WIN[id]) {
if (WIN[id].minimized) { WIN[id].el.classList.remove("minimized"); WIN[id].minimized = false; }
focusApp(id); return;
}

const app = APPS[id];
const w = Math.min(app.w, innerWidth - 20);
const h = Math.min(app.h, innerHeight - 100);

const el = document.createElement("div");
el.className = "window";
el.style.cssText = width:${w}px;height:${h}px;left:${Math.max(40,Math.random()*(innerWidth-w-100)+40)}px;top:${Math.max(50,Math.random()*(innerHeight-h-100)+50)}px;z-index:${++winZ}; el.innerHTML =
<div class="titlebar">
<div class="title">${app.name}&lt;/div&gt; &lt;div class="btns"&gt; &lt;div class="btn btn-min"&gt;−&lt;/div&gt; &lt;div class="btn btn-max"&gt;□&lt;/div&gt; &lt;div class="btn btn-close"&gt;×&lt;/div&gt; &lt;/div&gt; &lt;/div&gt; &lt;div class="body"&gt;&lt;/div>;

document.body.appendChild(el);
const body = el.querySelector(".body");
app.render(body, el, id);

const tb = document.createElement("div");
tb.className = "task-item active";
tb.textContent = app.name;
tb.onclick = () => {
if (WIN[id].minimized) { el.classList.remove("minimized"); WIN[id].minimized = false; }
focusApp(id);
};
document.getElementById("panel-center").appendChild(tb);

WIN[id] = { el, tb, minimized:false };
makeDraggable(el, el.querySelector(".titlebar"));

el.addEventListener("mousedown", () => focusApp(id));
el.querySelector(".btn-close").onclick = e => { e.stopPropagation(); closeApp(id); };
el.querySelector(".btn-min").onclick = e => { e.stopPropagation(); WIN[id].el.classList.add("minimized"); WIN[id].minimized = true; };
el.querySelector(".btn-max").onclick = e => {
e.stopPropagation();
if (el.dataset.max === "1") {
el.style.left = el.dataset.ol; el.style.top = el.dataset.ot;
el.style.width = el.dataset.ow; el.style.height = el.dataset.oh;
el.dataset.max = "0";
} else {
el.dataset.ol = el.style.left; el.dataset.ot = el.style.top;
el.dataset.ow = el.style.width; el.dataset.oh = el.style.height;
el.style.left = "0px"; el.style.top = "32px";
el.style.width = "100vw"; el.style.height = "calc(100vh - 80px)";
el.dataset.max = "1";
}
};

focusApp(id);
document.getElementById("start-menu").classList.remove("open");
}

function runTool(id) {
const tool = APPS[id];
if (!WIN.terminal) {
openApp("terminal");
} else {
if (WIN.terminal.minimized) { WIN.terminal.el.classList.remove("minimized"); WIN.terminal.minimized = false; }
focusApp("terminal");
}

setTimeout(async () => {
const termBody = WIN.terminal.el.querySelector(".term-body");
const inputLine = termBody.querySelector(".term-input")?.parentElement;

const appendAndRun = async (cmds) => {
for (const c of cmds) {
const span = document.createElement("div");
span.innerHTML = <span class="ps"&gt;root@kali&lt;/span&gt;:&lt;span class="pp"&gt;~&lt;/span&gt;# ${c}`;
if (inputLine) termBody.insertBefore(span, inputLine);
else termBody.appendChild(span);
}

const r = await api("/api/exec", "POST", { cmds: cmds, cwd: null });
if (r.error) return;
const sid = r.sid;
let off = 0;
while (true) {
await new Promise(res => setTimeout(res, 150));
const t = await api("/api/tail?sid=" + sid + "&off=" + off);
if (t.error) break;
if (t.lines && t.lines.length) {
t.lines.forEach(l => {
const isErr = /error|fail|not found|denied|no such/i.test(l);
const div = document.createElement("div");
div.className = isErr ? "err" : "";
div.textContent = l;
if (inputLine) termBody.insertBefore(div, inputLine);
else termBody.appendChild(div);
});
off = t.total;
termBody.scrollTop = termBody.scrollHeight;
}
if (t.done) break;
}
};
appendAndRun(tool.cmds);
}, 300);
}

function focusApp(id) {
if (!WIN[id]) return;
WIN[id].el.style.zIndex = ++winZ;
Object.keys(WIN).forEach(k => {
WIN[k].el.classList.remove("focused");
WIN[k].tb.classList.remove("active");
});
WIN[id].el.classList.add("focused");
WIN[id].tb.classList.add("active");
}
function closeApp(id) {
if (!WIN[id]) return;
WIN[id].el.remove();
WIN[id].tb.remove();
delete WIN[id];
}

function makeDraggable(el, handle) {
let sx,sy,ox,oy;
const start = e => {
if (e.target.classList.contains("btn")) return;
const p = e.touches ? e.touches[0] : e;
sx=p.clientX; sy=p.clientY; ox=el.offsetLeft; oy=el.offsetTop;
document.addEventListener("mousemove", move);
document.addEventListener("mouseup", end);
document.addEventListener("touchmove", move, {passive:false});
document.addEventListener("touchend", end);
};
const move = e => {
const p = e.touches ? e.touches[0] : e;
el.style.left = (ox + p.clientX - sx) + "px";
el.style.top = (oy + p.clientY - sy) + "px";
if (e.touches) e.preventDefault();
};
const end = () => {
document.removeEventListener("mousemove", move);
document.removeEventListener("mouseup", end);
document.removeEventListener("touchmove", move);
document.removeEventListener("touchend", end);
};
handle.addEventListener("mousedown", start);
handle.addEventListener("touchstart", start, {passive:false});
}

// ========== START MENU ==========
function renderHome() {
const grid = document.getElementById("sm-apps-container");
grid.innerHTML = "";
SM_APPS.forEach(id => {
const app = APPS[id];
const el = document.createElement("div");
el.className = "sm-app";
el.innerHTML = <div class="ic"&gt;${app.icon}</div><div class="nm">${app.name}&lt;/div>;
el.onclick = () => openApp(id);
grid.appendChild(el);
});
}
renderHome();

document.getElementById("start-btn").onclick = (e) => {
e.stopPropagation();
document.getElementById("start-menu").classList.toggle("open");
};
document.addEventListener("click", e => {
if (!e.target.closest("#start-menu") && !e.target.closest("#start-btn")) {
document.getElementById("start-menu").classList.remove("open");
}
document.getElementById("ctx-menu").classList.remove("open");
});

document.querySelectorAll(".dock-app").forEach(el => {
el.onclick = () => openApp(el.dataset.app);
});

// Sağ tık menüsü
document.addEventListener("contextmenu", e => {
if (e.target.closest(".window") || e.target.closest("#top-panel") || e.target.closest("#dock")) return;
e.preventDefault();
const m = document.getElementById("ctx-menu");
m.style.left = e.clientX + "px";
m.style.top = e.clientY + "px";
m.classList.add("open");
});

// ========== CLOCK ==========
function tickClock() {
const d = new Date();
document.getElementById("panel-clock").textContent =
String(d.getHours()).padStart(2,"0") + ":" + String(d.getMinutes()).padStart(2,"0");
}
tickClock(); setInterval(tickClock, 10000);

// ============================================
// APP: TERMINAL (REAL)
// ============================================
function renderTerminal(body, win, winId) {
body.classList.add("term-body");
body.innerHTML = "";
let cwd = null;

function w(text, cls) {
const s = document.createElement("span");
if (cls) s.className = cls;
s.textContent = text;
body.appendChild(s);
body.scrollTop = body.scrollHeight;
}
function wline(t, cls) { w(t + "\n", cls); }

async function prompt() {
if (!cwd) {
const info = await api("/api/sysinfo");
cwd = info.home || "/";
}
const line = document.createElement("div");
line.style.marginTop = "4px";
line.innerHTML = <span class="ps"&gt;root@kali&lt;/span&gt;:&lt;span class="pp"&gt;${cwd.replace(/^.*//, '~')}</span># `;
const inp = document.createElement("input");
inp.className = "term-input";
inp.autocomplete = "off"; inp.spellcheck = false;
line.appendChild(inp);
body.appendChild(line);
inp.focus();
body.scrollTop = body.scrollHeight;

let hist = [], hi = 0;
inp.addEventListener("keydown", async e => {
if (e.key === "Enter") {
const c = inp.value.trim();
inp.disabled = true; inp.style.display = "none";
w(c + "\n");
if (!c) { prompt(); return; }
hist.push(c); hi = hist.length;

if (c === "clear" || c === "cls") { body.innerHTML = ""; prompt(); return; }
if (c === "exit" || c === "logout") { closeApp(winId); return; }
if (c === "cd" || c.startsWith("cd ")) {
const tgt = c.slice(2).trim() || "~";
const r = await api("/api/cd", "POST", { cwd, path: tgt });
if (r.cwd) cwd = r.cwd;
else wline("cd: " + (r.error || "failed"), "err");
prompt(); return;
}
try {
const r = await api("/api/exec", "POST", { cmds: [c], cwd });
if (r.error) { wline(r.error, "err"); prompt(); return; }
const sid = r.sid;
let off = 0;
while (true) {
await new Promise(res => setTimeout(res, 120));
const t = await api("/api/tail?sid=" + sid + "&off=" + off);
if (t.error) break;
if (t.lines && t.lines.length) {
t.lines.forEach(l => {
const isErr = /error|fail|not found|denied|no such/i.test(l);
wline(l, isErr ? "err" : "");
});
off = t.total;
}
if (t.done) {
if (t.exit !== null && t.exit !== 0) wline("[exit " + t.exit + "]", "dim");
break;
}
}
} catch (ex) {
wline("bridge error: " + ex.message, "err");
}
prompt();
} else if (e.key === "ArrowUp") {
e.preventDefault();
if (hi > 0) { hi--; inp.value = hist[hi]; }
} else if (e.key === "ArrowDown") {
e.preventDefault();
if (hi < hist.length - 1) { hi++; inp.value = hist[hi]; }
else { hi = hist.length; inp.value = ""; }
}
});
}

(async () => {
const info = await api("/api/sysinfo");
wline("Kali GNU/Linux 2024.1 · " + info.kernel, "dim");
wline("Termux Bridge aktif.", "dim");
wline("");
prompt();
})();
}

// ============================================
// APP: FILES (REAL + RUN + RENAME)
// ============================================
function renderFiles(body, win) {
body.classList.add("fm-body");
let cwd = null;
body.innerHTML = &lt;div class="fm-path"&gt; &lt;input id="fm-path" placeholder="/path" /&gt; &lt;button id="fm-go"&gt;Git&lt;/button&gt; &lt;/div&gt; &lt;div class="fm-list" id="fm-list"&gt;&lt;/div>;
const pathInp = body.querySelector("#fm-path");
const list = body.querySelector("#fm-list");

async function load(p) {
const r = await api("/api/ls", "POST", { path: p });
if (r.error) { list.innerHTML = <div style="color:#f55;padding:10px"&gt;${r.error}</div>; return; } cwd = r.path; pathInp.value = cwd; list.innerHTML = ""; if (cwd !== "/") { const par = cwd.replace(/\/[^/]+\/?$/, "") || "/";
const it = document.createElement("div");
it.className = "fm-item";
it.innerHTML = <span class="fm-ico"&gt;↩&lt;/span&gt;&lt;span&gt;..&lt;/span>;
it.onclick = () => load(par);
list.appendChild(it);
}
r.files.forEach(f => {
const full = (cwd === "/" ? "" : cwd) + "/" + f.name;
const it = document.createElement("div");
it.className = "fm-item";
const sz = f.isDir ? "" : fmtSize(f.size);
it.innerHTML = <span class="fm-ico"&gt;${f.isDir ? "📁" : "📄"}</span><span>${f.name}&lt;/span&gt;&lt;span class="fm-size"&gt;${sz}</span>`;

it.onclick = () => {
if (f.isDir) { load(full); return; }
const ext = f.name.split('.').pop().toLowerCase();
if (['py','cpp','c','jsx','js','sh'].includes(ext)) {
openApp('terminal');
setTimeout(async () => {
const termBody = WIN.terminal.el.querySelector('.term-body');
const inputLine = termBody.querySelector('.term-input')?.parentElement;

const span = document.createElement("div");
span.innerHTML = <span class="ps"&gt;root@kali&lt;/span&gt;:&lt;span class="pp"&gt;~&lt;/span&gt;# ./${f.name}`;
if (inputLine) termBody.insertBefore(span, inputLine);
else termBody.appendChild(span);

const r = await api("/api/run", "POST", { path: full });
if (r.error) return;
let off = 0;
while(true) {
await new Promise(res => setTimeout(res, 150));
const t = await api("/api/tail?sid=" + r.sid + "&off=" + off);
if (t.lines && t.lines.length) {
t.lines.forEach(l => {
const d = document.createElement("div");
d.textContent = l;
if (inputLine) termBody.insertBefore(d, inputLine);
else termBody.appendChild(d);
});
off = t.total;
termBody.scrollTop = termBody.scrollHeight;
}
if (t.done) break;
}
}, 300);
} else {
openApp("notepad");
setTimeout(() => {
const ed = WIN.notepad?.controller;
if (ed && ed.openFile) ed.openFile(full);
}, 300);
}
};

it.oncontextmenu = e => {
e.preventDefault(); e.stopPropagation();
const newName = prompt("Yeni isim (" + f.name + "):", f.name);
if (newName && newName !== f.name) {
const newPath = (cwd === "/" ? "" : cwd) + "/" + newName;
api("/api/rename", "POST", { old: full, new: newPath }).then(() => load(cwd));
}
};

list.appendChild(it);
});
}
function fmtSize(n) {
if (n < 1024) return n + "B";
if (n < 1048576) return (n/1024).toFixed(1) + "K";
return (n/1048576).toFixed(1) + "M";
}

body.querySelector("#fm-go").onclick = () => load(pathInp.value);
pathInp.addEventListener("keydown", e => { if (e.key === "Enter") load(pathInp.value); });

(async () => {
const info = await api("/api/sysinfo");
load(info.home || "/");
})();
}

// ============================================
// APP: NOTEPAD
// ============================================
function renderNotepad(body, win) {
body.classList.add("editor-body");
body.innerHTML = &lt;div class="editor-toolbar"&gt; &lt;input id="ed-path" placeholder="/path/to/file.txt" /&gt; &lt;button id="ed-open"&gt;Aç&lt;/button&gt; &lt;button id="ed-save"&gt;Kaydet&lt;/button&gt; &lt;/div&gt; &lt;textarea id="ed-content" spellcheck="false" placeholder="type here..."&gt;&lt;/textarea>;
const pathInp = body.querySelector("#ed-path");
const content = body.querySelector("#ed-content");

async function openFile(p) {
pathInp.value = p;
const r = await api("/api/read", "POST", { path: p });
if (r.error) { content.value = "// ERROR: " + r.error; return; }
content.value = r.content;
}
async function saveFile() {
const p = pathInp.value.trim();
if (!p) { alert("path boş"); return; }
const r = await api("/api/save", "POST", { path: p, content: content.value });
if (r.error) alert("save: " + r.error);
else alert("Kaydedildi: " + p);
}
body.querySelector("#ed-open").onclick = () => openFile(pathInp.value.trim());
body.querySelector("#ed-save").onclick = saveFile;

win.controller = { openFile };
}

// ============================================
// APP: SETTINGS (Wallpapers)
// ============================================
function renderSettings(body, win) {
body.classList.add("settings-body");

const wallpapers = [
"https://www.kali.org/wallpapers/images/2024/kali-purple-whirlwind.jpg",
"https://www.kali.org/wallpapers/images/2024/kali-ferrofluid.jpg",
"https://www.kali.org/wallpapers/images/2023/kali-red-sticker.jpg",
"https://www.kali.org/wallpapers/images/2023/kali-moto.png",
"https://www.kali.org/wallpapers/images/2025/kali-tiles.jpg",
"https://www.kali.org/wallpapers/images/2026/kali-net.jpg"
 ];

body.innerHTML = &lt;div class="set-sidebar"&gt; &lt;div class="set-side-item active" data-tab="app"&gt;Appearance&lt;/div&gt; &lt;div class="set-side-item" data-tab="wp"&gt;Wallpapers&lt;/div&gt; &lt;div class="set-side-item" data-tab="sys"&gt;System Info&lt;/div&gt; &lt;/div&gt; &lt;div class="set-content" id="set-content"&gt;&lt;/div>;

const content = body.querySelector("#set-content");

function renderTab(tab) {
if (tab === "app") {
content.innerHTML = &lt;h3&gt;Appearance&lt;/h3&gt; &lt;div class="set-row"&gt;&lt;span&gt;Theme&lt;/span&gt;&lt;select&gt;&lt;option&gt;Kali-Dark&lt;/option&gt;&lt;option&gt;Breeze&lt;/option&gt;&lt;/select&gt;&lt;/div&gt; &lt;div class="set-row"&gt;&lt;span&gt;Icons&lt;/span&gt;&lt;select&gt;&lt;option&gt;Flat-Remix&lt;/option&gt;&lt;option&gt;Papirus&lt;/option&gt;&lt;/select&gt;&lt;/div&gt;;
} else if (tab === "wp") {
let html = <h3&gt;Wallpapers&lt;/h3&gt;&lt;div class="wp-grid">;
wallpapers.forEach(w => {
html += <div class="wp-item" style="background-image:url('${w}')" data-url="${w}"&gt;&lt;/div>;
});
html += </div>;
content.innerHTML = html;

content.querySelectorAll(".wp-item").forEach(el => {
el.onclick = () => {
document.body.style.background = var(--kali-bg) url('${el.dataset.url}') center/cover no-repeat fixed; content.querySelectorAll(".wp-item").forEach(x =&gt; x.classList.remove("active")); el.classList.add("active"); }; }); } else if (tab === "sys") { content.innerHTML =<h3>System Info</h3><div style="color:#888">Yükleniyor...</div>; api("/api/sysinfo").then(info =&gt; { content.innerHTML =
<h3>System Info</h3>
<div class="set-row"><span>Hostname</span><span style="color:#4fa3d1">${info.hostname}&lt;/span&gt;&lt;/div&gt; &lt;div class="set-row"&gt;&lt;span&gt;User&lt;/span&gt;&lt;span style="color:#4fa3d1"&gt;${info.user}</span></div>
<div class="set-row"><span>Kernel</span><span style="color:#4fa3d1">${info.kernel}&lt;/span&gt;&lt;/div&gt; &lt;div class="set-row"&gt;&lt;span&gt;Arch&lt;/span&gt;&lt;span style="color:#4fa3d1"&gt;${info.arch}</span></div>`;
});
}
}
renderTab("app");

body.querySelectorAll(".set-side-item").forEach(el => {
el.onclick = () => {
body.querySelectorAll(".set-side-item").forEach(x => x.classList.remove("active"));
el.classList.add("active");
renderTab(el.dataset.tab);
};
});
}

// ============================================
// APP: GOOGLE
// ============================================
function renderGoogle(body, win) {
body.classList.add("google-body");
body.innerHTML = &lt;div class="g-logo"&gt;&lt;span&gt;G&lt;/span&gt;&lt;span&gt;o&lt;/span&gt;&lt;span&gt;o&lt;/span&gt;&lt;span&gt;g&lt;/span&gt;&lt;span&gt;l&lt;/span&gt;&lt;span&gt;e&lt;/span&gt;&lt;/div&gt; &lt;div class="g-search"&gt; &lt;input id="g-q" placeholder="Search..." autocomplete="off"/&gt; &lt;button id="g-go"&gt;Ara&lt;/button&gt; &lt;/div>;
const q = body.querySelector("#g-q");
body.querySelector("#g-go").onclick = () => {
const v = q.value.trim(); if (!v) return;
window.open("https://www.google.com/search?q=" + encodeURIComponent(v), "_blank");
};
q.addEventListener("keydown", e => { if (e.key === "Enter") body.querySelector("#g-go").click(); });
}

// ============================================
// APP: CALENDAR
// ============================================
function renderCalendar(body, win) {
body.classList.add("cal-body");
const d = new Date();
let curMonth = d.getMonth(), curYear = d.getFullYear();
const months = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"];
const days = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"];

function render() {
body.innerHTML = &lt;div class="cal-header"&gt; &lt;button id="cal-prev"&gt;‹&lt;/button&gt; &lt;div class="cal-month"&gt;${months[curMonth]} ${curYear}&lt;/div&gt; &lt;button id="cal-next"&gt;›&lt;/button&gt; &lt;/div&gt; &lt;div class="cal-grid" id="cal-grid"&gt;&lt;/div>;

days.forEach(day => {
const el = document.createElement("div");
el.className = "cal-day-name"; el.textContent = day;
body.querySelector("#cal-grid").appendChild(el);
});

const first = new Date(curYear, curMonth, 1);
const last = new Date(curYear, curMonth+1, 0);
let startDay = first.getDay() - 1; if (startDay === -1) startDay = 6;

for(let i=0; i<startDay; i++) {
const el = document.createElement("div"); el.className = "cal-day dim"; el.textContent = "—";
body.querySelector("#cal-grid").appendChild(el);
}
for(let i=1; i<=last.getDate(); i++) {
const el = document.createElement("div"); el.className = "cal-day"; el.textContent = i;
if (i === d.getDate() && curMonth === d.getMonth() && curYear === d.getFullYear()) el.classList.add("today");
body.querySelector("#cal-grid").appendChild(el);
}

body.querySelector("#cal-prev").onclick = () => { curMonth--; if(curMonth<0){curMonth=11;curYear--;} render(); };
body.querySelector("#cal-next").onclick = () => { curMonth++; if(curMonth>11){curMonth=0;curYear++;} render(); };
}
render();
}

// ============================================
// APP: PACKAGES
// ============================================
function renderPkg(body, win) {
body.classList.add("pkg-body");
const pkgs = [
{ id:"c", ico:"<img src='https://upload.wikimedia.org/wikipedia/commons/1/19/C_Logo.png'>", name:"C (gcc)", cmd:"pkg install -y clang" },
{ id:"cpp", ico:"<img src='https://thumb.wikimedia.org/wikipedia/commons/thumb/1/18/ISO_C%2B%2B_Logo.svg/1280px-ISO_C%2B%2B_Logo.svg.png'>", name:"C++ (g++)", cmd:"pkg install -y clang" },
{ id:"py", ico:"🐍", name:"Python 3", cmd:"pkg install -y python" },
 ];

let html = <h3 style="color:#ee0000;margin-bottom:14px;border-bottom:1px solid #3a4050;padding-bottom:8px"&gt;Termux Paketleri (Gerçek)&lt;/h3>;
pkgs.forEach(p => {
html += &lt;div class="pkg-card" id="pkg-${p.id}">
<div class="pkg-ico">{p.name}</div>
<div class="pkg-cmd">{p.cmd}</div>
</div>
<button class="pkg-btn" data-id="{p.cmd}">Kur</button>
</div>`;
});
body.innerHTML = html;

body.querySelectorAll(".pkg-btn").forEach(btn => {
btn.onclick = async () => {
const cmd = btn.dataset.cmd;
btn.textContent = "Kuruluyor...";
btn.disabled = true;

openApp("terminal");
setTimeout(async () => {
const termBody = WIN.terminal.el.querySelector('.term-body');
const inputLine = termBody.querySelector('.term-input')?.parentElement;

const span = document.createElement("div");
span.innerHTML = <span class="ps"&gt;root@kali&lt;/span&gt;:&lt;span class="pp"&gt;~&lt;/span&gt;# ${cmd};
if (inputLine) termBody.insertBefore(span, inputLine);
else termBody.appendChild(span);

const r = await api("/api/exec", "POST", { cmds: [cmd] });
if (r.error) return;
let off = 0;
while(true) {
await new Promise(res => setTimeout(res, 200));
const t = await api("/api/tail?sid=" + r.sid + "&off=" + off);
if (t.lines && t.lines.length) {
t.lines.forEach(l => {
const d = document.createElement("div");
d.textContent = l;
if (inputLine) termBody.insertBefore(d, inputLine);
else termBody.appendChild(d);
});
off = t.total;
termBody.scrollTop = termBody.scrollHeight;
}
if (t.done) {
btn.textContent = "Kuruldu ✓";
btn.style.background = "#888";
break;
}
}
}, 300);
};
});
}

// ========== BOOT ==========
setTimeout(() => openApp("terminal"), 300);
</script>
</body>
</html>"""

if name == "main":
print(f"\033[1;31m[Kali]\033[0m Desktop v7 at http://localhost:{PORT}")
print("\033[1;33m[CTRL+C]\033[0m to stop")
srv = Threaded(("0.0.0.0", PORT), H)
try: srv.serve_forever()
except KeyboardInterrupt:
print("\n\033[1;31m[Kali]\033[0m stopped")
srv.shutdown()