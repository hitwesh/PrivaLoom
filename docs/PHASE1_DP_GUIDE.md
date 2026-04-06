# Phase 1: Formal Differential Privacy - Implementation Guide

## Overview

Phase 1 of the Privacy & Security Layer adds formal (ε, δ)-differential privacy to PrivaLoom using the Opacus library with RDP (Rényi Differential Privacy) accounting.

## What Was Implemented

### 1. Privacy and Security Module (`privacy_security/`)

#### `privacy_security/dp_engine.py`
Core differential privacy implementation:
- **DPConfig**: Configuration dataclass for DP parameters
- **PrivacyAccountant**: RDP-based privacy accounting using Opacus
- **DPGradientClipper**: Per-sample gradient clipping with L2 norm
- **DPNoiseGenerator**: Calibrated Gaussian/Laplace noise addition

#### `privacy_security/privacy_tracker.py`
Persistent privacy budget tracking:
- **PrivacyTracker**: Tracks cumulative (ε, δ) across rounds
- Persistent state in `~/.privaloom/privacy_state.json`
- Thread-safe state management
- Privacy history for audit trails

### 2. Client Integration (`client/client.py`)

Enhanced with formal DP:
- Privacy budget checking before each update
- Formal gradient clipping using `DPGradientClipper`
- Calibrated noise addition using `DPNoiseGenerator`
- Privacy accounting with `PrivacyAccountant`
- Persistent privacy tracking via `PrivacyTracker`
- Configurable gradient slicing

### 3. Testing Infrastructure

Comprehensive pytest suite:
- 45 passing tests covering all DP components
- Mock models for fast testing
- Thread-safety tests
- Integration tests
- Privacy correctness verification

## Configuration

### New Environment Variables

```bash
# Formal DP parameters
export DP_ENABLED=true                    # Enable differential privacy (default: true)
export DP_EPSILON=1.0                     # Target privacy budget (default: 1.0)
export DP_DELTA=1e-5                      # Failure probability (default: 1e-5)
export DP_MAX_GRAD_NORM=1.0               # Gradient clipping threshold (default: 1.0)

# Gradient transmission configuration
export DP_GRADIENT_SLICE_SIZE=2           # Elements per parameter (default: 2)
export DP_MAX_PARAMS=5                    # Max parameters to send (default: 5)

# Legacy (deprecated, use formal DP above)
export DP_NOISE_STDDEV=0.001              # Manual noise standard deviation
```

### Configuration Examples

**High Privacy (ε=0.1)**:
```bash
export DP_EPSILON=0.1
export DP_DELTA=1e-6
export DP_MAX_GRAD_NORM=0.5
```

**Moderate Privacy (ε=1.0, default)**:
```bash
export DP_EPSILON=1.0
export DP_DELTA=1e-5
export DP_MAX_GRAD_NORM=1.0
```

**More Gradient Information**:
```bash
export DP_GRADIENT_SLICE_SIZE=50  # Send 50 elements per parameter
export DP_MAX_PARAMS=10           # Send 10 parameters instead of 5
```

## Usage

### Running the Client with Formal DP

```bash
# Start server (in one terminal)
cd D:\Samik\PrivaLoom
python -m uvicorn server.api:app --reload

# Start client with formal DP (in another terminal)
export DP_EPSILON=1.0
export DP_DELTA=1e-5
python client/client.py
```

The client will:
1. Initialize DP components on startup
2. Check privacy budget before each update
3. Apply formal gradient clipping and calibrated noise
4. Track cumulative privacy loss
5. Stop sending updates when budget exhausted

### Checking Privacy Budget

The client logs privacy status every 10 updates:

```
{"message": "Privacy budget status", "cumulative_epsilon": 0.85, "cumulative_delta": 1e-5, "remaining_epsilon": 0.15, "updates_sent": 10}
```

When budget is exhausted:

```
Privacy budget exhausted. No more updates will be sent.
```

### Privacy State Files

Privacy state is persisted to disk:
- **Location**: `~/.privaloom/privacy_state.json`
- **Contents**: Cumulative (ε, δ), round history, timestamps
- **Persistence**: Survives client restarts

To reset privacy budget (for testing):
```python
from privacy_security.privacy_tracker import get_privacy_tracker
tracker = get_privacy_tracker()
tracker.reset_budget()
```

## Testing

### Run All Tests

```bash
cd D:\Samik\PrivaLoom
pytest tests/ -v
```

### Run Specific Test Categories

```bash
# DP engine tests
pytest tests/test_privacy_dp.py -v

# Privacy tracker tests
pytest tests/test_privacy_tracker.py -v

# Client integration tests
pytest tests/test_client_dp.py -v
```

### Test Coverage

```bash
pytest tests/ --cov=privacy --cov-report=html
```

## Privacy Guarantees

### Formal (ε, δ)-Differential Privacy

The system provides formal DP guarantees using RDP accounting:

- **ε (epsilon)**: Privacy loss bound. Lower is more private.
- **δ (delta)**: Probability of privacy violation. Typically set to < 1/dataset_size.

**Interpretation**:
- ε = 0.1: Very strong privacy, significant utility loss
- ε = 1.0: Strong privacy, moderate utility (default)
- ε = 10.0: Weaker privacy, better utility

### Privacy Composition

Privacy loss accumulates across updates:
- Basic composition: ε_total ≈ n * ε_per_update
- RDP accounting provides tighter bounds (what we use)

### Budget Enforcement

The client automatically stops sending updates when:
```
cumulative_epsilon >= DP_EPSILON
```

## Architecture

### Data Flow

```
Client Training
    ↓
Compute Gradients
    ↓
Clip Gradients (L2 norm ≤ max_grad_norm)
    ↓
Add Calibrated Noise (σ = noise_multiplier * sensitivity)
    ↓
Extract Gradient Slices (configurable)
    ↓
Record Privacy Loss (RDP accounting)
    ↓
Check Budget (stop if exhausted)
    ↓
Send Update to Server
```

### Privacy Accounting

```
PrivacyAccountant (in-memory, per-session)
    ↓ records each step
RDP Accountant (Opacus)
    ↓ computes (ε, δ)
PrivacyTracker (persistent, cross-session)
    ↓ saves to disk
~/.privaloom/privacy_state.json
```

## Troubleshooting

### Issue: "Privacy budget is too low"

**Error**: `ValueError: The privacy budget is too low.`

**Cause**: The target ε is unachievable with given parameters.

**Solution**:
```bash
# Option 1: Increase epsilon
export DP_EPSILON=1.0  # or higher

# Option 2: Increase delta
export DP_DELTA=1e-4  # less strict

# Option 3: Reduce expected updates
# (noise_multiplier calculated based on expected steps)
```

### Issue: Client stops sending updates

**Symptom**: "Privacy budget exhausted" message.

**Cause**: Cumulative privacy loss exceeded DP_EPSILON.

**Solution**:
```bash
# Option 1: Increase budget
export DP_EPSILON=5.0

# Option 2: Reset budget (testing only)
python -c "from privacy_security.privacy_tracker import get_privacy_tracker; get_privacy_tracker().reset_budget()"

# Option 3: Restart client with fresh budget
# (only if ethically justified - privacy is a one-way guarantee)
```

### Issue: Updates are very noisy

**Symptom**: Model converges slowly or not at all.

**Cause**: Noise multiplier is too high for the privacy budget.

**Solution**:
```bash
# Option 1: Increase epsilon (less privacy, less noise)
export DP_EPSILON=10.0

# Option 2: Increase gradient slice size (more information)
export DP_GRADIENT_SLICE_SIZE=50
export DP_MAX_PARAMS=10

# Option 3: Increase clipping threshold (but affects privacy)
export DP_MAX_GRAD_NORM=2.0
```

## Next Steps: Phase 2

Phase 2 will add:
- **Byzantine-robust aggregation** (Krum, Trimmed Mean, Median, Bulyan)
- **Outlier detection** for malicious updates
- **Client reputation system**
- **Adversarial testing**

Estimated timeline: 2-3 weeks

## References

- [Opacus Documentation](https://opacus.ai/)
- [Differential Privacy Book](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)
- [RDP Accounting Paper](https://arxiv.org/abs/1702.07476)
- [PrivaLoom Architecture](../architecture.md)

## Support

For issues or questions:
- Check CHANGELOG.md for recent changes
- Review test cases in tests/test_privacy_*.py
- Consult the implementation plan in plans/
