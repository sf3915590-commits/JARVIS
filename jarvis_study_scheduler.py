"""JARVIS Study Scheduler: persistent alarm + study-session launcher for Windows."""
from __future__ import annotations
import json, os, sys, time, subprocess, webbrowser
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / 'jarvis_study_config.json'
STATE = ROOT / 'jarvis_study_state.json'
LOG = ROOT / 'jarvis_study_scheduler.log'
DEFAULT = {
  'enabled': True, 'time': '09:00', 'days': [0,1,2,3,4,5,6],
  'label': 'Python study', 'course_url': 'https://www.youtube.com/results?search_query=Apna+College+Python+playlist',
  'auto_open_course': True, 'alarm_seconds': 90, 'snooze_minutes': 10
}

def log(msg):
    try:
        with LOG.open('a', encoding='utf-8') as f: f.write(f'[{datetime.now().isoformat(timespec="seconds")}] {msg}\n')
    except Exception: pass

def read_json(path, default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default.copy() if isinstance(default, dict) else default

def write_json(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)

def ensure_config():
    if not CONFIG.exists(): write_json(CONFIG, DEFAULT)

def launch_study():
    cfg = read_json(CONFIG, DEFAULT)
    state = read_json(STATE, {})
    state['last_started'] = datetime.now().isoformat(timespec='seconds')
    state['last_topic'] = cfg.get('label', 'Study')
    write_json(STATE, state)
    if cfg.get('auto_open_course', True):
        url = cfg.get('course_url') or DEFAULT['course_url']
        try: webbrowser.open(url, new=2)
        except Exception as e: log(f'open course failed: {e}')
    log('Study session launched')

def alarm():
    log('Alarm fired')
    try:
        import winsound
        end = time.monotonic() + max(15, int(read_json(CONFIG, DEFAULT).get('alarm_seconds', 90)))
        while time.monotonic() < end:
            winsound.Beep(1400, 650)
            winsound.Beep(950, 450)
            time.sleep(.15)
    except Exception as e:
        log(f'audio alarm error: {e}')
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, 'Good morning! Python study time. Click OK to continue.', 'JARVIS Study Alarm', 0x1000)
        except Exception: pass
    launch_study()

def scheduler_loop():
    ensure_config(); log('Scheduler online')
    while True:
        cfg = read_json(CONFIG, DEFAULT)
        now = datetime.now()
        if cfg.get('enabled', True) and now.strftime('%H:%M') == cfg.get('time', '09:00') and now.weekday() in cfg.get('days', list(range(7))):
            state = read_json(STATE, {})
            today = now.strftime('%Y-%m-%d')
            if state.get('last_alarm_date') != today:
                state['last_alarm_date'] = today; write_json(STATE, state)
                alarm()
        time.sleep(20)

def set_schedule(time_text=None, topic=None, url=None):
    ensure_config(); cfg = read_json(CONFIG, DEFAULT)
    if time_text:
        try: datetime.strptime(time_text, '%H:%M')
        except ValueError: return False, 'Time must be HH:MM, for example 09:00.'
        cfg['time'] = time_text
    if topic: cfg['label'] = topic.strip()[:120]
    if url: cfg['course_url'] = url.strip()
    cfg['enabled'] = True; write_json(CONFIG, cfg)
    log(f'Schedule updated: {cfg["time"]} / {cfg["label"]}')
    return True, f'Study alarm set for {cfg["time"]}; topic: {cfg["label"]}.'

def handle_command(command):
    """Return (handled, status, detail); called by Tahrun's command router."""
    c = str(command or '').strip(); low = c.lower()
    triggers = ('study schedule', 'study alarm', 'mujhe subah', 'python padhna', 'study time', 'schedule my study', 'jarvis study')
    if not any(x in low for x in triggers): return False, '', ''
    # Parse simple natural-language times, defaulting to 09:00 only when user asks for a study schedule.
    import re
    m = re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', low)
    time_text = None
    if m:
        h = int(m.group(1)); minute = int(m.group(2) or 0); mer = m.group(3)
        if minute < 60 and 0 <= h <= 23:
            if mer == 'pm' and h < 12: h += 12
            if mer == 'am' and h == 12: h = 0
            if mer and h > 12: h = -1
            if 0 <= h <= 23: time_text = f'{h:02d}:{minute:02d}'
    topic = 'Python study' if ('python' in low or 'padhna' in low) else None
    url = None
    um = re.search(r'https?://\S+', c)
    if um: url = um.group(0).rstrip('.,')
    ok, detail = set_schedule(time_text or '09:00', topic, url)
    return True, 'study_success' if ok else 'study_error', detail

if __name__ == '__main__':
    ensure_config()
    if '--once' in sys.argv:
        print(json.dumps(read_json(CONFIG, DEFAULT), indent=2)); raise SystemExit(0)
    scheduler_loop()
