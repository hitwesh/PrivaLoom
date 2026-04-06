# Changelog

- All notable changes to this project are documented here.
- Add your name and date along with timestamp
- Do not skip changelog updataion at any cost.
- Thoroughly explain about your features and changes committed.
- Always add changes on the top of previous changes, do not break this.

## Split Architecture page, refined access copy, and workspace-aware CTA
- Timestamp: 2026-04-06, 10:25pm
- Author: Hitesh
- Description: Added a dedicated Architecture route/view, removed sensitive implementation wording from access copy, changed account placeholder to username, and changed header CTA text/state so it no longer shows Try Workspace while already inside an active workspace.

## Replaced workspace login button with account badge and made update log action-driven
- Timestamp: 2026-04-06, 10:11pm
- Author: Hitesh 
- Description: Updated the header actions so the Log in button is no longer shown inside the active workspace; it now displays the current account name as a session badge. Reworked Update Log from hardcoded development history to a meaningful live activity feed powered by actual user actions in the console (document uploads and prompt submissions), including session boot entries when a workspace opens. This keeps the UI useful now while remaining easy to connect to backend events later.

## Added OpenAI-inspired navigation, explanatory project body, and structured footer
- Timestamp: 2026-04-06, 09:55pm
- Author: Hitesh
- Description: Reworked the global site shell to a cleaner OpenAI-inspired layout by introducing a minimal sticky header with professional navigation/actions, expanded the landing page with a detailed architecture-driven middle body section that explains PrivaLoom (privacy model, learning flow, implementation reality, and roadmap direction), and replaced the compact footer with a full multi-column information footer for platform, privacy, architecture, and resources. Updated responsive behavior for desktop/tablet/mobile to keep hierarchy, readability, and spacing consistent across all breakpoints.

## Added premium landing flow with dummy multi-client access gateway
- Timestamp: 2026-04-06, 08:19pm
- Author: Hitesh
- Description: Added a high-end monochrome landing page and an intermediate dummy account/client access page (account name + password + client workspace selection) that routes into the existing training dashboard, enabling a realistic multi-client entry flow without auth/RBAC/database dependencies.

## Redesigned frontend with premium monochrome chat workspace
- Timestamp: 2026-04-06, 08:00pm
- Author: Hitesh
- Description: Rebuilt the React interface into a professional black/space-gray/white layout with a premium ChatGPT-style chat surface, elevated sidebar cards for dataset intake/status/logs, refined typography, responsive spacing, and subtle motion while preserving existing local workflow behavior.

## Fixed frontend Vite entry path and missing dashboard components
- Timestamp: 2026-04-06, 07:44pm
- Author: Hitesh
- Description: Fixed frontend startup by updating index module path from /src/main.jsx to /main.jsx and restored missing React dashboard components (UploadPanel, TrainingStatus, UpdateLog, ChatPanel, PrivacyBadge) required by App.jsx so Vite resolves imports correctly.

## Added React Frontend UI for SLM Training & Testing Dashboard
- Timestamp: 2026-04-06, 01:56pm
- Author: Riya
- Description: Built a React dashboard with dataset upload, local parsing, training integration, update tracking, and chat-based model testing with privacy-         preserving update flow.

## Added Differential Privacy (DP) Client Gradient Noise/Clipping

- Timestamp: 2026-04-05, 12:51am
- Author: Samik
- Description: Implemented client-side gradient clipping and Gaussian noise addition before slicing and sending update payloads to the server, with env-var configuration for noise scale and clipping norm.

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
