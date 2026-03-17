# workflows/

ComfyUI API-format workflow templates for the RAINGOD AI Music Kit.

## Available Templates

| File | Preset | Resolution | Steps | Notes |
|------|--------|-----------|-------|-------|
| `txt2img_draft.json` | fast / euler normal | 512×512 | 20 | Preview quality — quickest generation |
| `txt2img_fast.json` | fast / euler normal | 512×512 | 20 | Alias for draft — same settings |
| `txt2img_quality.json` | quality / dpmpp_2m karras | 1024×1024 | 40 | Default production preset |
| `txt2img_final.json` | ultra / dpmpp_sde karras | 2048×2048 | 80 | Maximum quality for final masters |
| `txt2img_ultra.json` | ultra / dpmpp_sde karras | 2048×2048 | 80 | Alias for final — same settings |
| `img2img_refine.json` | quality / dpmpp_2m karras | source size | 30 | img2img at 75% denoise |
| `txt2img_synthwave_lora.json` | quality / dpmpp_2m karras | 1024×1024 | 40 | Synthwave LoRA @ 0.80 strength |
| `txt2img_lora_synthwave.json` | quality / dpmpp_2m karras | 1024×1024 | 40 | Synthwave LoRA @ 0.85 strength |
| `animatediff.json` | AnimateDiff v2 / euler_ancestral karras | 512×512×16fr | 20 | 16-frame MP4 via VHS_VideoCombine |

## Placeholder Values

Each template uses these placeholder strings — patch before use:

| Placeholder | Node | Field | Description |
|------------|------|-------|-------------|
| `POSITIVE_PROMPT_PLACEHOLDER` | `"2"` | `text` | Positive generation prompt |
| `NEGATIVE_PROMPT_PLACEHOLDER` | `"3"` | `text` | Negative / exclusion prompt |
| `POSITIVE_PROMPT` | `"2"` | `text` | Alternate positive placeholder (fast/ultra) |
| `NEGATIVE_PROMPT` | `"3"` | `text` | Alternate negative placeholder (fast/ultra) |
| `SOURCE_IMAGE_PLACEHOLDER` | `"4"` | `image` | Source image filename (img2img only) |

## Using Templates with WorkflowBuilder

```python
from backend.workflow_builder import WorkflowBuilder

builder = WorkflowBuilder()

# Load and patch
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

## Or via the Dispatcher (recommended)

```python
from backend.dispatcher import RainGodDispatcher, TaskType

dispatcher = RainGodDispatcher()
result = await dispatcher.dispatch(TaskType.IMAGE_GENERATE, {
    "prompt":   "glowing neon city at night",
    "preset":   "quality",
    "width":    1024,
    "height":   1024,
})
# Routes to Comfy Cloud → Replicate → local ComfyUI in order
print(result.data["image_url"])
```

## Adding New Templates

1. Design your workflow in the ComfyUI web UI
2. Use **Save (API format)** to export the workflow JSON
3. Drop the `.json` file here with a descriptive name
4. Replace variable prompt/seed values with placeholder strings above
5. Test with `WorkflowBuilder().from_template("<stem>")`

## AnimateDiff Requirements

`animatediff.json` requires these ComfyUI custom nodes:

```bash
# Install via ComfyUI Manager or manually:
comfy node install comfyui-animatediff-evolved
comfy node install comfyui-videohelpersuite
```

Motion model: `mm_sd_v15_v2.ckpt`
Download from: https://huggingface.co/guoyww/animatediff
Place in: `ComfyUI/models/animatediff_models/`
