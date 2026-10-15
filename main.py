from pathlib import Path
import json
import os

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
MODEL_NAME = os.getenv("GOHAR_MODEL", "gemma4:e2b")
LANGUAGE_NAMES = {
    "hi": "Hindi", "en": "English", "bn": "Bengali", "te": "Telugu", "mr": "Marathi",
    "ta": "Tamil", "ur": "Urdu", "gu": "Gujarati", "kn": "Kannada", "or": "Odia",
    "ml": "Malayalam", "pa": "Punjabi", "as": "Assamese", "mai": "Maithili",
    "bho": "Bhojpuri", "ks": "Kashmiri", "ne": "Nepali", "sat": "Santali",
    "sd": "Sindhi", "mni": "Meitei (Manipuri)",
}
DEFAULT_DEV_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000"
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("GOHAR_ALLOWED_ORIGINS", DEFAULT_DEV_ORIGINS).split(",") if origin.strip()]

app = FastAPI(title="Gohar API", description="Local-language farming advisor prototype")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=os.getenv("GOHAR_ALLOWED_ORIGIN_REGEX", r"https?://(localhost|127\.0\.0\.1)(:\d+)?"),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1500)
    language: str = Field(default="hi", max_length=8)


class ChatResponse(BaseModel):
    answer: str
    source: str | None = None
    mode: str


class TranslateUIRequest(BaseModel):
    language: str = Field(min_length=2, max_length=8)
    texts: list[str]


class TranslateUIResponse(BaseModel):
    translations: list[str]


def retrieve_context(question: str) -> tuple[str, str | None]:
    """Find the local note with the most matching question terms."""
    terms = {word.lower().strip(".,?!।") for word in question.split() if len(word) > 2}
    best_text, best_name, best_score = "", None, 0
    for path in (KNOWLEDGE_DIR / name for name in ("wheat.md", "paddy.md")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        score = sum(1 for term in terms if term in text.lower())
        if score > best_score:
            best_text, best_name, best_score = text, path.name, score
    return (best_text[:7000], best_name) if best_name else ("", None)


def ask_gemma(question: str, context: str, language_code: str = "hi") -> str:
    language_name = LANGUAGE_NAMES.get(language_code, "Hindi")
    prompt = f"""You are Gohar, a cautious farming information assistant for farmers in India.
Answer in simple, natural {language_name}, using its normal writing system. Keep technical farming terms easy to understand.
If the farmer's question is unclear or important details are missing, ask a short follow-up question in {language_name} before giving specific advice.
Use the agricultural context below when relevant. Do not invent facts, chemical doses, or weather alerts.
If details are missing, ask a clarifying question. Distinguish possible causes from confirmed diagnoses.
For pesticide decisions, advise following the product label and consulting a qualified local agriculture expert.
If the context does not answer the question, say so clearly.

AGRICULTURAL CONTEXT:
{context or "No relevant curated source was found. Ask clarifying questions and avoid specific prescriptions."}

FARMER QUESTION:
{question}

Helpful answer:"""
    response = requests.post(
        OLLAMA_URL,
        headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {},
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    answer = response.json().get("response", "").strip()
    if not answer:
        raise RuntimeError("Empty response from model")
    return answer


def translate_ui(texts: list[str], language_code: str) -> list[str]:
    """Translate interface strings locally with the configured Ollama model."""
    language_name = LANGUAGE_NAMES[language_code]
    prompt = f"""Translate each item in the JSON array below from English into {language_name}.
Use natural, concise wording and the language's normal writing system, suitable for an Indian farming app.
Keep meaning, numbering, emoji, placeholders such as {{url}}, URLs, and names/acronyms such as Gohar, Gemma, ICAR, IMD, KVK, NPK, DAP, SSP and MOP intact.
Do not add advice or explanations.
Return only a JSON array of strings, with exactly {len(texts)} items in the same order.

Items:
{json.dumps(texts, ensure_ascii=False)}
"""
    response = requests.post(
        OLLAMA_URL,
        headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {},
        json={"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}},
        timeout=120,
    )
    response.raise_for_status()
    result = response.json().get("response", "").strip()
    try:
        translations = json.loads(result)
    except (TypeError, ValueError) as error:
        raise RuntimeError("The language model returned invalid translation data") from error
    if isinstance(translations, dict):
        translations = translations.get("translations")
    if not isinstance(translations, list) or len(translations) != len(texts) or not all(isinstance(item, str) for item in translations):
        raise RuntimeError("The language model returned an incomplete translation")
    return translations


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(ROOT / "index.html")


@app.get("/style.css", include_in_schema=False)
def stylesheet():
    return FileResponse(ROOT / "style.css", media_type="text/css")


@app.get("/script.js", include_in_schema=False)
def frontend_script():
    return FileResponse(ROOT / "script.js", media_type="text/javascript")


@app.get("/health")
def health():
    return {"status": "ok", "service": "gohar-api"}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    context, source = retrieve_context(body.question)
    try:
        answer = ask_gemma(body.question, context, body.language)
        return ChatResponse(answer=answer, source=source, mode="gemma")
    except requests.ConnectionError:
        fallback = (
            "Ollama se connection nahi ho pa raha. Ollama app chalu karke dobara koshish karein. "
            "Agar Ollama installed nahi hai, use install karke Gemma model download karein."
        )
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except requests.Timeout:
        fallback = "Gemma ko jawab dene mein zyada samay lag raha hai. Thodi der baad dobara koshish karein."
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            fallback = f"Ollama mein {MODEL_NAME} model nahi mila. Terminal mein `ollama pull {MODEL_NAME}` chalayein."
        else:
            fallback = "Ollama se jawab nahi mila. Ollama chalu hai aur Gemma model available hai, yeh check karein."
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except requests.RequestException:
        fallback = "Ollama request mein dikkat aayi. Ollama server aur network settings check karein."
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except (RuntimeError, ValueError):
        fallback = (
            "Gemma se sahi jawab nahi mila. Kripya thodi der baad dobara koshish karein. "
            "Tab tak fasal, crop age aur symptoms note karein; kisi bhi dawa ki matra local krishi expert se confirm karein."
        )
        return ChatResponse(answer=fallback, source=source, mode="fallback")


@app.post("/translate-ui", response_model=TranslateUIResponse)
def translate_interface(body: TranslateUIRequest):
    if body.language not in LANGUAGE_NAMES:
        raise HTTPException(status_code=422, detail="Choose a supported interface language.")
    if not body.texts or len(body.texts) > 64:
        raise HTTPException(status_code=422, detail="Send between 1 and 64 interface strings at a time.")
    if any(not text.strip() or len(text) > 600 for text in body.texts):
        raise HTTPException(status_code=422, detail="Each interface string must contain 1 to 600 characters.")
    try:
        return TranslateUIResponse(translations=translate_ui(body.texts, body.language))
    except requests.ConnectionError as error:
        raise HTTPException(status_code=503, detail="Ollama is unavailable. Start Ollama and try the language switch again.") from error
    except requests.Timeout as error:
        raise HTTPException(status_code=504, detail="The local model took too long to translate the interface.") from error
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail="The local model could not translate the interface.") from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
