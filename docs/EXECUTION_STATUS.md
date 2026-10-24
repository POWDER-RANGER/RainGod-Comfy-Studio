# Rain God’s Sad Boy Pipeline — Execution Status and Next Engineering Actions

**Status type:** Repository evidence snapshot  
**Canonical repository:** `POWDER-RANGER/RainGod-Comfy-Studio`  
**Canonical branch:** `main`  
**Verified baseline commit:** `67fccd24ba19448de1f4eaa59bc6d7c434ccf1b8`  
**Product:** Rain God’s Sad Boy Pipeline

This document supplements the product blueprint with a repository-state checkpoint. It is not a deployment attestation. Update it whenever a material repository or deployment fact changes.

## 1. Verified source-control baseline

GitHub reports the latest commit on `main` as:

- SHA: `67fccd24ba19448de1f4eaa59bc6d7c434ccf1b8`
- Commit: merge PR #47, “Add local project-backed generation records”
- Date: 2026-10-21 06:04 UTC
- Parents: `25f89de69dd8066e48feeab7fcf653508d701a20` and `1da421d784de97cb3e4190ed9005d9c1383df086`

The baseline includes project records, project-associated generation jobs, explicit approval metadata, and local persistence of retrieved image assets with MIME type, byte size, and SHA-256 integrity metadata.

The README correctly limits this persistence slice to local development. It explicitly states that image bytes are copied when retrieved, and that automatic capture before ComfyUI history expiry, restart recovery, authentication, per-user access control, and shared multi-instance operation are not yet provided.

Do not describe this as production cloud persistence.

## 2. Current open pull-request triage

The following open pull requests were visible during this audit:

| PR | Subject | Branch | Initial disposition |
|---|---|---|---|
| #46 | Harden generated output path and request logging | `security/path-containment` | Security-relevant; inspect diff and retest against current main before merge. GitHub reported mergeable=false and its base SHA predates #47. |
| #42 | Grouped Python dependency updates | `dependabot/pip/backend/python-minor-patch-9201674760` | Review compatibility and full CI against current main; do not merge solely from the PR description. |
| #27 | websockets Python 3.10 compatibility | `dependabot/pip/backend/websockets-17.2` | Review whether superseded by #42 or other dependency work; avoid duplicate dependency changes. |

The repository also has historical or active branches for project-backed jobs, explicit generation deduplication, backend lifecycle handling, CI cleanup, security path containment, and documentation. Branch existence alone is not proof that work is unique, current, or safe to merge.

Before merging any branch:
1. Compare its head with current `main`.
2. Inspect the full diff and commit ancestry.
3. Determine whether the change is already present under another commit.
4. Rebase or recreate the work on current `main` if needed.
5. Run the applicable CI checks and regression tests.
6. Merge only when the change is non-duplicative and verified.

Do not force-push or delete branches as part of routine cleanup without a specific, verified reason.

## 3. CI and verification interpretation

The repository README and product blueprint contain historical test counts and CI snapshots. These must not be treated as current results without checking the run associated with the current commit.

For each release candidate, record:
- exact commit SHA;
- workflow run URL and conclusion;
- Python test matrix results;
- lint and type-check results;
- Docker build result;
- security scan results;
- any skipped, blocked, or unavailable checks.

A green test suite using mocked ComfyUI responses proves software behavior under those test conditions. It does not prove that a real ComfyUI runtime, model, custom node, GPU, or remote provider can generate an image.

## 4. Deployment status: not established

This repository inspection did not establish that the latest `main` commit is deployed to a live production or staging environment.

No root-level `render.yaml` or `render.yml` was found. A Dockerfile exists, but a Docker build is not a deployment. The absence of a checked-in Render Blueprint does not prove that no Render service exists; services may have been configured manually or through another deployment mechanism.

Before changing deployment configuration, inspect the actual hosting account and identify:
- service names and service IDs;
- repository and branch connected to each service;
- configured build and start commands;
- current deployed commit SHA;
- latest deploy status and logs;
- environment-variable names (never expose secret values);
- database connection target and migration state;
- persistent disk or object-storage configuration;
- public URL, health endpoint and access restrictions.

Do not trigger a public deployment until the service identity, target environment, data persistence, authentication posture, and rollback path are understood. The current SQLite and local filesystem project store must not be exposed as a public multi-user datastore.

### Render account inspection

The connected Render workspace was inspected read-only. It returned four web services, all belonging to CIVINTELLIGENCE / CIVWATCH repositories; none is connected to the Rain God studio repository. The only listed PostgreSQL instance is `civintelligence-db`, and no Key Value instances were listed. Therefore, no existing Rain God Render service or Rain God production deployment was found in this connected workspace.

This is not proof that no deployment exists on another hosting account or provider. It does establish that the inspected Render workspace has no Rain God service to update or move to a new commit. Do not repurpose a CIVINTELLIGENCE service or database for Rain God.

### CI failure found during this audit

The initial CI run for the execution-status PR failed only in the Python 3.10 test job before test collection. Coverage 7.17.0 attempted to import the standard-library `tomllib`, which is unavailable in Python 3.10. Docker, lint/type checks, and Python 3.11 tests passed in that run. The development requirements now pin Coverage 7.6.1; the follow-up CI run must verify this correction before merge.

The path-containment and log-sanitization fix from stale PR #46 has also been reapplied against current `main` in a separate focused PR (#49), with a regression test for the sibling-prefix traversal case. That PR must pass CI before merge.

## 5. Required next engineering sequence

### A. Close the source-control audit
- Review PR #46's security diff against current `main`, preserving the path-component containment fix and prompt-ID log sanitization if still correct.
- Review PR #42's dependency changes against the current lock/requirements manifests and supported Python versions.
- Determine whether PR #27 is superseded; close only after confirming its useful change is included elsewhere.
- Compare the remaining non-Dependabot branches against current `main` and classify each as unique, merged-equivalent, obsolete, or blocked.
- Reconcile stale documentation and test counts.

### B. Establish a deployable, safe staging baseline
- Inspect the actual Render account configuration before making changes.
- Choose an isolated staging service, not an existing production service by assumption.
- Add deployment-as-code only after confirming the real service topology and required secrets.
- Add authenticated access before any internet-accessible staging exposure.
- Keep ComfyUI's control port private.
- Use managed PostgreSQL and private object storage for shared deployment.
- Do not treat local SQLite or ephemeral container storage as durable cloud infrastructure.

### C. Prove the first real image-generation vertical slice
- Verify the actual ComfyUI endpoint and runtime version.
- Inventory installed checkpoints, LoRAs, custom nodes, and workflow requirements.
- Select one known-compatible model and minimal workflow.
- Submit a fresh real generation request from the studio.
- Track the upstream prompt/job to a terminal state.
- Retrieve the actual image bytes.
- Persist the image and provenance in project storage.
- Restart the relevant services and verify the asset remains retrievable.
- Record the exact evidence, limitations, and costs.

### D. Upgrade persistence and job reliability
- Introduce a storage abstraction so local SQLite is explicitly a development adapter.
- Design managed PostgreSQL schema and migrations for projects, jobs, assets, approvals, and provenance.
- Introduce private object storage for binary assets.
- Use durable job states, idempotency, retry limits, cancellation semantics, and recovery of interrupted jobs.
- Capture outputs independently of ComfyUI history retention.
- Add authorization before multi-user or public deployment.

## 6. Non-negotiable acceptance rules

- No mock or simulated generation may be described as real output.
- No deployment may be called successful without a deployment record and live health verification.
- No database integration may be called connected without a real connection and tested read/write.
- No secret values may be committed or printed in logs.
- No production service, database, storage bucket, or deployment may be deleted or replaced as part of cleanup without explicit identification and a verified backup/rollback plan.
- Preserve Rain's creative control: automated production must remain within explicit project, provider, approval, and spending boundaries.
- Keep this repository as the single active studio codebase; treat other studio repositories as historical sources unless a concrete dependency requires otherwise.

## 7. Immediate next task

Complete the current-main branch and pull-request audit, then inspect the actual Render deployment configuration. Do not jump directly to production deployment. The next product proof is a genuine ComfyUI image generation persisted to a project, not another mock endpoint or UI-only milestone.
