from contextlib import asynccontextmanager
from pathlib import Path
import json
import logging
import os
import re

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
import httpx
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gohar")

ROOT = Path(__file__).resolve().parent
KNOWLEDGE_DIR = ROOT
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate").strip()
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()
MODEL_NAME = os.getenv("GOHAR_MODEL", "gemma4:e2b").strip()
OLLAMA_TIMEOUT = float(os.getenv("GOHAR_OLLAMA_TIMEOUT", "300"))
RUNNING_ON_RENDER = os.getenv("RENDER", "").lower() == "true"

LANGUAGE_NAMES = {
    "hi": "Hindi", "en": "English", "bn": "Bengali", "te": "Telugu", "mr": "Marathi",
    "ta": "Tamil", "ur": "Urdu", "gu": "Gujarati", "kn": "Kannada", "or": "Odia",
    "ml": "Malayalam", "pa": "Punjabi", "as": "Assamese", "mai": "Maithili",
    "bho": "Bhojpuri", "ks": "Kashmiri", "ne": "Nepali", "sat": "Santali",
    "sd": "Sindhi", "mni": "Meitei (Manipuri)",
}

DEFAULT_DEV_ORIGINS = (
    "http://localhost:5500,http://127.0.0.1:5500,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "https://gohar.onrender.com"
)
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("GOHAR_ALLOWED_ORIGINS", DEFAULT_DEV_ORIGINS).split(",")
    if origin.strip()
]
ALLOWED_ORIGIN_REGEX = os.getenv(
    "GOHAR_ALLOWED_ORIGIN_REGEX",
    r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.github\.io|https://.*\.onrender\.com",
)

EXCLUDED_KNOWLEDGE_FILES = {
    "readme.md",
    "contributing.md",
    "license.md",
    "license",
}

KNOWLEDGE_CACHE: dict[str, str] = {}


def load_knowledge_base() -> dict[str, str]:
    """Scan and preload all agricultural Markdown knowledge files into memory."""
    global KNOWLEDGE_CACHE
    docs: dict[str, str] = {}
    for path in KNOWLEDGE_DIR.glob("*.md"):
        if path.name.lower() in EXCLUDED_KNOWLEDGE_FILES or path.name.startswith("."):
            continue
        try:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                docs[path.name] = content
        except Exception as exc:
            logger.warning("Could not read knowledge file %s: %s", path.name, exc)
    KNOWLEDGE_CACHE = docs
    logger.info("Loaded %d knowledge documents: %s", len(KNOWLEDGE_CACHE), list(KNOWLEDGE_CACHE.keys()))
    return KNOWLEDGE_CACHE


def retrieve_context(question: str) -> tuple[str, str | None]:
    """Find the in-memory knowledge note with the highest relevance to the query."""
    if not KNOWLEDGE_CACHE:
        load_knowledge_base()

    if not KNOWLEDGE_CACHE:
        return ("", None)

    # Tokenize question terms (ignoring punctuation and short tokens)
    clean_question = re.sub(r"[^\w\s\u0900-\u097F]", " ", question.lower())
    terms = {word.strip() for word in clean_question.split() if len(word.strip()) > 2}

    best_text, best_name, best_score = "", None, 0
    for name, text in KNOWLEDGE_CACHE.items():
        text_lower = text.lower()
        score = sum(1 for term in terms if term in text_lower)
        if score > best_score:
            best_text, best_name, best_score = text, name, score

    if best_score > 0 and best_name:
        return (best_text[:7000], best_name)
    return ("", None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: preload knowledge & create connection pool."""
    load_knowledge_base()
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=10.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="Gohar API",
    description="Local-language farming advisor prototype",
    version="1.0.0",
    lifespan=lifespan,
)

# GZip compression for responsive transfer over rural 2G/3G/4G connections
app.add_middleware(GZipMiddleware, minimum_size=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject baseline web security headers."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self)"
    return response


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


async def ask_gemma(
    client: httpx.AsyncClient,
    question: str,
    context: str,
    language_code: str = "hi",
) -> str:
    """Send agricultural query with retrieved knowledge context to Gemma model."""
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

    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}

    response = await client.post(OLLAMA_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    answer = data.get("response", "").strip()
    if not answer:
        raise RuntimeError("Empty response from model")
    return answer


async def translate_ui(
    client: httpx.AsyncClient,
    texts: list[str],
    language_code: str,
) -> list[str]:
    """Translate UI strings using the configured LLM inference service."""
    language_name = LANGUAGE_NAMES[language_code]
    prompt = f"""Translate each item in the JSON array below from English into {language_name}.
Use natural, concise wording and the language's normal writing system, suitable for an Indian farming app.
Keep meaning, numbering, emoji, placeholders such as {{url}}, URLs, and names/acronyms such as Gohar, Gemma, ICAR, IMD, KVK, NPK, DAP, SSP and MOP intact.
Do not add advice or explanations.
Return only a JSON array of strings, with exactly {len(texts)} items in the same order.

Items:
{json.dumps(texts, ensure_ascii=False)}
"""

    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

    response = await client.post(OLLAMA_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    result = data.get("response", "").strip()

    try:
        translations = json.loads(result)
    except (TypeError, ValueError) as error:
        raise RuntimeError("The language model returned invalid translation data") from error

    if isinstance(translations, dict):
        translations = translations.get("translations")

    if (
        not isinstance(translations, list)
        or len(translations) != len(texts)
        or not all(isinstance(item, str) for item in translations)
    ):
        raise RuntimeError("The language model returned an incomplete translation")

    return translations


@app.get("/", include_in_schema=False)
async def homepage():
    """Serve the single-page application with immediate revalidation cache header."""
    return FileResponse(
        ROOT / "index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


@app.get("/style.css", include_in_schema=False)
async def stylesheet():
    return FileResponse(
        ROOT / "style.css",
        media_type="text/css",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/script.js", include_in_schema=False)
async def frontend_script():
    return FileResponse(
        ROOT / "script.js",
        media_type="text/javascript",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/health")
async def health():
    """Readiness probe reporting service status, loaded knowledge, and model configuration."""
    return {
        "status": "ok",
        "service": "gohar-api",
        "version": "1.0.0",
        "model": MODEL_NAME,
        "knowledge_documents": list(KNOWLEDGE_CACHE.keys()),
        "inference_host": OLLAMA_URL.split("/api")[0] if "/api" in OLLAMA_URL else OLLAMA_URL,
    }


def _get_http_client(request: Request) -> httpx.AsyncClient:
    """Retrieve shared HTTP client from app state, or fallback to temporary instance."""
    client = getattr(request.app.state, "http_client", None)
    if client is not None:
        return client
    return httpx.AsyncClient(timeout=httpx.Timeout(OLLAMA_TIMEOUT, connect=10.0))


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    """Process farmer question, retrieve relevant agronomy context, and generate answer."""
    context, source = retrieve_context(body.question)
    client = _get_http_client(request)

    try:
        answer = await ask_gemma(client, body.question, context, body.language)
        return ChatResponse(answer=answer, source=source, mode="gemma")
    except (httpx.ConnectError, httpx.ConnectTimeout):
        if RUNNING_ON_RENDER:
            fallback = (
                "AI service tak connection nahi ho pa raha. Render ke Environment settings mein "
                "OLLAMA_URL ko reachable Ollama-compatible /api/generate endpoint par set karein. "
                "localhost ya 127.0.0.1 Render container ko refer karte hain, aapke PC ko nahi."
            )
        else:
            fallback = (
                "Ollama se connection nahi ho pa raha. Ollama app chalu karke dobara koshish karein. "
                "Agar Ollama installed nahi hai, use install karke Gemma model download karein."
            )
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except httpx.TimeoutException:
        fallback = "Gemma ko jawab dene mein zyada samay lag raha hai. Thodi der baad dobara koshish karein."
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except httpx.HTTPStatusError as error:
        if error.response is not None and error.response.status_code == 404:
            fallback = f"Ollama mein {MODEL_NAME} model nahi mila. Terminal mein `ollama pull {MODEL_NAME}` chalayein."
        else:
            fallback = "Ollama se jawab nahi mila. Ollama chalu hai aur Gemma model available hai, yeh check karein."
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except httpx.RequestError:
        fallback = "Ollama request mein dikkat aayi. Ollama server aur network settings check karein."
        return ChatResponse(answer=fallback, source=source, mode="fallback")
    except (RuntimeError, ValueError):
        fallback = (
            "Gemma se sahi jawab nahi mila. Kripya thodi der baad dobara koshish karein. "
            "Tab tak fasal, crop age aur symptoms note karein; kisi bhi dawa ki matra local krishi expert se confirm karein."
        )
        return ChatResponse(answer=fallback, source=source, mode="fallback")


@app.post("/translate-ui", response_model=TranslateUIResponse)
async def translate_interface(body: TranslateUIRequest, request: Request):
    """Translate UI strings into one of the 20 supported languages."""
    if body.language not in LANGUAGE_NAMES:
        raise HTTPException(status_code=422, detail="Choose a supported interface language.")
    if not body.texts or len(body.texts) > 64:
        raise HTTPException(status_code=422, detail="Send between 1 and 64 interface strings at a time.")
    if any(not text.strip() or len(text) > 600 for text in body.texts):
        raise HTTPException(status_code=422, detail="Each interface string must contain 1 to 600 characters.")

    client = _get_http_client(request)
    try:
        translations = await translate_ui(client, body.texts, body.language)
        return TranslateUIResponse(translations=translations)
    except (httpx.ConnectError, httpx.ConnectTimeout) as error:
        detail = (
            "The configured AI service is unreachable. Set OLLAMA_URL in Render to a reachable "
            "Ollama-compatible /api/generate endpoint; localhost refers to the Render container."
            if RUNNING_ON_RENDER
            else "Ollama is unavailable. Start Ollama and try the language switch again."
        )
        raise HTTPException(status_code=503, detail=detail) from error
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="The local model took too long to translate the interface.") from error
    except httpx.RequestError as error:
        raise HTTPException(status_code=502, detail="The local model could not translate the interface.") from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
