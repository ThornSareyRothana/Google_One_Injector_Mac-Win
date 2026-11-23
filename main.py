# -*- coding: utf-8 -*-
"""
Google One Subscription Injector (English Edition)

Usage:
  python main.py
  python main.py --plan helium_1m
  python main.py --stack --plan pro_6m
"""
from __future__ import annotations

import argparse
import glob
import lzma
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BIN = REPO / "bin"
JS_PATH = HERE / "frida.js"

PKG = "com.google.android.apps.subscriptions.red"
ACT = PKG + "/com.google.android.apps.subscriptions.red.main.MainActivity"
DEX_REMOTE = "/data/local/tmp/module_521.apk"
FRIDA_REMOTE = "/data/local/tmp/frida-server"

ABI_ASSET = {
    "arm64-v8a": "android-arm64",
    "armeabi-v7a": "android-arm",
    "x86_64": "android-x86_64",
    "x86": "android-x86",
}

GROUPS = [
    ("Plus", [
        "helium_12m", "helium_6m", "helium_3m", "helium_1m", "helium_3m_75",
        "plus_6m", "plus_3m", "plus_2tb_6m", "plus_2tb_85",
        "yt_1m", "yt_family", "yt_lite",
    ]),
    ("Pro", [
        "pro_12m", "pro_6m", "pro_6m_2", "pro_6m_ss", "pro_play_3m",
        "pro_3m_75",
        "pro10_1m_90", "pro10_3m_85",
    ]),
    ("Ultra 5x", [
        "ultra20_3m_90", "ultra20_3m_80", "ultra20_3m_75",
    ]),
    ("Ultra 20x", [
        "ultra_1m_90", "ultra_3m_90", "ultra_3m_80", "ultra_1m_75", "ultra_3m_75",
    ]),
]


def _fix_stdio():
    if sys.platform != "win32":
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def info(msg):
    print(f"[*] {msg}", flush=True)


def ok(msg):
    print(f"[+] {msg}", flush=True)


def warn(msg):
    print(f"[!] {msg}", flush=True)


def fail(msg):
    print(f"[x] {msg}", flush=True)


EMU_PORTS = (
    7555, 7556, 16384, 16416, 16448, 16480, 16385,
    5555, 5554, 5556, 5560, 62001, 21503,
)


def download_adb_if_needed():
    local_bin = HERE / "bin"
    adb_local = local_bin / "adb.exe"
    if adb_local.is_file():
        return str(adb_local)
    info("adb not found on system. Auto-downloading Google Platform Tools...")
    import zipfile
    url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    zip_dest = HERE / "platform-tools.zip"
    try:
        local_bin.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, zip_dest)
        with zipfile.ZipFile(zip_dest, "r") as z:
            for member in z.namelist():
                if member.startswith("platform-tools/"):
                    fname = member[len("platform-tools/"):]
                    if fname:
                        target = local_bin / fname
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if not member.endswith("/"):
                            with z.open(member) as source, open(target, "wb") as out:
                                shutil.copyfileobj(source, out)
        if zip_dest.is_file():
            zip_dest.unlink()
        if adb_local.is_file():
            ok(f"adb successfully downloaded to {adb_local}")
            return str(adb_local)
    except Exception as e:
        warn(f"Failed to auto-download adb: {e}")
    return "adb"


def find_adb_exe():
    exe = shutil.which("adb")
    if exe:
        return exe
    extras = [
        str(HERE / "bin" / "adb.exe"),
        str(REPO / "bin" / "adb.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        r"C:\Android\sdk\platform-tools\adb.exe",
        r"D:\SDK\platform-tools\adb.exe",
        r"E:\SDK\platform-tools\adb.exe",
    ]
    extras += glob.glob(r"C:\Program Files\Netease\*\*\adb.exe")
    extras += glob.glob(r"D:\Program Files\Netease\*\*\adb.exe")
    extras += glob.glob(r"C:\Program Files\MuMu*\**\adb.exe", recursive=True)
    extras += glob.glob(r"D:\Program Files\MuMu*\**\adb.exe", recursive=True)
    for p in extras:
        if p and os.path.isfile(p):
            return p
    return download_adb_if_needed()


class Adb:
    def __init__(self, serial=""):
        self.exe = find_adb_exe()
        self.serial = serial or os.environ.get("ANDROID_SERIAL") or ""

    def _cmd(self, args, serial=None, timeout=None):
        cmd = [self.exe]
        s = self.serial if serial is None else serial
        if s:
            cmd += ["-s", s]
        return subprocess.run(
            cmd + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )

    def run(self, args, serial=None):
        return self._cmd(args, serial=serial)

    def shell(self, *parts):
        r = self._cmd(["shell", *parts])
        return ((r.stdout or "") + (r.stderr or "")).strip()

    def devices(self):
        rows = []
        out = self._cmd(["devices"], serial="").stdout
        for ln in out.splitlines()[1:]:
            bits = ln.split()
            if len(bits) >= 2 and bits[-1] == "device":
                rows.append(bits[0])
        return rows

    def _restart_server(self):
        info("Restarting adb server...")
        self._cmd(["kill-server"], serial="")
        time.sleep(0.8)
        self._cmd(["start-server"], serial="")
        time.sleep(1.0)

    def _connect_emulators(self):
        for port in EMU_PORTS:
            r = self._cmd(["connect", f"127.0.0.1:{port}"], serial="")
            text = ((r.stdout or "") + (r.stderr or "")).strip()
            if "connected" in text.lower() or "already" in text.lower():
                ok(f"adb connect 127.0.0.1:{port}")

    def _fingerprint(self, serial):
        r = self._cmd(["shell", "settings", "get", "secure", "android_id"], serial=serial)
        aid = (r.stdout or "").strip()
        if aid and aid not in ("null", "error"):
            return aid
        r = self._cmd(["shell", "getprop", "ro.serialno"], serial=serial)
        return (r.stdout or "").strip() or serial

    def _dedupe(self, serials):
        best = {}
        order = []
        for s in serials:
            key = self._fingerprint(s)
            if key not in best:
                best[key] = s
                order.append(key)
                continue
            cur = best[key]
            prefer = (s.startswith("emulator-") and not cur.startswith("emulator-")) or (
                cur.startswith("127.0.0.1:") and not s.startswith("127.0.0.1:")
            )
            if prefer:
                best[key] = s
        return [best[k] for k in order]

    def _score(self, serial):
        score = 0
        old = self.serial
        self.serial = serial
        try:
            if "uid=0" in (self.shell("su", "-c", "id") + self.shell("su", "0", "id")):
                score += 10
            if "package:" in self.shell("pm", "path", PKG):
                score += 5
            if google_accounts():
                score += 3
        finally:
            self.serial = old
        return score

    def discover(self):
        info(f"adb binary: {self.exe}")
        rows = self.devices()
        if not rows:
            self._restart_server()
            rows = self.devices()
        if not rows:
            info("No device found, scanning emulator ports (MuMu / LDPlayer / Nox)...")
            self._connect_emulators()
            time.sleep(0.6)
            rows = self.devices()
        if not rows:
            info("Waiting for device to come online...")
            try:
                self._cmd(["wait-for-device"], serial="", timeout=15)
            except subprocess.TimeoutExpired:
                pass
            time.sleep(1.0)
            self._connect_emulators()
            rows = self.devices()
        rows = self._dedupe(rows)
        if not rows:
            fail("No available adb device found. Start emulator or enable USB debugging.")
            sys.exit(1)
        return rows

    def pick(self):
        rows = self.discover()
        if self.serial and self.serial in rows:
            ok(f"Selected device: {self.serial}")
            return self.serial
        if self.serial and self.serial not in rows:
            warn(f"Specified {self.serial} offline, auto-selecting...")
        if len(rows) == 1:
            self.serial = rows[0]
        else:
            ranked = sorted(rows, key=self._score, reverse=True)
            self.serial = ranked[0]
            info("Multiple devices found, selecting highest priority:")
            for s in ranked:
                info(f"  {s}  score={self._score(s)}")
        os.environ["ANDROID_SERIAL"] = self.serial
        ok(f"Active device: {self.serial}")
        return self.serial


adb = Adb()


def parse_plans(js_text):
    """Parse PLANS from frida.js so the menu stays in sync with the hook."""
    block = re.search(r"var PLANS = \{([\s\S]*?)\n\};", js_text)
    if not block:
        return {}
    plans = {}
    for m in re.finditer(
        r"(\w+)\s*:\s*\{\s*sku:\s*\"([^\"]+)\"\s*,\s*offer:\s*\"([^\"]+)\"\s*,\s*note:\s*\"([^\"]*)\"",
        block.group(1),
    ):
        plans[m.group(1)] = {"sku": m.group(2), "offer": m.group(3), "note": m.group(4)}
    return plans


def grouped_plans(plans):
    used = set()
    groups = []
    for title, ids in GROUPS:
        items = [(pid, plans[pid]) for pid in ids if pid in plans]
        if items:
            groups.append((title, items))
            used.update(pid for pid, _ in items)
    extra = [(pid, plans[pid]) for pid in plans if pid not in used]
    if extra:
        groups.append(("Other", extra))
    return groups


def flatten_menu(groups):
    rows = []
    for title, items in groups:
        for pid, spec in items:
            rows.append((title, pid, spec))
    return rows


def print_menu(plans, stack, addon):
    groups = grouped_plans(plans)
    rows = flatten_menu(groups)
    mode_desc = "STACK / RENEW (Replace & stack onto existing subscription)" if stack else "NEW PURCHASE (Standard flow)"
    print()
    print("=" * 70)
    print("  Google One Subscription Injector")
    print(f"  Mode :  {mode_desc}")
    print(f"  Addon:  {addon or 'None'}")
    print("=" * 70)
    n = 1
    index = {}
    for title, items in groups:
        print(f"\n  [{title}]")
        for pid, spec in items:
            print(f"  {n:2d}. {pid:<16} {spec['note']}")
            index[str(n)] = pid
            index[pid] = pid
            n += 1
    print()
    print("-" * 70)
    print("  Commands:")
    print("  [1-28] Select plan by number or plan ID to launch checkout")
    print("  s      Toggle Stack/Renew mode (Requires existing Google One subscription)")
    print("  a      Set YouTube Premium add-on")
    print("  r / g  Restart Google One app and re-attach Frida")
    print("  e      Re-check device environment")
    print("  l      Refresh plan menu")
    print("  q      Quit")
    print("-" * 70)
    return index, rows


# ── environment ──────────────────────────────────────────────────────────────

def host_frida_version():
    try:
        import frida
        return getattr(frida, "__version__", "") or ""
    except Exception:
        pass
    exe = shutil.which("frida")
    if not exe:
        return ""
    r = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or r.stderr or "").strip().split()[0]


def ensure_host_frida():
    ver = host_frida_version()
    if ver and ver == "17.9.1":
        ok(f"Host Frida version: {ver}")
        return ver
    if not ver:
        warn("Frida not found on host, installing frida==17.9.1 frida-tools==14.8.1...")
    else:
        info(f"Host Frida {ver} detected (aligning with pre-cached frida-server 17.9.1)...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "frida==17.9.1", "frida-tools==14.8.1"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if r.returncode != 0:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "frida", "frida-tools"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    ver = host_frida_version()
    if not ver:
        fail("Installed frida-tools but frida binary still not detected in PATH.")
        sys.exit(1)
    ok(f"Host Frida version: {ver}")
    return ver


def device_abi():
    abi = adb.shell("getprop", "ro.product.cpu.abi") or ""
    return abi.splitlines()[0].strip() if abi else ""


def has_root():
    if "uid=0" in adb.shell("id"):
        return True
    out = adb.shell("su", "-c", "id")
    if "uid=0" in out:
        return True
    out = adb.shell("su", "0", "id")
    return "uid=0" in out


def google_accounts():
    out = adb.shell("dumpsys", "account")
    names = re.findall(r"Account \{name=([^,}]+),\s*type=com\.google", out or "")
    if names:
        return [n.strip() for n in names]
    names = re.findall(r"type=com\.google[^\n]*name=([^\s,\}]+)", out or "")
    return [n.strip() for n in names]


def su_sh(cmd):
    # MuMu on macOS can already run adbd as root, without a working su.
    if "uid=0" in adb.shell("id"):
        r = adb.run(["shell", cmd])
        return ((r.stdout or "") + (r.stderr or "")).strip()
    escaped = cmd.replace("'", "'\\''")
    r = adb.run(["shell", f"su -c '{escaped}'"])
    text = ((r.stdout or "") + (r.stderr or "")).strip()
    bad = r.returncode != 0 or "inaccessible" in text or "not found" in text.lower()
    if bad:
        r = adb.run(["shell", f"su 0 sh -c '{escaped}'"])
        text = ((r.stdout or "") + (r.stderr or "")).strip()
    return text


def remote_exists(path):
    out = adb.shell("ls", path)
    return "No such" not in out and path.split("/")[-1] in out


def ensure_module():
    if remote_exists(DEX_REMOTE):
        ok(f"module_521.apk present on device: {DEX_REMOTE}")
        return
    info("Pushing embedded dex (module_521.apk) to device...")
    try:
        from module_b64 import MODULE_B64
    except Exception as e:
        fail(f"Failed to read module_b64.py: {e}")
        sys.exit(1)
    import base64
    tmp = Path(tempfile.gettempdir()) / "module_521.apk"
    tmp.write_bytes(base64.b64decode(MODULE_B64))
    r = adb.run(["push", str(tmp), DEX_REMOTE])
    print((r.stdout or r.stderr or "").strip(), flush=True)
    adb.shell("chmod", "644", DEX_REMOTE)
    if not remote_exists(DEX_REMOTE):
        fail("Failed to push module_521.apk")
        sys.exit(1)
    ok("module_521.apk installed to device")


def _xz_to_file(xz_path, dest):
    data = lzma.open(xz_path).read()
    dest.write_bytes(data)
    return dest


def local_frida_server(abi_tag):
    named = [
        HERE / "assets" / f"frida-server-{abi_tag}",
        BIN / f"frida-server-{abi_tag}",
    ]
    for p in named:
        if p.is_file() and p.stat().st_size > 1024 * 1024:
            return p
    generic = BIN / "frida-server"
    if abi_tag == "android-x86_64" and generic.is_file() and generic.stat().st_size > 1024 * 1024:
        return generic
    cache = HERE / "assets"
    cache.mkdir(exist_ok=True)
    unpacked = cache / f"frida-server-{abi_tag}"
    if unpacked.is_file() and unpacked.stat().st_size > 1024 * 1024:
        return unpacked
    xz_candidates = [
        HERE / "assets" / f"frida-server-{abi_tag}.xz",
        BIN / f"frida-server-{abi_tag}.xz",
    ]
    if abi_tag == "android-x86_64":
        xz_candidates.append(BIN / "frida-server-x86_64.xz")
    for xz in xz_candidates:
        if not xz.is_file():
            continue
        info(f"Extracting {xz.name}...")
        return _xz_to_file(xz, unpacked)
    return None


def download_frida_server(ver, abi_tag):
    cache = HERE / "assets"
    cache.mkdir(exist_ok=True)
    name = f"frida-server-{ver}-{abi_tag}.xz"
    url = f"https://github.com/frida/frida/releases/download/{ver}/{name}"
    xz = cache / name
    info(f"Downloading {url}...")
    try:
        urllib.request.urlretrieve(url, xz)
    except Exception as e:
        fail(f"Download failed: {e}")
        return None
    dest = cache / f"frida-server-{ver}-{abi_tag}"
    return _xz_to_file(xz, dest)


def remote_frida_version():
    if not remote_exists(FRIDA_REMOTE):
        return ""
    out = adb.shell(FRIDA_REMOTE, "--version") or su_sh(f"{FRIDA_REMOTE} --version")
    m = re.search(r"(\d+\.\d+\.\d+)", out or "")
    return m.group(1) if m else ""


def start_remote_frida():
    su_sh(f"chmod 755 {FRIDA_REMOTE}")
    su_sh("killall -9 frida-server 2>/dev/null || true")
    time.sleep(0.5)
    su_sh(f"{FRIDA_REMOTE} -D >/dev/null 2>&1 &")
    time.sleep(1.2)
    running = (adb.shell("pidof", "frida-server") or su_sh("pidof frida-server") or "").strip()
    if not running:
        adb.run(["shell", f"su 0 sh -c '{FRIDA_REMOTE} -D >/dev/null 2>&1 &'"])
        time.sleep(1.2)
        running = (adb.shell("pidof", "frida-server") or su_sh("pidof frida-server") or "").strip()
    return running


def ensure_frida_server(ver):
    abi = device_abi()
    abi_tag = ABI_ASSET.get(abi, "")
    if not abi_tag:
        fail(f"Unrecognized device ABI: {abi!r}")
        sys.exit(1)
    info(f"Device ABI: {abi} -> {abi_tag}")

    remote_ver = remote_frida_version()
    running = (adb.shell("pidof", "frida-server") or "").strip()
    if running and remote_ver == ver:
        ok(f"frida-server {remote_ver} already running (pid={running.split()[0]})")
        return

    if remote_ver and remote_ver != ver:
        warn(f"Device frida-server ({remote_ver}) differs from host ({ver}), updating...")

    local = None
    cache = HERE / "assets" / f"frida-server-{ver}-{abi_tag}"
    if cache.is_file() and cache.stat().st_size > 1024 * 1024:
        local = cache
    if local is None:
        local = download_frida_server(ver, abi_tag)
    if local is None:
        local = local_frida_server(abi_tag)
    if local is None:
        fail("Cannot find or download matching frida-server. Place it in assets/ or ../bin/")
        sys.exit(1)

    if running:
        su_sh("killall -9 frida-server 2>/dev/null || true")
        time.sleep(0.5)

    info(f"Pushing {local.name} ({ver}) -> {FRIDA_REMOTE}")
    r = adb.run(["push", str(local), FRIDA_REMOTE])
    print((r.stdout or r.stderr or "").strip(), flush=True)

    running = start_remote_frida()
    if not running:
        fail("Failed to start frida-server. Root access is required.")
        sys.exit(1)
    ok(f"frida-server {ver} started (pid={running.split()[0]})")


def ensure_google_one():
    path = adb.shell("pm", "path", PKG)
    if "package:" in path:
        ok("Google One app verified installed")
        return
    fail("Google One app not found (com.google.android.apps.subscriptions.red)")
    fail("Please install Google One from the Play Store first.")
    sys.exit(1)


def ensure_google_account():
    accts = google_accounts()
    if accts:
        ok(f"Google Account: {', '.join(accts)}")
        return accts
    fail("No Google account found logged in. Please sign in via Settings or Play Store.")
    sys.exit(1)


def ensure_root():
    if has_root():
        ok("Root access verified")
        return
    fail("Root access check failed (su failed). Root is required.")
    sys.exit(1)


def print_env(ver):
    accts = google_accounts()
    print()
    print("-" * 64)
    print("  Environment Status")
    print("-" * 64)
    print(f"  Device        : {adb.serial}")
    print(f"  ABI           : {device_abi() or '?'}")
    print(f"  Root          : {'YES' if has_root() else 'NO'}")
    print(f"  Google Account: {', '.join(accts) if accts else 'None'}")
    print(f"  Host Frida    : {ver or 'None'}")
    print(f"  frida-server  : {(adb.shell('pidof', 'frida-server') or 'Not running').split()[0]}")
    print(f"  module_521    : {'Ready' if remote_exists(DEX_REMOTE) else 'Missing'}")
    g1 = "Installed" if "package:" in adb.shell("pm", "path", PKG) else "Missing"
    print(f"  Google One    : {g1}")
    print("-" * 64)


def ensure_env():
    adb.pick()
    ensure_root()
    ensure_google_account()
    ensure_google_one()
    ver = ensure_host_frida()
    ensure_module()
    ensure_frida_server(ver)
    print_env(ver)
    return ver


# ── Google One + Frida session ───────────────────────────────────────────────

def g1_pid():
    return (adb.shell("pidof", PKG) or "").split()[:1]


def wake():
    adb.shell("input", "keyevent", "224")
    adb.shell("wm", "dismiss-keyguard")


def start_google_one():
    wake()
    adb.shell("am", "force-stop", PKG)
    time.sleep(1.2)
    adb.shell("am", "start", "-n", ACT)
    adb.shell("monkey", "-p", PKG, "-c", "android.intent.category.LAUNCHER", "1")
    pid = ""
    for _ in range(40):
        time.sleep(0.35)
        got = g1_pid()
        if got:
            pid = got[0]
            break
    if not pid:
        fail("Google One app failed to start.")
        sys.exit(1)
    time.sleep(2.5)
    pid = (g1_pid() or [pid])[0]
    ok(f"Google One running (pid={pid})")
    return int(pid)


def post_frida_bridge(script, name):
    try:
        import frida_tools
        root = Path(frida_tools.__file__).resolve().parent / "bridges"
    except Exception as e:
        fail(f"Cannot find frida_tools/bridges: {e}")
        return False
    stem = (name or "java").lower()
    for p in root.glob("*.js"):
        if p.stem.lower() == stem:
            script.post({
                "type": "frida:bridge-loaded",
                "filename": p.name,
                "source": p.read_text(encoding="utf-8"),
            })
            return True
    fail(f"Frida bridge not found: {stem}")
    return False


class Session:
    def __init__(self):
        self.device = None
        self.session = None
        self.script = None
        self.ready = threading.Event()
        self.last_ev = ""
        self.lock = threading.Lock()

    def _on_message(self, message, _data):
        if message.get("type") == "error":
            fail(message.get("stack") or message.get("description") or str(message))
            return
        if message.get("type") != "send":
            return
        payload = message.get("payload") or {}
        if isinstance(payload, dict) and payload.get("type") == "frida:load-bridge":
            info(f"Loading Frida bridge: {payload.get('name')}")
            post_frida_bridge(self.script, payload.get("name") or "java")
            return
        if not isinstance(payload, dict):
            print(payload, flush=True)
            return
        ev = payload.get("ev") or ""
        with self.lock:
            self.last_ev = ev
        bits = [ev] if ev else []
        for k, v in payload.items():
            if k == "ev" or v in ("", None):
                continue
            bits.append(f"{k}={v}")
        print("[g1] " + "  ".join(str(x) for x in bits), flush=True)
        if ev == "ready":
            self.ready.set()
        if ev == "launched":
            code = str(payload.get("code", ""))
            if code == "0":
                ok("Checkout sheet launched! Check device screen to confirm (will not auto-subscribe).")
            else:
                warn(f"launchBillingFlow returned code={code} {payload.get('msg', '')}")

    def attach(self, pid):
        import frida
        self.ready.clear()
        mgr = frida.get_device_manager()
        dev = None
        for d in mgr.enumerate_devices():
            if d.id == adb.serial:
                dev = d
                break
        if dev is None:
            dev = frida.get_usb_device(timeout=8)
        self.device = dev
        info(f"Attaching Frida to pid={pid}...")
        self.session = dev.attach(pid)
        js = JS_PATH.read_text(encoding="utf-8")
        try:
            import frida_tools
            java_js = Path(frida_tools.__file__).resolve().parent / "bridges" / "java.js"
            if java_js.is_file():
                js = java_js.read_text(encoding="utf-8") + "\n;var Java = bridge;\n" + js
                info("Embedded frida-java-bridge loaded")
        except Exception as e:
            warn(f"Could not embed Java bridge: {e}")
        self.script = self.session.create_script(js)
        self.script.on("message", self._on_message)
        self.script.load()
        if not self.ready.wait(timeout=20):
            warn("BillingClient not ready within 20s, but order can still be dispatched.")
        else:
            ok("BillingClient ready")

    def _exports(self):
        sc = self.script
        if hasattr(sc, "exports_sync"):
            return sc.exports_sync
        return sc.exports

    def buy(self, plan_id, stack=False, addon=""):
        exp = self._exports()

        def rpc(names, arg=None, required=True):
            last = None
            for n in names:
                fn = getattr(exp, n, None)
                if not callable(fn):
                    continue
                try:
                    return fn() if arg is None else fn(arg)
                except Exception as e:
                    last = e
            if required:
                raise last or AttributeError(names[0])
            return None

        try:
            rpc(("set_addon", "setAddon"), addon or "", required=False)
            ret = rpc(("stack",) if stack else ("buy",), plan_id)
            info(ret)
        except Exception as e:
            warn(f"RPC call failed, using post message fallback: {e}")
            self.script.post({
                "type": "cfg",
                "payload": {"target": plan_id, "stack": stack, "addon": addon},
            })

    def close(self):
        try:
            if self.script:
                self.script.unload()
        except Exception:
            pass
        try:
            if self.session:
                self.session.detach()
        except Exception:
            pass
        self.script = None
        self.session = None


def pick_addon(plans):
    yt = [pid for pid in ("yt_1m", "yt_family", "yt_lite") if pid in plans]
    print("\nYouTube Add-on Options:")
    print("  0. None")
    for i, pid in enumerate(yt, 1):
        print(f"  {i}. {pid:<12} {plans[pid]['note']}")
    raw = input("Select add-on [0-3]: ").strip().lower() or "0"
    if raw in ("0", "n", "none", "", "no"):
        return ""
    if raw in plans:
        return raw
    try:
        return yt[int(raw) - 1]
    except Exception:
        return ""


def parse_args():
    p = argparse.ArgumentParser(description="Google One Subscription Injector")
    p.add_argument("-s", "--serial", default=os.environ.get("ANDROID_SERIAL") or "",
                   help="Device serial number")
    p.add_argument("--plan", default="",
                   help="Direct plan name or index number (skips interactive menu)")
    p.add_argument("--stack", "--renew", action="store_true",
                   help="Stack/renew mode: stack onto existing subscription (STACK=true)")
    p.add_argument("--addon", default="",
                   help="Add-on plan ID (e.g. yt_1m)")
    p.add_argument("--wait", type=float, default=8.0,
                   help="Seconds to wait after triggering checkout")
    return p.parse_args()


def resolve_plan(raw, plans, index=None):
    if not raw:
        return ""
    if raw in plans:
        return raw
    if index and raw in index:
        return index[raw]
    return ""


def main():
    _fix_stdio()
    args = parse_args()
    if args.serial:
        adb.serial = args.serial
        os.environ["ANDROID_SERIAL"] = args.serial

    if not JS_PATH.is_file():
        fail(f"Script file not found: {JS_PATH}")
        sys.exit(1)
    plans = parse_plans(JS_PATH.read_text(encoding="utf-8"))
    if not plans:
        fail("No PLANS found in frida.js")
        sys.exit(1)

    ensure_env()
    sess = Session()
    pid = start_google_one()
    sess.attach(pid)

    stack = bool(args.stack)
    addon = args.addon
    groups = grouped_plans(plans)
    index = {str(i): pid for i, (_t, pid, _s) in enumerate(flatten_menu(groups), 1)}
    index.update({pid: pid for pid in plans})

    if args.plan:
        plan_id = resolve_plan(args.plan, plans, index)
        if not plan_id:
            fail(f"Unknown plan: {args.plan!r}")
            sess.close()
            sys.exit(1)
        spec = plans[plan_id]
        info(f"{'STACK / RENEW' if stack else 'NEW PURCHASE'}: {plan_id} (sku={spec['sku']}, offer={spec['offer']})")
        info(spec["note"])
        sess.buy(plan_id, stack=stack, addon=addon)
        time.sleep(max(args.wait, 1.0))
        sess.close()
        return

    try:
        while True:
            index, _rows = print_menu(plans, stack, addon)
            try:
                raw = input("\nEnter choice > ").strip()
            except EOFError:
                break
            if not raw:
                continue
            low = raw.lower()
            if low in ("q", "quit", "exit"):
                break
            if low in ("l", "refresh"):
                continue
            if low in ("s", "stack", "renew"):
                stack = not stack
                ok(f"Stack Mode: {'ON (Stack onto existing subscription)' if stack else 'OFF (New purchase)'}")
                continue
            if low in ("a", "addon"):
                addon = pick_addon(plans)
                ok(f"Selected Add-on: {addon or 'None'}")
                continue
            if low in ("e", "env"):
                ensure_env()
                continue
            if low in ("r", "g", "restart"):
                sess.close()
                pid = start_google_one()
                sess.attach(pid)
                continue
            plan_id = index.get(raw) or index.get(low)
            if not plan_id:
                warn("Unrecognized input. Enter plan number [1-28], plan ID, or 'q' to quit.")
                continue
            spec = plans[plan_id]
            info(f"{'STACK / RENEW' if stack else 'NEW PURCHASE'}: {plan_id} (sku={spec['sku']}, offer={spec['offer']})")
            info(spec["note"])
            sess.buy(plan_id, stack=stack, addon=addon)
            time.sleep(1.2)
    except KeyboardInterrupt:
        print()
        warn("Interrupted by user.")
    finally:
        sess.close()
        info("Session terminated.")


if __name__ == "__main__":
    main()
