# Annotation-Only Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the cloud deployment to run annotation workflows without PyTorch, Transformers, Redis, or the active-learning worker while preserving all machine-learning features in a fully provisioned local environment.

**Architecture:** Expose a lightweight backend capability endpoint that detects optional ML packages. Guard the three active-learning start APIs and let the frontend show a clear unavailable message before creating a task. Keep the main Compose stack intact for full environments and add an annotation-only override that omits optional services and builds a slim backend image.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, Axios, Docker Compose, pytest.

---

### Task 1: Runtime capability detection

**Files:**
- Create: `backend/app/services/runtime_capabilities.py`
- Modify: `backend/app/schemas/system.py`
- Modify: `backend/app/api/v1/system.py`
- Test: `backend/tests/test_runtime_capabilities.py`

- [ ] Write tests proving missing `torch` or `transformers` makes ML unavailable.
- [ ] Run the focused test and confirm it fails because the capability service does not exist.
- [ ] Implement package detection and `GET /api/v1/system/capabilities`.
- [ ] Run the focused test and confirm it passes.

### Task 2: Guard active-learning task creation

**Files:**
- Modify: `backend/app/api/v1/active_learning.py`
- Test: `backend/tests/test_runtime_capabilities.py`

- [ ] Write tests proving training, prediction, and CoreSet creation return HTTP 503 without an ML runtime.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Add a shared FastAPI dependency to the three creation endpoints only.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Frontend unavailable message

**Files:**
- Create: `frontend/src/services/system.ts`
- Modify: `frontend/src/services/active-learning.ts`
- Modify: `frontend/src/pages/admin/index.tsx`

- [ ] Add the system capability type and request.
- [ ] Check capability before training, prediction, and CoreSet POST requests.
- [ ] Display the backend message through the existing Ant Design message handling.
- [ ] Run TypeScript type checking.

### Task 4: Optional ML dependencies and annotation-only Compose

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `deploy/docker/backend/Dockerfile`
- Modify: `deploy/compose/docker-compose.yml`
- Create: `deploy/compose/docker-compose.annotation.yml`
- Modify: `deploy/compose/docker-compose.cuda.yml`
- Modify: `deploy/compose/.env.example`

- [ ] Move ML-only libraries into the `ml` optional dependency group.
- [ ] Add an `INSTALL_ML` build argument, defaulting to full compatibility in the main stack.
- [ ] Add an annotation-only override that skips ML installation and disables Redis/worker.
- [ ] Ensure the CUDA override explicitly enables ML installation.
- [ ] Validate the merged Compose configuration.

### Task 5: Deployment documentation and verification

**Files:**
- Modify: `deploy/FIN_DEPLOYMENT_GUIDE.md`
- Modify: `deploy/README.md`

- [ ] Document the annotation-only startup command and required uploads.
- [ ] Document that Redis currently serves only the unused Celery worker configuration.
- [ ] Run focused and full backend tests.
- [ ] Run frontend type checking and production build.
- [ ] Inspect `git diff` for accidental changes.
