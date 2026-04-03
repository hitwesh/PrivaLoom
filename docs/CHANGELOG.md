# Changelog

- All notable changes to this project are documented here.
- Add your name and date along with timestamp
- Do not skip changelog updataion at any cost.
- Thoroughly explain about your features and changes committed.
- Always add changes on the top of previous changes, do not break this.

## Fixed client import path

- Timestamp: 2026-04-03, 10:25pm
- Author: Hitesh
- Description: Added repo-root path injection so client can import model when run as a script.

## Switched client to model-based updates

- Timestamp: 2026-04-03, 10:20pm
- Author: Hitesh
- Description: Replaced random update payloads with small slices of model parameters for update simulation.

## Added update flow simulation

- Timestamp: 2026-04-03, 10:00pm
- Author: Hitesh
- Description: Added client-side dummy update posts and a /send-update endpoint to receive simulated weights.

## Added client CLI and tuned sampling

- Timestamp: 2026-04-03, 09:52pm
- Author: Hitesh
- Description: Added client/client.py for calling the /chat API and adjusted generation sampling parameters for more natural outputs.

## Fixed server package discovery

- Timestamp: 2026-04-03, 09:40pm
- Author: Hitesh
- Description: Added server/__init__.py so uvicorn can import server.api.

## Added FastAPI chat API

- Timestamp: 2026-04-03, 09:30pm
- Author: Hitesh
- Description: Added server/api.py with root health route and /chat endpoint that returns model responses.

## Added requirements.txt

- Timestamp: 2026-04-03, 09:10pm
- Author: Hitesh
- Description: Added requirements.txt inside root directory.

## Added HF fallback for local model load

- Timestamp: 2026-04-03, 08:45pm
- Author: Hitesh
- Description: Fall back to downloading the model from Hugging Face when local files are missing, then save to ./model for later runs.

## Fixed tokenizer init without extras

- Timestamp: 2026-04-03, 08:40pm
- Author: Hitesh
- Description: Use slow tokenizer fallback to avoid requiring extra tokenizer backends when loading the local model.

## Ignored local model artifacts

- Timestamp: 2026-04-03, 08:38pm
- Author: Hitesh
- Description: Added gitignore rules to keep Hugging Face-downloaded model files out of commits while preserving model source files.

## Added local model bootstrap and structure

- Timestamp: 2026-04-03, 08:35pm
- Author: Hitesh
- Description: Added base project folders, local model download script, model loader, and a simple CLI entrypoint for testing text generation.

## Added roadmap.sh

- Timestamp: 2026-04-03, 08:00pm
- Author: Hitesh
- Description: Added roadmap.sh with the rapid build roadmap.

## Added PROJECT_BIBLE.md

- Timestamp: 2026-04-03, 03:00pm
- Author: Hitesh
- Description: Added PROJECT_BIBLE.md with the core project description.