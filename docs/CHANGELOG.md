# Changelog

- All notable changes to this project are documented here.
- Add your name and date along with timestamp
- Do not skip changelog updataion at any cost.
- Thoroughly explain about your features and changes committed.
- Always add changes on the top of previous changes, do not break this.

## Fixed one-time dataset training flag

- Timestamp: 2026-04-04, 07:23pm
- Author: Hitesh
- Description: Moved the dataset training flag outside the loop so dataset training runs only once.

## Added one-time dataset training flow

- Timestamp: 2026-04-04, 05:23pm
- Author: Hitesh
- Description: Added data.txt placeholder and client-side one-time dataset training with aggregated update slices before incremental updates.

## Applied selective last-layer updates

- Timestamp: 2026-04-04, 01:31pm
- Author: Hitesh
- Description: Aggregation now applies averaged update slices only to the last model layers instead of the entire parameter set.

## Applied averaged gradient aggregation

- Timestamp: 2026-04-04, 01:07pm
- Author: Hitesh
- Description: Replaced simulated noise updates with averaged gradient slice aggregation applied to model parameters.

## Added server-side update aggregation buffer

- Timestamp: 2026-04-04, 12:50pm
- Author: Hitesh
- Description: Server now buffers incoming updates, applies a simulated aggregation update when a threshold is reached, then clears the buffer.

## Switched updates to gradients

- Timestamp: 2026-04-03, 10:35pm
- Author: Hitesh
- Description: Client now computes and sends small gradient slices from a local forward/backward pass instead of static weights.

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

## Added Differential Privacy (DP) Client Gradient Noise/Clipping

- Timestamp: 2026-04-05, 12:51am
- Author: Samik
- Description Implemented client-side gradient clipping and Gaussian noise addition before slicing and sending update payloads to the server, with env-var configuration for noise scale and clipping norm.