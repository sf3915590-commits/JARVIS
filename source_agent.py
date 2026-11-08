import re
import shutil
from datetime import datetime
from pathlib import Path

import ollama


PROJECT_ROOT = Path(
    r"C:\Users\MD Farhan\OneDrive\Desktop\Tahrun"
)

ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".css",
    ".html",
    ".json",
}

MAX_FILE_SIZE = 120_000

# ---------------------------------------------------------
# OLLAMA SETTINGS
# ---------------------------------------------------------

OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3:4b-instruct"
OLLAMA_TIMEOUT = 60.0

# Client-level timeout prevents source editing from waiting
# forever if Ollama becomes stuck.
ollama_client = ollama.Client(
    host=OLLAMA_HOST,
    timeout=OLLAMA_TIMEOUT,
)


# ---------------------------------------------------------
# SAFE PATH
# ---------------------------------------------------------

def _safe_path(path):
    path = path.resolve()

    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return None

    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None

    if path.name.startswith(".env"):
        return None

    return path


# ---------------------------------------------------------
# FIND TARGET SOURCE FILE
# ---------------------------------------------------------

def _extract_target(request):
    matches = re.findall(
        r"(?i)([\w.-]+\.(?:py|js|jsx|css|html|json))",
        request,
    )

    for name in matches:
        candidate = _safe_path(
            PROJECT_ROOT / name
        )

        if candidate and candidate.exists():
            return candidate

    # Default source file
    return _safe_path(
        PROJECT_ROOT / "tahrun.py"
    )


# ---------------------------------------------------------
# BACKUP
# ---------------------------------------------------------

def _backup(path):
    backup_root = PROJECT_ROOT / ".jarvis_backups"

    backup_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    destination = (
        backup_root
        / f"{path.name}.{stamp}.bak"
    )

    shutil.copy2(
        path,
        destination,
    )

    return destination


# ---------------------------------------------------------
# EXTRACT GENERATED CODE
# ---------------------------------------------------------

def _extract_code(response):
    if not response:
        return None

    match = re.search(
        r"<FILE>\s*(.*?)\s*</FILE>",
        response,
        re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    if "```" in response:
        parts = response.split("```")

        if len(parts) >= 3:
            body = parts[1]

            body = re.sub(
                r"^\s*(python|javascript|jsx|css|html|json)\s*\n",
                "",
                body,
                flags=re.IGNORECASE,
            )

            return body.strip()

    return None


# ---------------------------------------------------------
# SOURCE EDITOR
# ---------------------------------------------------------

def edit_source(request):

    # -----------------------------------------------------
    # FIND TARGET
    # -----------------------------------------------------

    target = _extract_target(request)

    if target is None or not target.exists():
        return (
            False,
            "Boss, requested source file nahi mili.",
        )

    # -----------------------------------------------------
    # SIZE PROTECTION
    # -----------------------------------------------------

    if target.stat().st_size > MAX_FILE_SIZE:
        return (
            False,
            "Boss, source file bahut badi hai; "
            "pehle specific file ya section batao.",
        )

    # -----------------------------------------------------
    # READ CURRENT SOURCE
    # -----------------------------------------------------

    try:
        current = target.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as error:
        return (
            False,
            f"Boss, source file read nahi ho paayi: {error}",
        )

    # -----------------------------------------------------
    # AI INSTRUCTIONS
    # -----------------------------------------------------

    system = """You are Jarvis's local source-code editor.

Modify ONLY the requested source file.

Preserve all existing functionality unless the user
explicitly asks for a change.

Do not remove unrelated features.

Return the COMPLETE resulting file, not a patch.

Output ONLY:

<FILE>
complete file contents
</FILE>

Do not add explanations outside the FILE tags.
"""

    prompt = f"""User request:
{request}

Target file:
{target.name}

Current source:
{current}
"""

    # -----------------------------------------------------
    # OLLAMA CALL
    # -----------------------------------------------------

    try:

        print(
            f"🛠️ Source editor: working on {target.name}...",
            flush=True,
        )

        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={
                "temperature": 0.1,
                "num_predict": 1200,
                "num_ctx": 8192,
            },
            keep_alive=-1,
        )

    except Exception as error:

        error_text = str(error).lower()

        if (
            "timeout" in error_text
            or "timed out" in error_text
        ):
            return (
                False,
                "Boss, source editor timeout ho gaya. "
                "Jarvis ko maine safely release kar diya.",
            )

        if (
            "connection" in error_text
            or "refused" in error_text
            or "connect" in error_text
        ):
            return (
                False,
                "Boss, Ollama connection available nahi hai. "
                "Source file safe hai; koi change nahi hua.",
            )

        return (
            False,
            f"Boss, source editor mein problem aa gayi: {error}",
        )

    # -----------------------------------------------------
    # READ AI RESPONSE
    # -----------------------------------------------------

    try:
        content = response["message"]["content"]
    except Exception:
        return (
            False,
            "Boss, AI response readable nahi tha. "
            "Source file change nahi hui.",
        )

    # -----------------------------------------------------
    # EXTRACT FILE
    # -----------------------------------------------------

    generated = _extract_code(content)

    if not generated:
        return (
            False,
            "Boss, AI ne valid source output nahi diya. "
            "Source file change nahi hui.",
        )

    # -----------------------------------------------------
    # BASIC SAFETY
    # -----------------------------------------------------

    if len(generated.strip()) < 20:
        return (
            False,
            "Boss, generated source suspiciously chhota tha. "
            "Original file safe rakhi hai.",
        )

    # -----------------------------------------------------
    # BACKUP FIRST
    # -----------------------------------------------------

    try:
        backup = _backup(target)
    except Exception as error:
        return (
            False,
            f"Boss, backup create nahi ho paaya: {error}",
        )

    # -----------------------------------------------------
    # WRITE NEW SOURCE
    # -----------------------------------------------------

    try:
        target.write_text(
            generated,
            encoding="utf-8",
        )
    except Exception as error:
        return (
            False,
            f"Boss, source file write nahi ho paayi: {error}",
        )

    # -----------------------------------------------------
    # PYTHON SYNTAX CHECK
    # -----------------------------------------------------

    if target.suffix.lower() == ".py":

        try:
            compile(
                generated,
                str(target),
                "exec",
            )

        except SyntaxError as error:

            try:
                shutil.copy2(
                    backup,
                    target,
                )
            except Exception:
                pass

            return (
                False,
                "Boss, generated Python code invalid tha. "
                "Maine automatically original backup restore kar diya.",
            )

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    return (
        True,
        f"{target.name} update kar diya. "
        "Purana version backup mein safe hai.",
    )