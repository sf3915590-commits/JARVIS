import re

# Contacts explicitly trusted by the user for sensitive WhatsApp messages.
TRUSTED_CONTACTS = {
    "kaya",
    "k a y a",
    "kayani",
    "ali 2",
    "ali two",
    "anish",
    "ames",
    "arman ff",
}

SENSITIVE_WORDS = {
    "password", "otp", "pin", "cvv", "bank", "bank account",
    "account number", "ifsc", "upi", "upi pin", "card number",
    "aadhaar", "pan number", "passport number", "private key",
    "secret key", "api key", "token", "verification code",
    "security code", "live location", "money", "payment",
    "transfer", "send money", "medical", "health", "private",
    "confidential",
}

def normalize_name(name):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(name).lower())).strip()

def is_trusted_contact(name):
    n = normalize_name(name)
    trusted = {normalize_name(x) for x in TRUSTED_CONTACTS}
    if n in trusted:
        return True
    compact = n.replace(" ", "")
    return compact in {"kaya", "kayani", "ali2", "alitwo", "anish", "ames", "armanff"}

def is_sensitive_message(message):
    text = str(message).lower()
    return any(word in text for word in SENSITIVE_WORDS)

def needs_message_approval(name, message):
    return is_sensitive_message(message) and not is_trusted_contact(name)

def explicit_shutdown_command(text):
    c = re.sub(r"\\s+", " ", str(text).lower().strip())
    c = re.sub(r"[^a-z0-9\\s]", "", c)
    c = re.sub(r"\\s+", " ", c).strip()

    shutdown_phrases = {
        "shutdown",
        "shut down",
        "shutdown jarvis",
        "shut down jarvis",
        "jarvis shutdown",
        "jarvis shut down",
        "jarvis shut down yourself",
        "shut down yourself",
        "jarvis shutdown yourself",
        "shutdown yourself",
        "jarvis shut yourself down",
        "turn yourself off",
        "turn off yourself",
        "turn off jarvis",
        "jarvis turn off",
        "stop jarvis",
        "jarvis stop",
        "band ho jao",
        "jarvis band ho jao",
        "jarvis band ho ja",
        "exit jarvis",
        "goodbye jarvis",
    }

    return c in shutdown_phrases


def parse_delete_request(text):
    c = re.sub(r"\s+", " ", str(text).lower().strip())
    patterns = [
        (r"^(?:delete|remove) (?:the )?(?:file )?(.+)$", "file"),
        (r"^(?:delete|remove) (?:the )?folder (.+)$", "folder"),
    ]
    for pattern, kind in patterns:
        m = re.match(pattern, c, re.IGNORECASE)
        if m:
            target = m.group(1).strip(" .:-")
            if target and target not in {"file", "folder", "this"}:
                return kind, target
    return None, None
