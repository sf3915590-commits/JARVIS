import ctypes
import math
import random
import threading
import time
import tkinter as tk
import winsound


# ============================================================
# JARVIS HUD v2
# Clean holographic "core + energy wave" style.
#
# BIG mode  : desktop / nothing active
# SMALL mode: Chrome, VS Code, etc.
#
# States:
#   idle
#   listening
#   thinking
#   speaking
#
# Wake:
#   hud.wake()
#   -> visual flash + original sci-fi audio cue
# ============================================================


class JarvisHUD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Jarvis HUD")

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", False)

        self.transparent = "#010101"
        self.root.configure(bg=self.transparent)

        try:
            self.root.wm_attributes(
                "-transparentcolor",
                self.transparent,
            )
        except tk.TclError:
            pass

        # Bigger desktop presentation.
        self.big_size = 340
        self.small_size = 145

        self.current_size = self.big_size
        self.target_size = self.big_size

        # Slightly lower than the webcam area.
        self.big_y = 58
        self.small_y = 52

        self.state = "idle"

        self.phase = 0.0
        self.wave_phase = 0.0

        self.flash = 0.0
        self.wake_wave = 0.0

        self.running = True

        self.canvas = tk.Canvas(
            self.root,
            width=self.big_size,
            height=self.big_size,
            bg=self.transparent,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.root.bind("<KeyPress>", self.demo_key)
        self.root.focus_force()

        self.last_foreground_check = 0.0

        self.center_window()

        self.animate()

    # ========================================================
    # Position / size
    # ========================================================

    def center_window(self):
        screen_w = self.root.winfo_screenwidth()

        x = int((screen_w - self.current_size) / 2)

        if self.current_size >= 250:
            y = self.big_y
        else:
            y = self.small_y

        self.root.geometry(
            f"{int(self.current_size)}x{int(self.current_size)}+{x}+{y}"
        )

    def set_window_size(self, size):
        size = int(size)

        screen_w = self.root.winfo_screenwidth()
        x = int((screen_w - size) / 2)

        y = self.big_y if size >= 250 else self.small_y

        self.root.geometry(
            f"{size}x{size}+{x}+{y}"
        )

    # ========================================================
    # Public API
    # ========================================================

    def set_state(self, state):
        state = str(state).lower().strip()

        if state not in {
            "idle",
            "listening",
            "thinking",
            "speaking",
        }:
            state = "idle"

        self.state = state

        self.root.attributes("-topmost", state != "idle")
        if state == "idle":
            self.target_size = self.big_size

        else:
            # During active voice interaction keep the HUD
            # clearly visible instead of letting it disappear.
            self.target_size = self.big_size

    def wake(self):
        self.flash = 1.0
        self.wake_wave = 1.0
        self.state = "listening"
        self.target_size = self.big_size

        # Original short sci-fi electronic cue.
        play_wake_sound()

    def set_big(self):
        self.target_size = self.big_size

    def set_small(self):
        self.target_size = self.small_size

    def stop(self):
        self.running = False

        try:
            self.root.after(
                0,
                self.root.destroy,
            )
        except Exception:
            pass

    # ========================================================
    # Windows foreground app detection
    # ========================================================

    def get_foreground_title(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()

            if not hwnd:
                return ""

            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)

            if length <= 0:
                return ""

            buffer = ctypes.create_unicode_buffer(
                length + 1
            )

            ctypes.windll.user32.GetWindowTextW(
                hwnd,
                buffer,
                length + 1,
            )

            return buffer.value or ""

        except Exception:
            return ""

    def is_desktop(self, title):
        title = title.lower().strip()

        if not title:
            return True

        return title in {
            "program manager",
            "desktop",
        }

    def update_mode(self):
        # While Jarvis is actively interacting, keep the
        # cinematic BIG presentation.
        if self.state != "idle":
            return

        now = time.time()

        if now - self.last_foreground_check < 0.4:
            return

        self.last_foreground_check = now

        title = self.get_foreground_title()

        if self.is_desktop(title):
            self.target_size = self.big_size
        else:
            self.target_size = self.small_size

    # ========================================================
    # Smooth transition
    # ========================================================

    def smooth_resize(self):
        difference = self.target_size - self.current_size

        if abs(difference) < 1:
            self.current_size = self.target_size
            return

        self.current_size += difference * 0.13

        if abs(
            self.current_size - self.target_size
        ) < 0.7:
            self.current_size = self.target_size

        self.set_window_size(
            self.current_size
        )

    # ========================================================
    # Drawing
    # ========================================================

    def draw(self):
        self.canvas.delete("all")

        size = max(
            40,
            int(self.current_size),
        )

        self.canvas.config(
            width=size,
            height=size,
        )

        cx = size / 2
        cy = size / 2

        scale = size / 340.0

        speed = {
            "idle": 0.018,
            "listening": 0.060,
            "thinking": 0.100,
            "speaking": 0.070,
        }.get(self.state, 0.02)

        self.phase += speed
        self.wave_phase += speed * 1.8

        # Amber/gold holographic palette.
        deep = "#351700"
        dark = "#693000"
        amber = "#b85b00"
        orange = "#e67b00"
        gold = "#ffae24"
        hot = "#ffd36a"
        white_gold = "#fff1bd"

        # ----------------------------------------------------
        # Very subtle HUD frame fragments
        # ----------------------------------------------------

        if size >= 180:
            margin = 20 * scale
            line = max(
                1,
                int(1.2 * scale),
            )

            # Top-left fragment
            self.canvas.create_line(
                margin,
                margin + 18 * scale,
                margin + 65 * scale,
                margin + 18 * scale,
                fill=dark,
                width=line,
            )

            self.canvas.create_line(
                margin,
                margin + 18 * scale,
                margin,
                margin + 55 * scale,
                fill=dark,
                width=line,
            )

            # Top-right fragment
            self.canvas.create_line(
                size - margin - 65 * scale,
                margin + 18 * scale,
                size - margin,
                margin + 18 * scale,
                fill=dark,
                width=line,
            )

            self.canvas.create_line(
                size - margin,
                margin + 18 * scale,
                size - margin,
                margin + 55 * scale,
                fill=dark,
                width=line,
            )

        # ----------------------------------------------------
        # Energy sphere / chip
        # ----------------------------------------------------

        base_r = 73 * scale

        # Outer ghost sphere: fragmented, NOT a solid ring.
        fragment_count = 38

        for i in range(fragment_count):
            angle = (
                i * (360 / fragment_count)
                + math.degrees(self.phase * 0.45)
            )

            # Irregular holographic edge.
            noise = math.sin(
                self.phase * 4.0
                + i * 2.7
            )

            radius = (
                base_r
                + noise * 10 * scale
                + random.Random(i).uniform(
                    -5,
                    5,
                ) * scale
            )

            arc_len = (
                5
                + 8 * (
                    0.5
                    + 0.5 * math.sin(
                        i * 1.7
                        + self.phase * 5
                    )
                )
            )

            # Only some fragments are visible.
            if (
                i % 3 == 0
                or self.state in {
                    "listening",
                    "thinking",
                }
            ):
                self.canvas.create_arc(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    start=angle,
                    extent=arc_len,
                    style=tk.ARC,
                    outline=(
                        orange
                        if i % 4
                        else gold
                    ),
                    width=max(
                        1,
                        int(
                            1.4 * scale
                        ),
                    ),
                )

        # ----------------------------------------------------
        # Particle field
        # ----------------------------------------------------

        particle_count = (
            120 if size >= 220
            else 50
        )

        for i in range(particle_count):
            a = (
                i * 2.399
                + self.phase * (
                    0.8
                    + (i % 5) * 0.07
                )
            )

            radius = (
                35
                + (
                    i % 31
                ) * 1.9
                + math.sin(
                    self.phase * 3
                    + i
                ) * 5
            ) * scale

            px = (
                cx
                + math.cos(a)
                * radius
            )

            py = (
                cy
                + math.sin(a)
                * radius
            )

            particle_size = (
                0.5
                + (
                    i % 4
                ) * 0.35
            ) * scale

            self.canvas.create_oval(
                px - particle_size,
                py - particle_size,
                px + particle_size,
                py + particle_size,
                fill=(
                    hot
                    if i % 7 == 0
                    else amber
                ),
                outline="",
            )

        # ----------------------------------------------------
        # Central CHIP / CORE
        # ----------------------------------------------------

        core_r = 35 * scale

        # Broken outer core fragments.
        for i in range(12):
            angle = (
                self.phase * 80
                + i * 30
            )

            radius = (
                core_r * 1.25
            )

            self.canvas.create_arc(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                start=angle,
                extent=10,
                style=tk.ARC,
                outline=gold,
                width=max(
                    1,
                    int(
                        1.5 * scale
                    ),
                ),
            )

        # Core glow layers.
        for multiplier, outline, width in [
            (1.20, dark, 2),
            (1.00, orange, 2),
            (0.78, gold, 2),
        ]:
            radius = (
                core_r
                * multiplier
            )

            self.canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=outline,
                width=max(
                    1,
                    int(
                        width * scale
                    ),
                ),
            )

        # ----------------------------------------------------
        # THE ORANGE ENERGY WAVE
        # ----------------------------------------------------

        wave_points = []

        wave_width = 46 * scale
        wave_height = 12 * scale

        for i in range(34):
            x = (
                cx
                - wave_width
                + (
                    2
                    * wave_width
                    * i
                    / 33
                )
            )

            y = (
                cy
                + math.sin(
                    self.wave_phase * 6
                    + i * 0.72
                )
                * wave_height
            )

            # Thinking makes the wave more energetic.
            if self.state == "thinking":
                y += (
                    math.sin(
                        self.wave_phase * 12
                        + i
                    )
                    * 4
                    * scale
                )

            wave_points.extend(
                [x, y]
            )

        if len(wave_points) >= 4:
            self.canvas.create_line(
                *wave_points,
                fill=hot,
                width=max(
                    1,
                    int(
                        2.4 * scale
                    ),
                ),
                smooth=True,
            )

        # Second thinner wave.
        wave2 = []

        for i in range(28):
            x = (
                cx
                - wave_width * 0.8
                + (
                    1.6
                    * wave_width
                    * i
                    / 27
                )
            )

            y = (
                cy
                + math.sin(
                    self.wave_phase * 5
                    + i * 0.9
                    + 1.4
                )
                * wave_height
                * 0.45
            )

            wave2.extend(
                [x, y]
            )

        self.canvas.create_line(
            *wave2,
            fill=orange,
            width=max(
                1,
                int(
                    1.1 * scale
                ),
            ),
            smooth=True,
        )

        # ----------------------------------------------------
        # Listening / thinking energy
        # ----------------------------------------------------

        if self.state in {
            "listening",
            "thinking",
        }:
            spokes = (
                28
                if self.state == "thinking"
                else 18
            )

            for i in range(spokes):
                angle = (
                    i * (
                        360 / spokes
                    )
                    + self.phase * 100
                )

                inner_r = (
                    39 * scale
                )

                outer_r = (
                    48
                    + 8 * math.sin(
                        self.phase * 7
                        + i
                    )
                ) * scale

                x1 = (
                    cx
                    + math.cos(
                        math.radians(
                            angle
                        )
                    )
                    * inner_r
                )

                y1 = (
                    cy
                    + math.sin(
                        math.radians(
                            angle
                        )
                    )
                    * inner_r
                )

                x2 = (
                    cx
                    + math.cos(
                        math.radians(
                            angle
                        )
                    )
                    * outer_r
                )

                y2 = (
                    cy
                    + math.sin(
                        math.radians(
                            angle
                        )
                    )
                    * outer_r
                )

                self.canvas.create_line(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=orange,
                    width=max(
                        1,
                        int(
                            1.2 * scale
                        ),
                    ),
                )

        # ----------------------------------------------------
        # Speaking pulse
        # ----------------------------------------------------

        if self.state == "speaking":
            pulse = (
                1
                + 0.18 * math.sin(
                    self.phase * 18
                )
            )

            radius = (
                54
                * scale
                * pulse
            )

            self.canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=orange,
                width=max(
                    1,
                    int(
                        1.4 * scale
                    ),
                ),
            )

        # ----------------------------------------------------
        # Wake flash
        # ----------------------------------------------------

        if self.flash > 0:
            radius = (
                45
                + 115 * self.flash
            ) * scale

            self.canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=hot,
                width=max(
                    1,
                    int(
                        3 * self.flash
                        * scale
                    ),
                ),
            )

            self.flash *= 0.84

            if self.flash < 0.015:
                self.flash = 0

        # Wake wave sweep.
        if self.wake_wave > 0:
            sweep = (
                75
                * (1 - self.wake_wave)
            )

            self.canvas.create_arc(
                cx - sweep * scale,
                cy - sweep * scale,
                cx + sweep * scale,
                cy + sweep * scale,
                start=(
                    -90
                    + self.phase * 120
                ),
                extent=95,
                style=tk.ARC,
                outline=hot,
                width=max(
                    1,
                    int(
                        2 * scale
                    ),
                ),
            )

            self.wake_wave *= 0.90

            if self.wake_wave < 0.015:
                self.wake_wave = 0

    # ========================================================
    # Demo controls
    # ========================================================

    def demo_key(self, event):
        key = event.keysym.lower()

        if key == "escape":
            self.stop()

        elif key == "1":
            self.set_state("idle")

        elif key == "2":
            self.set_state("listening")

        elif key == "3":
            self.set_state("thinking")

        elif key == "4":
            self.set_state("speaking")

        elif key == "w":
            self.wake()

        elif key == "s":
            self.set_small()

        elif key == "b":
            self.set_big()

    # ========================================================
    # Loop
    # ========================================================

    def animate(self):
        if not self.running:
            return

        self.update_mode()
        self.smooth_resize()
        self.draw()

        self.root.after(
            30,
            self.animate,
        )

    def run(self):
        self.root.mainloop()


# ============================================================
# Original sci-fi wake sound
# ============================================================

def play_wake_sound():
    def sound():
        try:
            # Short ascending electronic cue.
            winsound.Beep(440, 45)
            winsound.Beep(587, 45)
            winsound.Beep(784, 65)
            winsound.Beep(988, 85)
        except Exception:
            pass

    threading.Thread(
        target=sound,
        daemon=True,
    ).start()


# ============================================================
# Future integration API
# ============================================================

_hud_instance = None
_hud_thread = None


def start_hud():
    global _hud_instance
    global _hud_thread

    if _hud_instance is not None:
        return _hud_instance

    ready = threading.Event()

    def runner():
        global _hud_instance

        _hud_instance = JarvisHUD()
        ready.set()
        _hud_instance.run()

    _hud_thread = threading.Thread(
        target=runner,
        daemon=True,
    )

    _hud_thread.start()

    ready.wait(timeout=5)

    return _hud_instance


def set_state(state):
    hud = start_hud()

    try:
        hud.root.after(
            0,
            hud.set_state,
            state,
        )
    except Exception:
        pass


def wake():
    hud = start_hud()

    try:
        hud.root.after(
            0,
            hud.wake,
        )
    except Exception:
        pass


def stop():
    global _hud_instance

    if _hud_instance is not None:
        try:
            _hud_instance.root.after(
                0,
                _hud_instance.stop,
            )
        except Exception:
            pass


if __name__ == "__main__":
    print("JARVIS HUD v2")
    print("")
    print("1 = Idle")
    print("2 = Listening")
    print("3 = Thinking")
    print("4 = Speaking")
    print("W = Wake + sound")
    print("S = Small")
    print("B = Big")
    print("ESC = Exit")
    print("")

    JarvisHUD().run()

# JARVIS_LEGACY_HUD_DISABLED_BY_LIVE_FIX
# React dashboard is the only production HUD.
def start_hud(): return None
def set_state(state): return None
def wake(): return None
def stop(): return None



