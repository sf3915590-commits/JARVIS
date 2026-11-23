# Android emulator pairing: verified source contract and safe handoff

> Status: **not paired remotely**. This handoff preserves the running Windows JARVIS and Tailscale services. The local Windows files were not modified or restarted from GitHub.

## Evidence from Android source supplied on 23 November 2026

The uploaded Android `PairingClient.kt` expects a trusted HTTPS URL ending **exactly** in `/api/chat` and makes:

- `POST /api/pairing/enroll` with a single-use `tpc_` code and device label. A bearer `tpb_` session with scope `companion:chat` is returned.
- `POST /api/pairing/session` with the bearer for verification.
- `POST /api/pairing/logout` to revoke it.
- `POST /api/chat` with bearer, `provider=jarvis`, text messages, empty attachments.

Android requires certificate validation (optionally explicit SHA-256 certificate pin), verifies the session before storing it, and encrypts tokens in Android Keystore.

The uploaded Android `TESTER_BUILD.md` documents an existing *separate* Windows service, **`jarvis_companion_server.py`**, with local HTTPS binding at port **8778** and a previously tested Android emulator TLS pairing and Ollama chat flow. That means a displayed “pairing required” is **not sufficient evidence of broken client code**; the service may simply be unstarted/unconfigured. This Python server file was **not present in GitHub main** when checked, but may exist in the user’s later Windows workspace. **Never recreate, overwrite, or merge over the user's newer local source blindly.**

## Safe default for the Android Studio emulator

Android's `10.0.2.2` host alias normally reaches Windows host loopback. Subject to the actual existing server CLI:

```powershell
# In the local JARVIS project, ONLY if jarvis_companion_server.py exists.
python jarvis_companion_server.py init 10.0.2.2
python jarvis_companion_server.py serve --listen 127.0.0.1 --port 8778
# Run in another terminal, with owner confirmation:
python jarvis_companion_server.py code profile-1
```

In Android **Main**, use `https://10.0.2.2:8778/api/chat`, verify and save the actual server certificate's SHA-256 fingerprint, approve `profile-1`, enroll with the desktop-issued one-time code, and verify the saved session. Chat needs a running local Ollama model.

Run `tools/start_android_emulator_pairing.cmd` from the Windows project folder to automate the normal local setup without stopping or changing any existing Windows service. The launcher refuses to proceed if `jarvis_companion_server.py` is missing or port 8778 already belongs to another process. A human must still confirm the owner profile and enter the secret one-time code in Android.

## Avoid unsafe shortcuts

The Tailscale Serve configuration previously inspected maps TLS TCP :8444 to the **legacy desktop HTTP chat backend :8766**. This is **not proof of a mobile bearer-authenticated pairing API** and must **not** be substituted for the documented separate HTTPS service. Do not forward the legacy HTTP chat bridge to the Internet, convert chat into OS commands, infer HTTPS from untrusted forwarding headers, bypass certificate pinning/hostname checks, disable Android Play Protect, or include certificate private keys/codes/tokens in Git.

GitHub `main` is older than the user's current local Android and Windows implementation. Any further integration needs a review of local **`jarvis_companion_server.py`**, **`jarvis_android_pairing.py`** and current `JARVIS_CHAT_WORKSPACE/backend/server.py`, rather than assuming the GitHub files reflect the running code.

### Checks before claiming a fix

Observe real owner-confirmed code issuance, TLS enrollment, session verification, actual Ollama reply, replay rejection, logout, expired/revoked token rejection on the user's Windows host and emulator. The uploaded tester build notes report some of these as previously tested on a different emulator, but **this handoff did not rerun them**.
