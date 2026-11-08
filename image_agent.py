import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except Exception:
    pass
import urllib.parse
import urllib.request

def generate_image(prompt):
    prompt = str(prompt or "").strip()
    if not prompt:
        return False, "Boss, image kis cheez ki generate karni hai?"

    key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    if not key:
        return False, "Boss, Pollinations API key configured nahi hai."

    try:
        encoded = urllib.parse.quote(prompt, safe="")
        url = f"https://gen.pollinations.ai/image/{encoded}?model=openai/gpt-image-2.5-flare&quality=medium"

        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {key}"}
        )

        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()

        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "JARVIS_HUD_V2",
            "public"
        )
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, "jarvis-generated.png")
        with open(output_file, "wb") as f:
            f.write(data)

        return True, "Boss, image generate ho gayi."

    except Exception as e:
        return False, f"Boss, image generation failed: {e}"

