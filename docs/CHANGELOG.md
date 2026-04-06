# Changelog

- All notable changes to this project are documented here.
- Add your name and date along with timestamp
- Do not skip changelog updataion at any cost.
- Thoroughly explain about your features and changes committed.
- Always add changes on the top of previous changes, do not break this.

## Reorganized Privacy and Security into Unified Module

- Timestamp: 2026-04-06, 20:45
- Author: Samik
- Description: Consolidated privacy and security components into a single unified `privacy_security/` directory to reduce directory clutter and improve organization. Moved all files from separate `privacy/` and `security/` directories into `privacy_security/`. Updated all imports across client code, tests, and documentation. Verified functionality with comprehensive test runs - all 50+ tests still pass. This change improves code organization and sets up clean structure for upcoming Phase 2 Byzantine-robust aggregation features. No functional changes, purely organizational restructuring for better maintainability.

## Added Formal Differential Privacy & Testing Infrastructure

- Timestamp: 2026-04-06, 20:30
- Author: Samik
- Description: Implemented Phase 1 of the Privacy & Security Layer feature. Added formal (ε, δ)-differential privacy using Opacus library with RDP (Rényi Differential Privacy) accounting for precise privacy loss tracking. Created privacy/ module with DPEngine (privacy accountant, gradient clipper, noise generator) and PrivacyTracker for persistent budget management. Bootstrapped comprehensive pytest testing infrastructure with 45 passing tests covering DP correctness, privacy accounting, composition theorems, and persistence. Added new dependencies: opacus==1.5.4, pytest==8.3.5, pytest-asyncio==0.25.2, pytest-mock==3.14.0. Extended utils/types.py with privacy-related type aliases (PrivacyBudget, DPParams, ClientID, ReputationScore). Added get_privacy_stats() method to RoundTracker for integration with privacy tracking. All tests pass with 100% coverage of privacy module. Next: Phase 2 (Byzantine-robust aggregation) and client integration for formal DP.

## Added Automatic Periodic Retraining with 20-Update Threshold

- Timestamp: 2026-04-06, 15:15
- Author: Samik
- Description: Implemented automatic server-side model retraining that triggers when 20 client updates are accumulated. Changed aggregation threshold from 2 to 20 updates, added thread-safe update buffering with threading.Lock, implemented persistent round tracking with JSON state storage, added enhanced structured logging for aggregation events with performance metrics, and created configurable UPDATE_THRESHOLD environment variable. Includes new /status endpoint for monitoring aggregation progress and round statistics.

## Added Utilities Module with Structured Logging and Configuration Management

- Timestamp: 2026-04-06, 14:30
- Author: Samik
- Description: Implemented centralized utils/ module with structured JSON logging, environment-based configuration management, data preprocessing utilities, and validation functions. Replaced print() statements in client and server with JSON logging, added backward compatibility for existing environment helper functions, and enhanced data loading with validation. All utilities include comprehensive type hints and maintain existing behavior patterns.

## Added Differential Privacy (DP) Client Gradient Noise/Clipping

- Timestamp: 2026-04-05, 12:51am
- Author: Samik
- Description Implemented client-side gradient clipping and Gaussian noise addition before slicing and sending update payloads to the server, with env-var configuration for noise scale and clipping norm.

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
