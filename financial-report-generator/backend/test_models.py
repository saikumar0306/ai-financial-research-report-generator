import google.genai as genai
from config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)
models_to_test = ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]

print(f"Testing Gemini API connectivity across candidate models...")
for m in models_to_test:
    try:
        res = client.models.generate_content(model=m, contents="Hi")
        text = (res.text or "").strip()
        print(f"SUCCESS: model={m!r} -> {text[:40]!r}")
    except Exception as e:
        err_msg = str(e).replace("\n", " ")
        print(f"FAILED: model={m!r} -> {err_msg[:90]}")

