# Gohar — AI Kheti Salahkar 🌾

Open-source prototype for local-language farming guidance for smallholder farmers near Lucknow.

## Current status
- Responsive HTML/CSS/JavaScript frontend.
- FastAPI backend with a simple keyword retrieval baseline.
- Optional local Gemma inference through an Ollama-compatible API.
- Starter wheat and paddy knowledge notes.
- Clear connection and model-unavailable messages in the chat UI.
- Language selection for typed questions, browser speech input and spoken answers in 20 languages: Hindi, English, Bengali, Telugu, Marathi, Tamil, Urdu, Gujarati, Kannada, Odia, Malayalam, Punjabi, Assamese, Maithili, Bhojpuri, Kashmiri, Nepali, Santali, Sindhi and Meitei (Manipuri).
- A seasonal checklist for Kharif, Rabi and Zaid, plus a crop nutrition guide for wheat, rice, maize, mustard and pulses with ICAR/Soil Health Card references.

**Important:** This is a hackathon prototype, not a validated agricultural advisory service. The starter knowledge notes are not sufficient for precise crop treatment recommendations. Verify important advice with current local agricultural experts and official sources.

Browser speech recognition and speech synthesis are used for voice chat. Language availability and voice quality depend on the browser and installed speech services. Seasonal checklists are static reminders, not live weather, pest, or push alerts. Fertilizer guidance is educational; use a current Soil Health Card and local crop package for rates.

## Run locally on Windows

From Command Prompt in the project folder, start the app:

```cmd
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/` for the UI. The API health check is `http://127.0.0.1:8000/health`.

If dependencies are not installed in the virtual environment, run `.venv\Scripts\python.exe -m pip install -r requirements.txt` once. This uses the virtual environment's Python and pip.

## Connect Gemma through Ollama

Gohar uses Ollama's local API at `http://localhost:11434/api/generate` and defaults to `gemma4:e2b` (`GOHAR_MODEL` can override the tag).

1. Install [Ollama for Windows](https://ollama.com/download/windows) and open the Ollama app. Ollama serves its local API at `http://localhost:11434`.
2. In a new Command Prompt, download and start Gemma once:

   ```cmd
   ollama run gemma4:e2b
   ```

   The official Ollama library currently lists this model at roughly 4.6–7.5 GB, so make sure you have enough disk space and memory. Type `/bye` after it answers.
3. Start Gohar's backend in another Command Prompt with the commands above.
4. Open `http://127.0.0.1:8000/` and ask a question. If the model is missing, Gohar will tell you to run `ollama pull gemma4:e2b`; if Ollama is offline, it will say to start the Ollama app.

Ollama's generate endpoint accepts a model name and prompt and returns a non-streaming response when `stream` is false, which is how this backend calls it. See the [Ollama Gemma 4 tags](https://ollama.com/library/gemma4/tags), [Windows setup](https://docs.ollama.com/windows), and [generate API](https://docs.ollama.com/api/generate).

## Deployment notes

The FastAPI app serves the frontend and API from one origin. A hosted app cannot reach Ollama running on your personal computer; configure `OLLAMA_URL` to point to an inference service reachable by the host. The backend accepts an optional `OLLAMA_API_KEY` environment variable and sends it as a Bearer token. Store that key in the hosting provider's secret settings, never in frontend files or source control. Set `GOHAR_MODEL` to the model tag accepted by that inference service. Prompts will be sent to the configured inference provider.

For cross-origin hosting, set `GOHAR_ALLOWED_ORIGINS` to a comma-separated list of trusted frontend origins. Same-origin deployment does not need a CORS exception.

If the frontend and backend use different public domains, set the `gohar-api-url` meta tag in `index.html` to the backend's base URL (for example, `https://your-api.example.com`, without `/chat`).

## Repository layout
```text
index.html      Static web UI
style.css       Responsive interface styles
script.js       Chat interactions and API connection
main.py         FastAPI API and retrieval/model call
wheat.md        Starter wheat note
paddy.md        Starter paddy note
README.md       Setup and limitations
LICENSE         Project license
CONTRIBUTING.md Contribution guide
```

## Open-source and licensing
Project code is offered under the MIT License. Third-party models and documents retain their own licenses/terms. Do not redistribute agricultural documents unless their terms permit it.

## Roadmap
- Replace keyword retrieval with BM25 and add cited, region-specific sources.
- Evaluate Hindi and Awadhi responses with local speakers/agriculture experts.
- Add voice and weather API only after the core workflow is reliable.
- Add automated tests and production request limits before public use.
