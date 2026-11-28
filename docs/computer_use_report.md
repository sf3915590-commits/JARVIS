# Computer-use upgrade: implementation and validation

## Scope and baseline
Implemented on GitHub main commit `4e0497f7a10c176476e69c44b7e85aa867dd1f91` in an isolated checkout. No live Windows filesystem/controller is exposed in this session. Android source is absent. This is a reviewable incremental upgrade, not an installed Windows/Android release or production certification.

## Discovered capabilities
- `Tahrun.py`: voice, action execution, HUD, study and screen fastpaths.
- `brain.py`: Ollama/cloud brain and intent routing; preserved.
- `coding_agent.py`: website generation, project backups, VS Code, npm runtimes and Playwright smoke tests; preserved.
- `windows_control.py`, `actions.py`: app launch, mouse, keyboard, volume and folders; preserved.
- `file_manager.py`: legacy folder/search/open/PDF helpers; preserved.
- `screen_agent.py`: PyAutoGUI screenshot/input, UI Automation text matching.
- `screen_vision.py`: MSS/Pillow capture, local Ollama VLM description and click grounding; preserved.
- Existing browser, WhatsApp, voice and provider implementations were not replaced.

## New implementation
- `file_manager.py`: scoped FileSystemAgent; exact/partial/extension/fuzzy/recursive/latest search, full paths, duplicate names, explicit incomplete-search reporting; read/write/mkdir/move/reveal operations.
- `computer_tasks.py`: deterministic command route, 60-second result selection, stale selection invalidation, project scaffold, bounded sequential API (up to 20 steps), stop on failure/ambiguity; rotating metadata audit log under user `.jarvis/logs`.
- `orchestrator.py`, `Tahrun.py`: integrate into existing voice/text execution; overwrite uses existing local confirmation callback, not an LLM-supplied approval flag.
- `screen_agent.py`: local OCR reusing existing MSS capture and Pillow, temporary image cleanup, unique-title window switch and dependency-aware capability reporting.
- `requirements-computer-use.txt`: optional `pytesseract>=0.3.13,<0.4`; no packages or vision models automatically installed.
- `tests/test_computer_use.py`, `docs/computer_use_plan.md`, this report.

## Commands
- `find Tahrun.py`
- `find Tahrun.py and open it in File Explorer` then `choose 2` if ambiguous.
- `find my Python coding files`, `search for my HTML files`, `find the latest project file`.
- `create a Python project inside my Desktop folder with main.py, brain.py and requirements.txt` creates a new `PythonProject` containing empty starter files; existing target is rejected.
- `open folder C:\Users\...`, `open in explorer C:\Users\...`.
- `read file <absolute path>`.
- `write file <absolute path> with content <text>` (existing-file overwrite asks through local voice confirmation).
- `create folder <absolute path>`.
- `move file <absolute source> to <absolute destination>`; rename uses same operation.
- `switch to window <unique title>`.
- `read screen text`.

## Security and recovery
Default permitted root is home. Owner may set `JARVIS_FILE_ROOTS` to additional permitted directories using the OS path separator (`;` on Windows). Protected repository directory cannot be changed through new file APIs. Secret/configuration locations, symbolic links, junctions and reparse points are rejected. No delete operation or generated-shell/code execution was introduced. Existing edits need confirmation, retain an exclusive backup, and use a temporary file plus atomic replace. Changed-during-approval files are rejected. Move never overwrites an existing destination; cross-volume hard-link failures leave source intact. Search does not silently open a partial or ambiguous result. Partial scaffolds report files actually created rather than deleting user work. Audit stores operation/path, never file content.

The scope checks are not an OS security sandbox: a hostile local process could race filesystem checks. Legacy file/GUI/coding APIs remain outside this new policy. Whole-system security and approval enforcement are not established by this patch.

## Tests actually run
`python -m unittest discover -s tests -v`: **22 passed** on Linux/Python. Actual temporary-file tests cover exact/partial/fuzzy/extension/latest search, duplicates, bounded scans, permissions, symlinks, protection, overwrite denial/approval, backup, concurrent-edit detection, move collision, project creation/preflight, selection expiry, failure stop. Mock tests cover Explorer argv, GUI dispatch/failure, OCR extraction/cleanup/missing dependency, screenshot failure, window ambiguity and brain fallback. AST test verifies Tahrun integration without starting microphone/providers.

`python -m compileall -q .`: passed. `git diff --check`: passed.
No pre-existing automated regression suite was present in this checkout. Voice, OpenAI/Groq/Ollama calls, browser/WhatsApp and coding runtime regressions have NOT been live tested.

## Incomplete and unverified
- Real Windows Explorer window/highlight, GUI clicks, screenshots, OCR/Tesseract and VLM inference require the actual machine; mocked success is not live verification.
- General natural-language autonomous desktop planning, visual postcondition/recovery loops and unified GUI risk approvals remain incomplete. The new multi-step interface accepts explicit structured steps; it does not pretend to solve arbitrary desktop tasks.
- Direct file-open after search, stateful Explorer parent/subfolder navigation and cross-volume moves are not added. Existing app launch/VS Code and input tools remain available.
- No Android build/install changes; this checkout cannot validate Android 3.9 Build 8 parity.
- Existing VLM uses local `qwen3-vl:4b-instruct`, resized images (1600px edge) and a 120-second timeout. Hardware fit, latency and memory were not benchmarked. No CNN added: no measured task benefit or labeled target dataset. OpenCV was not needed for the implemented grayscale/autocontrast OCR. Current external VLM alternatives and pricing were not benchmarked; cloud screen upload remains absent.
- No performance claim or guaranteed two-second latency. Search defaults: five-second budget, 100,000 entries, 100 reported matches; incomplete results explicitly marked.

## Remaining machine steps
Review draft diff against the latest local Windows files before merging; do not overwrite uncommitted local improvements. Apply the reviewed commit, optionally install `requirements-computer-use.txt` plus the local Tesseract executable, configure permitted roots, and run the test command. Then validate Explorer selection, voice overwrite rejection/approval, GUI/OCR, local VLM description, browser and voice/provider regressions on Windows. No paid API, model download or deployment was performed.
