import json
import os
import threading
from datetime import datetime

MEMORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "memory.json"
)

_memory_lock = threading.Lock()


def load_memory():
    with _memory_lock:
        try:
            if not os.path.exists(MEMORY_FILE):
                return {
                    "user": {},
                    "preferences": {},
                    "facts": [],
                    "conversations": []
                }

            with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                return json.load(file)

        except Exception:
            return {
                "user": {},
                "preferences": {},
                "facts": [],
                "conversations": []
            }


def save_memory(memory):
    with _memory_lock:
        temp_file = MEMORY_FILE + f".{os.getpid()}.tmp"

        for attempt in range(3):
            try:
                with open(
                    temp_file,
                    "w",
                    encoding="utf-8"
                ) as file:
                    json.dump(
                        memory,
                        file,
                        ensure_ascii=False,
                        indent=4
                    )

                os.replace(temp_file, MEMORY_FILE)
                break

            except PermissionError:
                time.sleep(0.1)

            except Exception as error:
                print(
                    f"Memory save error: {error}",
                    flush=True
                )
                break

            finally:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass

def add_fact(fact):
    memory = load_memory()

    if fact not in memory["facts"]:
        memory["facts"].append(fact)

    save_memory(memory)


def add_conversation(user_text, jarvis_text):
    memory = load_memory()

    memory["conversations"].append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "user": user_text,
        "jarvis": jarvis_text
    })

    # Keep the latest 100 conversations
    memory["conversations"] = memory["conversations"][-100:]

    save_memory(memory)


def get_facts():
    return load_memory().get("facts", [])


def get_recent_conversations(limit=10):
    conversations = load_memory().get("conversations", [])
    return conversations[-limit:]


def clear_memory():
    memory = {
        "user": {},
        "preferences": {},
        "facts": [],
        "conversations": []
    }

    save_memory(memory)