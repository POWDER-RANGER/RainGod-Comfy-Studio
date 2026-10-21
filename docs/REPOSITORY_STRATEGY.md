# Single-Master Repository Strategy

## Product identity

**Product name:** Rain God’s Sad Boy Pipeline  
**Canonical studio repository:** this repository (currently hosted at `POWDER-RANGER/RainGod-Comfy-Studio`)  
**Artist reference:** [Rain God Music on YouTube](https://youtube.com/@raingodmusic)

The repository slug is historical and has not yet been changed in GitHub repository settings. Product branding and documentation are being consolidated here first.

## One active studio

This repository is the sole active home for:
- the Rain-facing studio and creative-project workflow;
- the backend orchestration and ComfyUI integration;
- artist-controlled style/reference profiles and project metadata;
- provider adapters that are proven useful and actually tested;
- workflows, tests, setup instructions, provenance records, and release evidence.

Do not develop competing studio versions in parallel. New functionality belongs here unless there is a demonstrated infrastructure reason to separate a component.

## Keep the engine separate

`POWDER-RANGER/ComfyUI` is the ComfyUI engine/fork, not another Rain God studio. Keep the upstream/fork relationship, setup instructions, supported node requirements, and version/license notes documented. Do not vendor the entire engine into this repository or duplicate its source without a concrete reason.

## Existing Rain God repositories

The other studio/integration repositories are historical reference material, not separate active products:
- `POWDER-RANGER/raingod-studio-v4`: inspect for unique, tested capabilities only; port useful pieces with provenance and tests.
- `POWDER-RANGER/RAINGOD-ComfyUI-Integration`: compare against this repository, identify unique verified code, then stop parallel feature development.
- `POWDER-RANGER/RainGod-Comfy-Studio`: current canonical repository content while its GitHub slug remains historical.

Do not delete or archive repositories before unique content, open issues, releases, GitHub Pages, deployment references, and user-facing links have been inventoried. Repository deletion is not required to achieve one active codebase. Once migration and link checks are complete, mark old variants archived or legacy using repository settings.

## Consolidation rules

1. Prefer the smallest useful, maintainable implementation over broad rewrites.
2. Before copying a component, check whether a maintained library or existing code already solves the same problem.
3. No duplicate modules or repositories without an explicit reason and ownership.
4. Do not claim a provider works because an adapter exists; test the actual capability.
5. Do not present mocked generation as a real output.
6. Preserve Rain's originals and project decisions; generated artifacts and analysis belong in separate, traceable records.
7. Explain external provider, credential, data-transfer, license, retention, and cost implications before enabling that provider.
8. Require CI, focused regression tests, and a real end-to-end smoke test for release claims.

## Current release priority

The next concrete milestone is the smallest verifiable vertical slice:
1. launch the backend;
2. verify the configured ComfyUI instance and its required models/nodes;
3. submit a fresh generation request;
4. track the returned prompt to completion;
5. retrieve a real output through the API and show it in the studio;
6. preserve settings and provenance;
7. report failures honestly.

Only after that path is working should advanced artist-reference analysis, music/audio integrations, and video synchronization be expanded.
