#!/usr/bin/env sh

# PROJECT ROADMAP (Rapid Build)
# Phase 1: Base Model Setup
# - Pick distilgpt2
# - Load model locally using HuggingFace
# - Build a simple script: Input -> generate -> output
# - Wrap into function: generate_response(text)
# Goal: Local working AI model

# Phase 2: Structure Your Project
# Create folders:
# project/
#  ├── client/
#  ├── server/
#  ├── model/
#  ├── frontend/
#  └── utils/
# - Keep model loading inside model/
# - Keep logic clean from the start
# Goal: Organized codebase

# Phase 3: Backend API
# - Setup FastAPI server
# - Create endpoints:
#   - /chat -> returns model response
#   - /get-model -> sends model
#   - /send-update -> receives updates
# Goal: Model accessible via API

# Phase 4: Client Endpoint (Core System)
# - Build a Python client app:
#   - Take user input (text/data)
#   - Pass to local model
#   - Simulate "training signal"
# - Start simple:
#   - Generate dummy updates (random tensors or small weight changes)
# Goal: Client -> Server communication working

# Phase 5: Federated Learning (Basic)
# - Implement simple aggregation on server:
#   - Average incoming updates (FedAvg logic)
# - Update global model weights
# Goal: Multiple clients improve one model

# Phase 6: Replace Dummy Updates with Real Logic
# - Now improve:
#   - Instead of fake updates:
#     - Compute gradients from local data
#   - Send gradients to server
# Goal: Real learning happening

# Phase 7: Your Innovation (Update Mapping)
# - Add a layer that:
#   - Detects which part of model to update
# - Simple version:
#   - Only update last few layers
#   - OR weight filtering
# Goal: "Smart updates" instead of blind training

# Phase 8: Privacy Layer
# - Clip gradients (bounded sensitivity)
# - Add Gaussian noise to gradient slices (basic Differential Privacy)
# - Keep payload compact (send only partial/noised slices)
# - (Optional / later) Encrypt updates before sending
# Goal: No raw or exact gradient info leakage

# Phase 9: Frontend (Parallel or After Backend)
# - Build simple React UI:
#   - Chat interface
#   - Input box + response display
# - Connect to /chat API
# - Add:
#   - Privacy indicators
#   - Status messages
# Goal: Usable system demo

# Phase 10: Multi-Client Simulation
# - Run multiple client scripts
# - Send updates simultaneously
# Goal: Show distributed learning

# Phase 11: Testing & Demo Prep
# - Show:
#   - Model improves after updates
#   - No raw data sent
# - Log:
#   - Updates received
#   - Aggregation steps
# Goal: Strong demo + viva clarity

# Build Order (IMPORTANT PRIORITY)
# - Model works locally
# - API works
# - Client sends data
# - Server aggregates
# - THEN add privacy + innovation
