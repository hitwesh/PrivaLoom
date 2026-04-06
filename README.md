# PrivaLoom

Privacy-first distributed learning prototype for small language models.

PrivaLoom explores how language models can improve collaboratively while minimizing direct exposure of private user data. The current codebase implements a working prototype with local model inference, a FastAPI backend, and a client-side update simulation loop.

## What this project is

PrivaLoom is not only a chatbot. It is an early framework for privacy-aware, federated-style learning workflows with a chatbot interface as one practical entry point.

Project intent:
- move learning close to user data
- transmit compact learning signals instead of raw datasets
- aggregate updates into a shared model path
- incrementally evolve toward stronger privacy guarantees

For product vision and philosophy, see:
- `docs/PROJECT_BIBLE.md`

For detailed technical design, see:
- `docs/architecture.md`

## Current implementation status

Implemented now:
- local model bootstrap and loading (`distilgpt2`)
- standalone CLI chat loop
- FastAPI server with `/`, `/chat`, `/send-update`
- client CLI that:
  - chats through the server
  - computes local gradient slices
  - sends compact update payloads
- client-side gradient clipping + Gaussian noise (basic differential privacy)
- server-side in-memory update buffering and averaging
- selective update application to last model parameters

Partially implemented:
- federated-style aggregation logic (prototype-level)
- update mapping/selective update strategy

Not implemented yet:
- update encryption and secure aggregation
- frontend UI
- automated tests and CI pipeline
- production hardening (auth, persistence, observability)

DP configuration (client)
- `DP_ENABLED` (default: `true`)
- `DP_MAX_GRAD_NORM` (default: `1.0`)
- `DP_NOISE_STDDEV` (default: `0.001`)

## Repository structure

```text
PrivaLoom/
|- client/
|  |- client.py
|- docs/
|  |- CHANGELOG.md
|  |- PROJECT_BIBLE.md
|  |- architecture.md
|  |- roadmap.sh
|- frontend/
|- model/
|  |- __init__.py
|  |- download_model.py
|  |- load_model.py
|  |- config.json
|  |- generation_config.json
|  |- tokenizer_config.json
|  |- tokenizer.json
|  |- model.safetensors
|- server/
|  |- __init__.py
|  |- api.py
|- utils/
|- data.txt
|- main.py
|- requirements.txt
```

Notes:
- Model artifacts in `model/` are generated/used locally.
- `.gitignore` excludes heavy model files while preserving source files in `model/*.py`.

## Architecture at a glance

Runtime modes:
1. Local-only mode
- run `main.py`
- no HTTP server required
- useful for quick inference checks

2. Client-server simulation mode
- run FastAPI server
- run client CLI separately
- client sends prompts to `/chat`
- client computes local updates and sends to `/send-update`
- server applies averaged updates after threshold

High-level data path:
- user text -> chat response path (currently server-side inference)
- local text -> gradient slices -> server aggregation

Detailed architecture and trust boundaries:
- `docs/architecture.md`

## Requirements

- Python 3.10+ (3.11 recommended)
- pip
- internet access for first-time model download (if local artifacts absent)
- enough disk/RAM for DistilGPT2 artifacts and runtime tensors

Main dependencies are pinned in:
- `requirements.txt`

## Setup

### 1) Create and activate a virtual environment

Windows PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Optional: pre-download model artifacts

```bash
python model/download_model.py
```

If you skip this step, the first run of model loading will auto-download and cache assets into `./model`.

## Running the project

## Option A: Local standalone chat

```bash
python main.py
```

This launches a direct console chat loop using `generate_response` from `model/load_model.py`.

## Option B: API server + client simulation

Start the server:
```bash
uvicorn server.api:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal, start the client:
```bash
python client/client.py
```

Flow in this mode:
- client sends prompt to `/chat`
- client computes local update slices
- client posts update to `/send-update`
- server buffers updates and applies averaged update when threshold is reached

## API reference

## `GET /`

Health check response:
```json
{
  "message": "Server is running"
}
```

## `POST /chat`

Request:
```json
{
  "prompt": "Hello"
}
```

Response:
```json
{
  "input": "Hello",
  "response": "Generated text..."
}
```

## `POST /send-update`

Request shape:
```json
{
  "weights": [[0.001, -0.003], [0.004, 0.002]]
}
```

Response:
```json
{
  "status": "update received"
}
```

## How training/update simulation currently works

Client side (`client/client.py`):
- tokenizes local text
- runs forward/backward pass using LM loss
- extracts a very small gradient subset:
  - first 2 values per parameter gradient
  - first 5 parameter slices total
- sends these compact slices to server

Server side (`server/api.py`):
- stores incoming updates in memory
- once update count reaches `UPDATE_THRESHOLD` (currently 2):
  - averages updates element-wise
  - applies averaged values to the first segment of the last 5 model parameters
  - clears update buffer

This is intentionally lightweight and prototype-oriented, not yet a production federated optimization pipeline.

## Privacy posture (important)

Vision:
- keep data local and share privacy-preserving updates only

Current reality:
- update sharing exists in compact form
- however, raw chat prompt text is still sent to server for inference
- no DP noise and no secure aggregation are currently implemented

Do not treat the present implementation as a complete privacy-preserving system yet.

## Changelog policy

Project history is tracked in:
- `docs/CHANGELOG.md`

The project currently follows a strict update pattern:
- add newest changes on top
- include timestamp, author, and concise explanation

## Known limitations

- in-memory update buffer only (no persistence)
- no model checkpoint/version management after updates
- auth is local SQLite-based only (no MFA, SSO, or password reset flow)
- anti-poisoning protections are heuristic and need broader adversarial validation
- automated tests exist, but auth/RBAC end-to-end coverage is still limited

## Roadmap alignment

Roadmap source:
- `docs/roadmap.sh`

Current position:
- foundational, frontend, and baseline auth/RBAC phases are complete
- security hardening, persistence, and scale validation remain

Recommended next focus:
1. Strengthen auth security (password policy, lockouts, optional MFA/SSO).
2. Add persistence and model versioning for applied updates.
3. Expand auth/RBAC and aggregation API contract tests.
4. Add auditable admin action logs and stronger observability.
5. Package deployment profiles for local/staging/production.

## Troubleshooting

If model loading fails:
- ensure internet is available for first download
- run `python model/download_model.py` manually
- verify `model/config.json` exists afterward

If server import fails:
- run from repository root
- ensure `server/__init__.py` exists
- verify dependencies are installed in active environment

If client cannot reach server:
- confirm server is running on `127.0.0.1:8000`
- check firewall/proxy settings
- verify `CHAT_URL` and `UPDATE_URL` in `client/client.py`

## Contributing notes

Suggested contribution workflow:
1. Make focused, testable changes.
2. Update docs when behavior changes.
3. Add a changelog entry at the top of `docs/CHANGELOG.md`.
4. Keep privacy implications explicit in PR descriptions.

## License

No license file is currently present in the repository.
Add a license before external distribution.
