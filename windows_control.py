import os
import re
import subprocess
import webbrowser
from pathlib import Path


# ============================================================
# JARVIS WINDOWS VOLUME CONTROL
# ============================================================

def _send_volume_key(vk_code):
    """Send a Windows hardware-style media volume key."""
    import ctypes

    KEYEVENTF_KEYUP = 0x0002
    user32 = ctypes.windll.user32

    user32.keybd_event(vk_code, 0, 0, 0)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def volume_up():
    _send_volume_key(0xAF)  # VK_VOLUME_UP
    return True, "Volume badha diya."


def volume_down():
    _send_volume_key(0xAE)  # VK_VOLUME_DOWN
    return True, "Volume kam kar diya."


def volume_mute():
    _send_volume_key(0xAD)  # VK_VOLUME_MUTE
    return True, "Volume mute kar diya."


def volume_unmute():
    # Windows uses the same mute toggle key.
    _send_volume_key(0xAD)
    return True, "Volume unmute kar diya."

APP_ALIASES = {
    "chrome": "Google Chrome", "google chrome": "Google Chrome",
    "edge": "Microsoft Edge", "microsoft edge": "Microsoft Edge",
    "vscode": "Visual Studio Code", "vs code": "Visual Studio Code",
    "notepad": "Notepad", "calculator": "Calculator", "paint": "Paint",
    "whatsapp": "WhatsApp", "chatgpt": "ChatGPT Classic", "anthropic": "Claude",
    "claude": "Claude", "node": "Node.js", "nodejs": "Node.js",
    "instagram": "Instagram", "insta": "Instagram",
}

EXE_NAMES = {
    "chrome": ["chrome.exe"], "google chrome": ["chrome.exe"],
    "edge": ["msedge.exe"], "microsoft edge": ["msedge.exe"],
    "vscode": ["Code.exe"], "vs code": ["Code.exe"],
    "notepad": ["notepad.exe"], "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"], "node": ["node.exe"], "nodejs": ["node.exe"],
    "whatsapp": ["WhatsApp.exe", "WhatsApp.Root.exe"],
    "chatgpt": ["ChatGPT.exe"], "claude": ["Claude.exe"], "anthropic": ["Claude.exe"],
    "instagram": ["Instagram.exe"], "insta": ["Instagram.exe"],
}

# Common installed executable locations. We check these only when StartApps cannot launch it.
COMMON_DIRS = [
    os.environ.get("LOCALAPPDATA", ""),
    os.environ.get("PROGRAMFILES", ""),
    os.environ.get("PROGRAMFILES(X86)", ""),
]

def _clean(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())

def _powershell(script, timeout=6):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True, text=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )

def _start_app_id(display_name):
    # Return both Name and AppID so the matching is done by Windows itself.
    safe = str(display_name).replace("'", "''")
    script = f"Get-StartApps | Where-Object {{ $_.Name -like '*{safe}*' }} | Select-Object -First 1 -ExpandProperty AppID"
    try:
        out = _powershell(script).stdout.strip()
        return out.splitlines()[0].strip() if out else None
    except Exception:
        return None

def _launch_start_app(app_id):
    # explorer.exe is the most reliable shell entry point for Store/UWP apps.
    try:
        p = subprocess.Popen(
            ["explorer.exe", f"shell:AppsFolder\\{app_id}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return p.poll() is None or p.returncode is None
    except Exception:
        return False

def _find_exe(exe_names):
    # Always prefer the real installed Google Chrome over
    # Playwright's bundled Chromium.
    if "chrome.exe" in exe_names:
        real_chrome_paths = [
            os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for chrome_path in real_chrome_paths:
            if chrome_path and os.path.isfile(chrome_path):
                return chrome_path

    # First let Windows resolve commands on PATH.
    for exe in exe_names:
        try:
            result = subprocess.run(["where.exe", exe], capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.splitlines()[0].strip()
        except Exception:
            pass

    # Then search likely LocalAppData/Program Files locations (limited depth via PowerShell).
    names = ",".join("'" + x.replace("'", "''") + "'" for x in exe_names)
    roots = [p for p in COMMON_DIRS if p]
    for root in roots:
        safe = root.replace("'", "''")
        script = f"Get-ChildItem -Path '{safe}' -Filter '*.exe' -Recurse -ErrorAction SilentlyContinue | Where-Object {{ @({names}) -contains $_.Name }} | Select-Object -First 1 -ExpandProperty FullName"
        try:
            out = _powershell(script, timeout=10).stdout.strip()
            if out:
                return out.splitlines()[0].strip()
        except Exception:
            pass
    return None

# JARVIS ChatGPT Classic â€” exact installed Windows AppID
CHATGPT_CLASSIC_APP_ID = "OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0!ChatGPT"

def _get_window_aumid(hwnd):
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        k = ctypes.windll.kernel32
        a = ctypes.windll.advapi32
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        ph = k.OpenProcess(0x1000, False, pid.value)
        if not ph: return None
        token = wintypes.HANDLE()
        try:
            if not a.OpenProcessToken(ph, 0x0008, ctypes.byref(token)): return None
            try:
                n = wintypes.DWORD(0)
                k.GetApplicationUserModelId(token, ctypes.byref(n), None)
                if not n.value: return None
                buf = ctypes.create_unicode_buffer(n.value)
                rc = k.GetApplicationUserModelId(token, ctypes.byref(n), buf)
                return buf.value if rc == 0 else None
            finally:
                k.CloseHandle(token)
        finally:
            k.CloseHandle(ph)
    except Exception:
        return None

def _find_window_by_aumid(aumid):
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        found = []
        CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        @CB
        def cb(hwnd, _):
            if u.IsWindowVisible(hwnd) and _get_window_aumid(hwnd) == aumid:
                found.append(hwnd); return False
            return True
        u.EnumWindows(cb, 0)
        return found[0] if found else None
    except Exception:
        return None

def _focus_window(hwnd):
    try:
        import ctypes
        u = ctypes.windll.user32
        k = ctypes.windll.kernel32
        target = u.GetWindowThreadProcessId(hwnd, None)
        current = k.GetCurrentThreadId()
        fg = u.GetForegroundWindow()
        fg_thread = u.GetWindowThreadProcessId(fg, None) if fg else 0
        a = b = False
        if target and target != current:
            a = bool(u.AttachThreadInput(current, target, True))
        if fg_thread and target and fg_thread != target and fg_thread != current:
            b = bool(u.AttachThreadInput(fg_thread, target, True))
        u.ShowWindow(hwnd, 9)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        u.SetFocus(hwnd)
        if b: u.AttachThreadInput(fg_thread, target, False)
        if a: u.AttachThreadInput(current, target, False)
        return True
    except Exception:
        return False









def _send_ctrl_key(key):
    """Send Ctrl+key through the foreground window."""
    import ctypes
    import time
    user32 = ctypes.windll.user32
    VK_CONTROL = 0x11
    vk = ord(key.upper())
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.12)


def _send_enter():
    import ctypes
    import time
    user32 = ctypes.windll.user32
    VK_RETURN = 0x0D
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.15)


def _paste_chatgpt_text(text):
    if not text:
        return False

    try:
        import ctypes
        import time

        # Keep the clipboard path already used by JARVIS.
        _set_clipboard_text(text)
        time.sleep(0.15)

        # Click the lower-center area of the ChatGPT window so the composer
        # receives keyboard input, without hard-coding screen coordinates.
        user32 = ctypes.windll.user32
        hwnd = _find_chatgpt_classic_window()
        if hwnd and user32.GetForegroundWindow() != hwnd:
            _focus_chatgpt_classic(hwnd)
            time.sleep(0.25)

        if hwnd:
            rect = ctypes.wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            x = (rect.left + rect.right) // 2
            y = rect.bottom - max(90, min(140, (rect.bottom - rect.top) // 5))
            user32.SetCursorPos(x, y)
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.15)

        _send_ctrl_key("V")
        time.sleep(0.35)
        return True
    except Exception as e:
        print(f"âš ï¸ ChatGPT text paste failed: {e}", flush=True)
        return False









def _send_ctrl_key(key):
    """Send Ctrl+key through the foreground window."""
    import ctypes
    import time
    user32 = ctypes.windll.user32
    VK_CONTROL = 0x11
    vk = ord(key.upper())
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.12)


def _send_enter():
    import ctypes
    import time
    user32 = ctypes.windll.user32
    VK_RETURN = 0x0D
    KEYEVENTF_KEYUP = 0x0002
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.15)


def _paste_chatgpt_text(text):
    """Put text in clipboard and paste it into the focused ChatGPT composer."""
    if not text:
        return False
    try:
        _set_clipboard_text(text)
        _send_ctrl_key("V")
        return True
    except Exception as e:
        print(f"âš ï¸ ChatGPT text paste failed: {e}", flush=True)
        return False



# ===================== JARVIS CHATGPT CLASSIC V3 =====================
CHATGPT_CLASSIC_APP_ID = "OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0!ChatGPT"
CHATGPT_OPERATOR_TIMEOUT = 240


def _chatgpt_window_candidates():
    """Find visible top-level ChatGPT windows without relying on AUMID alone."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    enum_windows = user32.EnumWindows
    enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    get_len = user32.GetWindowTextLengthW
    get_text = user32.GetWindowTextW
    is_visible = user32.IsWindowVisible
    get_pid = user32.GetWindowThreadProcessId

    result = []

    def process_name(pid: int) -> str:
        try:
            h = kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
            if not h:
                return ""
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buf))
            # QueryFullProcessImageNameW(h, 0, buffer, size)
            ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
            kernel32.CloseHandle(h)
            if ok:
                return str(buf.value).rsplit("\\", 1)[-1].lower()
        except Exception:
            pass
        return ""

    def proc(hwnd, _):
        try:
            if not is_visible(hwnd):
                return True
            length = get_len(hwnd)
            buf = ctypes.create_unicode_buffer(max(1, length + 1))
            get_text(hwnd, buf, length + 1)
            title = str(buf.value or "").strip()
            pid = wintypes.DWORD()
            get_pid(hwnd, ctypes.byref(pid))
            pname = process_name(int(pid.value))
            haystack = f"{title} {pname}".lower()
            if "chatgpt" in haystack:
                result.append((int(hwnd), title, pname))
        except Exception:
            pass
        return True

    try:
        enum_windows(enum_proc_type(proc), 0)
    except Exception as exc:
        print(f"ChatGPT window scan warning: {exc}", flush=True)

    result.sort(key=lambda item: ("chatgpt" in item[1].lower(), item[1] != ""), reverse=True)
    return result


def _find_chatgpt_classic_window():
    """Return the best visible ChatGPT window HWND."""
    # Keep the existing AUMID helper as the first preference when present.
    try:
        finder = globals().get("_find_window_by_aumid")
        if finder:
            hwnd = finder(CHATGPT_CLASSIC_APP_ID)
            if hwnd:
                return hwnd
    except Exception:
        pass
    items = _chatgpt_window_candidates()
    return items[0][0] if items else None


def _focus_chatgpt_classic(hwnd):
    """Restore, focus, and verify a ChatGPT top-level window."""
    import ctypes
    import time

    user32 = ctypes.windll.user32
    if not hwnd or not user32.IsWindow(hwnd):
        return False

    try:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.BringWindowToTop(hwnd)
    except Exception:
        pass

    # Windows can restrict SetForegroundWindow; use thread-input attachment
    # and verify the real foreground window instead of trusting the call result.
    try:
        fg = user32.GetForegroundWindow()
        target_tid = user32.GetWindowThreadProcessId(hwnd, None)
        fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        if target_tid and fg_tid and target_tid != fg_tid:
            user32.AttachThreadInput(fg_tid, target_tid, True)
        try:
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
            user32.BringWindowToTop(hwnd)
        finally:
            if target_tid and fg_tid and target_tid != fg_tid:
                user32.AttachThreadInput(fg_tid, target_tid, False)
    except Exception:
        try:
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    deadline = time.time() + 2.5
    while time.time() < deadline:
        if user32.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.08)
    # A successful ShowWindow/BingToTop is still useful when Windows delays
    # foreground confirmation. Treat the visible ChatGPT HWND as focused enough
    # for the subsequent UI click, but do not invent success when no window exists.
    try:
        return bool(user32.IsWindow(hwnd))
    except Exception:
        return False


def launch_chatgpt_classic():
    """Launch/focus ChatGPT Classic and ALWAYS return (success, message)."""
    import subprocess
    import time

    before = {item[0] for item in _chatgpt_window_candidates()}
    try:
        hwnd = _find_chatgpt_classic_window()
        if hwnd and _focus_chatgpt_classic(hwnd):
            print("OK ChatGPT Classic focused.", flush=True)
            return True, "ChatGPT Classic focused."
    except Exception as exc:
        print(f"ChatGPT existing-window focus warning: {exc}", flush=True)

    try:
        subprocess.Popen(
            ["explorer.exe", f"shell:AppsFolder\\{CHATGPT_CLASSIC_APP_ID}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return False, f"ChatGPT Classic launch failed: {exc}"

    deadline = time.time() + 12.0
    while time.time() < deadline:
        try:
            items = _chatgpt_window_candidates()
            fresh = [item for item in items if item[0] not in before]
            pool = fresh or items
            if pool:
                hwnd = pool[0][0]
                if _focus_chatgpt_classic(hwnd):
                    print("OK ChatGPT Classic launched + focused.", flush=True)
                    return True, "ChatGPT Classic launched and focused."
        except Exception:
            pass
        time.sleep(0.25)

    # FALLBACK (added by apply_chatgpt_open_fix.py):
    # The hardcoded package AppID can go stale after a reinstall/update.
    # Resolve the current AppID dynamically (same helper used elsewhere
    # in this file for other apps) and try once more before giving up.
    try:
        dynamic_id = _start_app_id("ChatGPT")
        if dynamic_id and dynamic_id != CHATGPT_CLASSIC_APP_ID:
            print(f"ChatGPT Classic: hardcoded AppID failed, trying resolved AppID: {dynamic_id}", flush=True)
            subprocess.Popen(
                ["explorer.exe", f"shell:AppsFolder\\{dynamic_id}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline2 = time.time() + 8.0
            while time.time() < deadline2:
                try:
                    items = _chatgpt_window_candidates()
                    fresh = [item for item in items if item[0] not in before]
                    pool = fresh or items
                    if pool:
                        hwnd = pool[0][0]
                        if _focus_chatgpt_classic(hwnd):
                            print("OK ChatGPT Classic launched + focused (dynamic AppID).", flush=True)
                            return True, "ChatGPT Classic launched and focused."
                except Exception:
                    pass
                time.sleep(0.25)
    except Exception as exc:
        print(f"ChatGPT Classic dynamic AppID fallback warning: {exc}", flush=True)

    try:
        hwnd = _find_chatgpt_classic_window()
        if hwnd:
            return True, "ChatGPT Classic window found."
    except Exception:
        pass
    return False, "ChatGPT Classic window not found."


def run_chatgpt_operator(*args, **kwargs):
    """Compatibility wrapper used by existing Tahrun routing."""
    try:
        from jarvis_chatgpt_operator import execute
        prompt = kwargs.get("prompt") or kwargs.get("text") or kwargs.get("command")
        if not prompt:
            for value in args:
                if isinstance(value, str) and value.strip():
                    prompt = value
                    break
        prompt = str(prompt or "").strip()
        selected = kwargs.get("selected_image")
        if selected is None:
            selected = kwargs.get("has_image")
        if selected is None:
            selected = kwargs.get("image") is not None or kwargs.get("image_path") is not None
        return execute(prompt, use_selected_image=bool(selected))
    except Exception as exc:
        print(f"ChatGPT operator error: {exc}", flush=True)
        return False, f"ChatGPT operator error: {exc}"

# =================== END JARVIS CHATGPT CLASSIC V3 ==================


def launch_installed_app(name):
    if str(name).strip().lower() in {"chatgpt", "chat gpt", "chatgpt classic"}:
        return launch_chatgpt_classic()

    key = _clean(name)
    display = APP_ALIASES.get(key, str(name).strip() or key)
    exe = _find_exe(EXE_NAMES.get(key, []))
    if exe:
        try:
            subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            return True, f'{display} open kar diya Boss.'
        except Exception:
            pass
    app_id = _start_app_id(display)
    if app_id and _launch_start_app(app_id):
        return True, f'{display} open kar diya Boss.'
    try:
        subprocess.Popen(['explorer.exe', f'shell:AppsFolder\\{display}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f'{display} open kar diya Boss.'
    except Exception:
        return False, f'{display} installed app nahi mila.'
def open_explorer(path=None):
    target = os.path.expandvars(path) if path else str(Path.home())
    try:
        subprocess.Popen(["explorer.exe", target])
        return True, "File Explorer open kar diya Boss."
    except Exception as e:
        return False, str(e)

def open_folder(name):
    folders = {"desktop": Path.home()/"Desktop", "downloads": Path.home()/"Downloads",
               "documents": Path.home()/"Documents", "pictures": Path.home()/"Pictures",
               "videos": Path.home()/"Videos", "music": Path.home()/"Music"}
    p = folders.get(_clean(name))
    return open_explorer(str(p)) if p else (False, "Folder nahi mila.")

def open_url(url):
    try:
        webbrowser.open(url, new=2)
        return True, "Open kar diya Boss."
    except Exception as e:
        return False, str(e)

def close_app(name):
    proc = {"chrome":"chrome.exe", "google chrome":"chrome.exe", "edge":"msedge.exe",
            "microsoft edge":"msedge.exe", "vscode":"Code.exe", "vs code":"Code.exe",
            "notepad":"notepad.exe", "whatsapp":"WhatsApp.exe", "chatgpt":"ChatGPT.exe",
            "claude":"Claude.exe", "anthropic":"Claude.exe"}.get(_clean(name))
    if not proc:
        return False, "Is app ke liye close mapping nahi hai."
    try:
        r = subprocess.run(["taskkill", "/IM", proc, "/T"], capture_output=True, text=True, timeout=5)
        return True, f"{name} close kar diya Boss."
    except Exception as e:
        return False, str(e)


 

