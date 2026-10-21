# Artist Reference Workflow

## Canonical reference

- **Artist:** Rain God
- **Artist channel:** [Rain God Music on YouTube](https://youtube.com/@raingodmusic)
- **Purpose:** Help Rain create, revise, compare, and organize his own artistic projects without surrendering creative control.

The channel is a discovery pointer, not proof that every upload is available for every technical use. The studio must not infer a complete artistic profile from the channel name or a handful of items. Build the profile from tracks, videos, lyrics, images, and notes that Rain explicitly selects or provides.

## Reference catalog

Each reference item should retain:

- Source URL and title as supplied or confirmed by Rain.
- Asset type (audio, video, lyrics, cover art, or notes).
- Import date and local project-relative asset path, when imported.
- Rights/permission note and any usage restrictions Rain records.
- A human-authored note describing why the reference matters.
- Analysis results with the model/tool and version identified, when available.
- Rain's edits, approval state, and profile version.

Missing metadata must remain unknown instead of being guessed. Keep original files unchanged; store analysis and generated derivatives separately.

## Artistic profile

The profile should be editable and versioned, not a hidden prompt. Candidate fields:

- Vocal/flow and melodic characteristics Rain chooses to document.
- Tempo, rhythm, instrumentation, production texture, and mood.
- Lyrical themes, vocabulary, narrative point of view, and exclusions.
- Visual palette, recurring imagery, composition preferences, and cover-art constraints.
- Per-project deviations from the broader profile.

These fields are hypotheses until Rain reviews and approves them. Avoid claims of exact voice or identity reproduction; consistency must be evaluated against selected references.

## Data and control boundaries

1. No automatic bulk download, third-party upload, or model-training use merely because an item is publicly viewable.
2. Prefer local analysis and local generation when the available hardware and models support them.
3. Before an external provider receives an asset or prompt, show the provider, the data being sent, and any known cost/retention implications.
4. Rain can reject, edit, pin, replace, or remove a reference and can approve or reject every generated candidate.
5. Keep provenance: source references, prompt/workflow version, model/checkpoint, seed, settings, output path, and generation status where available.
6. Never present placeholder analysis, mocked generation, or an unverified feature as a live result.

## First practical workflow

1. Rain selects a specific channel item or supplies the source asset.
2. The studio records its source and permission notes.
3. An available local or explicitly approved analysis tool extracts candidate observations.
4. The studio presents those observations for Rain to edit and approve.
5. Approved observations become a versioned project/style profile.
6. Image generation is tested first through a real ComfyUI queue-and-output cycle; music/audio generation is enabled only after its provider and end-to-end behavior are independently verified.

## Current verification status

This document records the intended workflow. It does not claim that YouTube ingestion, audio analysis, voice analysis, model training, music generation, or an end-to-end creative session has been implemented or tested.
