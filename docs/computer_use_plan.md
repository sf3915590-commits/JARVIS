# Incremental computer-use upgrade
Baseline: 4e0497f7a10c176476e69c44b7e85aa867dd1f91 (GitHub main).
This checkout has no Android source and cannot establish equivalence to Android 3.9 Build 8 or uncommitted Windows code.

Existing: Tahrun voice/main execution; brain local/cloud routing; coding_agent website generation, backups, VS Code, npm and Playwright smoke checks; actions mouse/keyboard; windows_control installed app launch; file_manager substring search and PDF reading; screen_agent UIA and PyAutoGUI; screen_vision MSS capture and Ollama VLM; browser/WhatsApp modules.

Plan before edits:
1. Extend file_manager with scoped paths, bounded exact/partial/extension/fuzzy/latest search, duplicate reporting, verified creation/edit/move/read and Explorer reveal. Preserve old APIs.
2. Add a thin computer_tasks coordinator: deterministic command parsing, expiring disambiguation, bounded sequential tool plans, stop on failure; never execute generated shell/code.
3. Integrate through orchestrator and Tahrun execution without changing brain/providers or browser code.
4. Extend existing screen_agent with optional OCR and truthful dependency detection; keep existing VLM and capture. No new CNN: no task dataset or demonstrated benefit. No automatic VLM/model download or paid calls.
5. Test direct filesystem behavior, permission and ambiguity failures, routing, mocked Windows/GUI/OCR; clearly distinguish these from live Windows verification.

Security: allowed roots default to user home; additional roots explicitly configured locally. Protected repository writes denied by default. No delete API. Existing-file edits require a host callback approval; command/model fields cannot grant approval. Audit logs contain operation/path, never contents. Symlinks/reparse paths rejected. New GUI operations expose dispatched vs verified state. Existing legacy GUI pathways are preserved and are not represented as fully secured.
