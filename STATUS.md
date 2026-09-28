# STATUS

**Label:** `canonical`  
**Role:** Shared runtime library — bounded execution, retries, guardrails, evaluation, model routing, event envelope.

Production modules:
- `model_router.py` — provider-neutral task_class routing
- `event_envelope.py` — canonical event builder
- `patterns.py` / `engineering.py` / `metacognition.py` — harness primitives

Authoritative contracts: [sahiixx-production-hardening](https://github.com/sahiixx/sahiixx-production-hardening)
