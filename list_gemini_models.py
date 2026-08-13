"""One-off helper: list Gemini models your API key can actually call via generateContent.

Run: python list_gemini_models.py
(reads GEMINI_API_KEY from .env, same as the bot)
"""

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

print(f"{'model':<40} {'supports generateContent':<28} thinking")
print("-" * 80)
for m in client.models.list():
    name = m.name.removeprefix("models/")
    supports_gc = "generateContent" in (m.supported_actions or [])
    if supports_gc and "flash" in name.lower():
        thinking = getattr(m, "thinking", None)
        print(f"{name:<40} {'yes':<28} {thinking}")
