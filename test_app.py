import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch
import main
from main import app, load_knowledge_base, retrieve_context


@pytest.fixture(autouse=True)
def setup_knowledge():
    """Ensure knowledge base is loaded for all tests."""
    load_knowledge_base()


def test_knowledge_base_loading():
    """Verify that agricultural knowledge files are cached in memory."""
    assert len(main.KNOWLEDGE_CACHE) >= 5
    expected_docs = {"wheat.md", "paddy.md", "mustard.md", "maize.md", "pulses.md"}
    assert expected_docs.issubset(set(main.KNOWLEDGE_CACHE.keys()))
    assert "readme.md" not in main.KNOWLEDGE_CACHE


def test_retrieval_wheat():
    context, doc_name = retrieve_context("गेहूँ में पीला रतुआ का इलाज क्या है?")
    assert doc_name == "wheat.md"
    assert len(context) > 0


def test_retrieval_paddy():
    context, doc_name = retrieve_context("धान की नर्सरी और खैरा रोग के लक्षण")
    assert doc_name == "paddy.md"
    assert len(context) > 0


def test_retrieval_mustard():
    context, doc_name = retrieve_context("सरसों में माहू कीट नियंत्रण और सल्फर की मात्रा")
    assert doc_name == "mustard.md"
    assert len(context) > 0


def test_retrieval_maize():
    context, doc_name = retrieve_context("मक्का में फॉल आर्मीवर्म की दवा")
    assert doc_name == "maize.md"
    assert len(context) > 0


def test_retrieval_pulses():
    context, doc_name = retrieve_context("चना में उकठा रोग और अरहर की उन्नत किस्में")
    assert doc_name == "pulses.md"
    assert len(context) > 0


def test_retrieval_unrelated():
    context, doc_name = retrieve_context("space rocket launching technology")
    assert doc_name is None
    assert context == ""


@pytest.mark.anyio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "gohar-api"
        assert "wheat.md" in data["knowledge_documents"]


@pytest.mark.anyio
async def test_static_routes_and_security_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Homepage
        home_res = await client.get("/")
        assert home_res.status_code == 200
        assert "text/html" in home_res.headers.get("content-type", "")
        assert home_res.headers.get("x-content-type-options") == "nosniff"
        assert home_res.headers.get("x-frame-options") == "SAMEORIGIN"

        # Stylesheet
        css_res = await client.get("/style.css")
        assert css_res.status_code == 200
        assert "text/css" in css_res.headers.get("content-type", "")

        # Script
        js_res = await client.get("/script.js")
        assert js_res.status_code == 200
        assert "javascript" in js_res.headers.get("content-type", "")


@pytest.mark.anyio
async def test_chat_success():
    with patch("main.ask_gemma", new_callable=AsyncMock) as mock_gemma:
        mock_gemma.return_value = "गेहूँ में पहली सिंचाई 20-25 दिन पर CRI अवस्था में करें।"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"question": "गेहूँ में पहली सिंचाई कब करें?", "language": "hi"})
            assert response.status_code == 200
            data = response.json()
            assert data["mode"] == "gemma"
            assert data["source"] == "wheat.md"
            assert "CRI" in data["answer"]


@pytest.mark.anyio
async def test_chat_fallback_when_offline(monkeypatch):
    monkeypatch.setattr(main, "OLLAMA_URL", "http://127.0.0.1:9999/api/generate")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/chat", json={"question": "गेहूँ में खाद कब डालें?", "language": "hi"})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "fallback"
        assert len(data["answer"]) > 10
        assert data["source"] == "wheat.md"


@pytest.mark.anyio
async def test_chat_input_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Question too short (< 2 chars)
        res = await client.post("/chat", json={"question": "a", "language": "hi"})
        assert res.status_code == 422


@pytest.mark.anyio
async def test_translate_ui_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Unsupported language
        res = await client.post("/translate-ui", json={"language": "invalid_lang", "texts": ["hello"]})
        assert res.status_code == 422
