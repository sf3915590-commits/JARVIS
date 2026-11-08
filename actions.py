import os
import subprocess
import webbrowser
import ctypes
import time
from urllib.parse import quote

try:
    from mss import mss
except ImportError:
    mss = None



class JarvisActions:
    def _find_executable(self, candidates):
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def open_app(self, app):
        app = app.lower().strip()

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", "")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "")

        apps = {
            "chrome": [
                os.path.join(
                    local_app_data,
                    "Google", "Chrome", "Application", "chrome.exe"
                ),
                os.path.join(
                    program_files,
                    "Google", "Chrome", "Application", "chrome.exe"
                ),
                os.path.join(
                    program_files_x86,
                    "Google", "Chrome", "Application", "chrome.exe"
                ),
            ],
            "vscode": [
                os.path.join(
                    local_app_data,
                    "Programs", "Microsoft VS Code", "Code.exe"
                ),
                os.path.join(
                    program_files,
                    "Microsoft VS Code", "Code.exe"
                ),
                os.path.join(
                    program_files_x86,
                    "Microsoft VS Code", "Code.exe"
                ),
            ],
        }

        simple_commands = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "paint": ["mspaint.exe"],
        }

        if app in apps:
            executable = self._find_executable(apps[app])

            if executable:
                try:
                    subprocess.Popen([executable])
                    return True, f"{app} open kar diya."
                except Exception as error:
                    return False, f"{app} open nahi ho paaya: {error}"

            # Fallback to PATH if available.
            try:
                command = "chrome" if app == "chrome" else "code"
                subprocess.Popen([command])
                return True, f"{app} open kar diya."
            except Exception:
                return False, (
                    f"{app} computer par nahi mila. "
                    f"Please check karo ke {app} installed hai."
                )

        if app in simple_commands:
            try:
                subprocess.Popen(simple_commands[app])
                return True, f"{app} open kar diya."
            except Exception as error:
                return False, f"{app} open nahi ho paaya: {error}"

        return False, f"{app} abhi configured nahi hai."

    def open_website(self, site):
        sites = {
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "facebook": "https://www.facebook.com",
            "instagram": "https://www.instagram.com",
        }

        key = str(site or "").lower().strip()
        url = sites.get(key)

        if not url:
            return False, "Ye website configured nahi hai."

        try:
            chrome_paths = [
                os.path.join(
                    os.environ.get("PROGRAMFILES", ""),
                    "Google", "Chrome", "Application", "chrome.exe"
                ),
                os.path.join(
                    os.environ.get("LOCALAPPDATA", ""),
                    "Google", "Chrome", "Application", "chrome.exe"
                ),
                os.path.join(
                    os.environ.get("PROGRAMFILES(X86)", ""),
                    "Google", "Chrome", "Application", "chrome.exe"
                ),
            ]

            chrome = next(
                (path for path in chrome_paths if path and os.path.isfile(path)),
                None,
            )

            if chrome:
                subprocess.Popen(
                    [chrome, "--new-window", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            else:
                webbrowser.open(url, new=2, autoraise=True)

            return True, f"{site} open kar diya."
        except Exception as error:
            return False, f"Website open nahi ho paayi: {error}"

    def open_folder(self, folder):
        home = os.path.expanduser("~")

        folders = {
            "desktop": os.path.join(home, "Desktop"),
            "downloads": os.path.join(home, "Downloads"),
            "documents": os.path.join(home, "Documents"),
            "pictures": os.path.join(home, "Pictures"),
            "videos": os.path.join(home, "Videos"),
            "music": os.path.join(home, "Music"),
        }

        path = folders.get(folder.lower().strip())

        if not path:
            return False, "Ye folder configured nahi hai."

        if not os.path.exists(path):
            return False, "Folder computer par nahi mila."

        try:
            os.startfile(path)
            return True, f"{folder} folder open kar diya."
        except Exception as error:
            return False, f"Folder open nahi ho paaya: {error}"

    def search_web(self, query):
        if not query:
            return False, "Search query nahi mili."

        url = "https://www.google.com/search?q=" + query.replace(" ", "+")
        webbrowser.open(url)

        return True, f"Google par {query} search kar diya."


    def take_screenshot(self, path=None):
        """Take a real desktop screenshot without PyAutoGUI/PyScreeze."""
        try:
            if mss is None:
                return None

            if path is None:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                os.makedirs(desktop, exist_ok=True)
                stamp = time.strftime("%Y%m%d_%H%M%S")
                path = os.path.join(desktop, f"jarvis_screenshot_{stamp}.png")

            with mss() as screen:
                screen.shot(output=path)

            return path if os.path.exists(path) else None
        except Exception as error:
            print(f"❌ Screenshot error: {error}", flush=True)
            return None

    def get_screen_size(self):
        if mss is not None:
            with mss() as screen:
                monitor = screen.monitors[0]
                return monitor["width"], monitor["height"]
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    def click(self):
        import pyautogui
        pyautogui.click()

    def double_click(self):
        import pyautogui
        pyautogui.doubleClick()

    def right_click(self):
        import pyautogui
        pyautogui.rightClick()

    def type_text(self, text):
        import pyautogui
        pyautogui.write(text, interval=0.01)

    def press_key(self, key):
        import pyautogui
        pyautogui.press(key)

    def turn_off_screen(self):
        """Turn off only the monitor; Windows/Jarvis keeps running."""
        HWND_BROADCAST = 0xFFFF
        WM_SYSCOMMAND = 0x0112
        SC_MONITORPOWER = 0xF170
        MONITOR_OFF = 2
        ctypes.windll.user32.SendMessageW(
            HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_OFF
        )
        return True, "Screen off kar diya Boss. Jarvis background mein running hai."

    def turn_on_screen(self):
        HWND_BROADCAST = 0xFFFF
        WM_SYSCOMMAND = 0x0112
        SC_MONITORPOWER = 0xF170
        MONITOR_ON = -1
        ctypes.windll.user32.SendMessageW(
            HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, MONITOR_ON
        )
        return True, "Screen on kar diya Boss."

    def open_this_pc(self):
        try:
            subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            return True, "This PC open kar diya Boss."
        except Exception as error:
            return False, f"This PC open nahi ho paaya: {error}"

    def open_whatsapp(self):
        try:
            webbrowser.open("https://web.whatsapp.com")
            return True, "WhatsApp Web open kar diya Boss."
        except Exception as error:
            return False, f"WhatsApp open nahi ho paaya: {error}"

    def prepare_whatsapp_message(self, name, message):
        """Open WhatsApp Web and copy the message so it is ready to paste.
        Contact selection/sending remains user-confirmed because WhatsApp's UI and
        contact names are not reliably addressable by a public URL.
        """
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(message)
            root.update()
            root.destroy()
        except Exception:
            pass
        webbrowser.open("https://web.whatsapp.com")
        return True, f"WhatsApp open hai Boss. {name} ko message ready hai; contact select karke paste/send karo."

    def close_app(self, app):
        processes = {
            "chrome": "chrome.exe",
            "notepad": "notepad.exe",
        }

        process = processes.get(app.lower().strip())

        if not process:
            return False, "Is app ko close karna abhi configured nahi hai."

        try:
            result = subprocess.run(
                ["taskkill", "/IM", process, "/F"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return True, f"{app} band kar diya."

            return False, f"{app} abhi running nahi tha."

        except Exception as error:
            return False, f"{app} band nahi ho paaya: {error}"


actions = JarvisActions()
def take_screenshot():
    return JarvisActions().take_screenshot()