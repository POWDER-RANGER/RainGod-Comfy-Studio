# workflows/

ComfyUI API-format workflow templates for the RAINGOD AI Music Kit.

## Available Templates

| File | Preset | Resolution | Steps | Notes |
|------|--------|-----------|-------|-------|
| `txt2img_draft.json` | fast / euler | 512×512 | 20 | Preview quality — quickest generation |
| `txt2img_quality.json` | quality / dpmpp_2m karras | 1024×1024 | 40 | Default production preset |
| `txt2img_final.json` | ultra / dpmpp_sde karras | 2048×2048 | 80 | Maximum quality for final masters |
| `img2img_refine.json` | quality / dpmpp_2m karras | (source size) | 30 | img2img at 75% denoise — refine existing images |
| `txt2img_synthwave_lora.json` | quality / dpmpp_2m karras | 1024×1024 | 40 | Synthwave LoRA at 0.8 strength |

## Placeholder Values

Each template contains placeholders that must be patched before use:

| Placeholder | Node | Field | Description |
|------------|------|-------|-------------|
| `POSITIVE_PROMPT_PLACEHOLDER` | `"2"` | `text` | Positive generation prompt |
| `NEGATIVE_PROMPT_PLACEHOLDER` | `"3"` | `text` | Negative / exclusion prompt |
| `SOURCE_IMAGE_PLACEHOLDER` | `"4"` | `image` | Source image filename (img2img only) |

## Using Templates with WorkflowBuilder

```python
from backend.workflow_builder import WorkflowBuilder

builder = WorkflowBuilder()

# Load a template and patch the prompts
workflow = builder.from_template(
    "txt2img_quality",
    patches={
        "2.text": "glowing neon city at night, synthwave aesthetic",
        "3.text": "blurry, low quality, watermark",
        "5.seed": 42,
    },
)

# Submit to ComfyUI
from backend.comfyui_client import ComfyUIClient
client = ComfyUIClient()
prompt_id = client.queue_prompt(workflow)
```

## Adding New Templates

1. Design your workflow in the ComfyUI web UI
2. Use **Save (API format)** to export the workflow JSON
3. Drop the file here with a descriptive name: `<type>_<style>.json`
4. Replace variable values with the placeholder strings above
5. Test with `WorkflowBuilder().from_template("<stem>")`
