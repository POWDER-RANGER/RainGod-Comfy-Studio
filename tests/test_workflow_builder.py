"""Tests for backend/workflow_builder.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.rain_backend_config import LoRAConfig
from backend.workflow_builder import WorkflowBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_builder(tmp_path: Path | None = None) -> WorkflowBuilder:
    return WorkflowBuilder(
        checkpoint="test_model.safetensors",
        workflows_dir=tmp_path,
    )


# ---------------------------------------------------------------------------
# build_txt2img
# ---------------------------------------------------------------------------

class TestBuildTxt2img:
    def _build(self, **kwargs) -> dict:
        b = _make_builder()
        defaults = dict(
            positive="test prompt",
            negative="bad",
            width=512,
            height=512,
            steps=20,
            cfg=7.0,
            sampler_name="euler",
            scheduler="normal",
            seed=42,
        )
        defaults.update(kwargs)
        return b.build_txt2img(**defaults)

    def test_returns_dict(self) -> None:
        assert isinstance(self._build(), dict)

    def test_has_all_required_nodes(self) -> None:
        graph = self._build()
        for node_id in ("1", "2", "3", "4", "5", "6", "7"):
            assert node_id in graph, f"Node {node_id!r} missing from graph"

    def test_checkpoint_node_correct(self) -> None:
        graph = self._build()
        assert graph["1"]["class_type"] == "CheckpointLoaderSimple"
        assert graph["1"]["inputs"]["ckpt_name"] == "test_model.safetensors"

    def test_positive_prompt_in_node_2(self) -> None:
        graph = self._build(positive="a blue sunset")
        assert graph["2"]["inputs"]["text"] == "a blue sunset"

    def test_negative_prompt_in_node_3(self) -> None:
        graph = self._build(negative="ugly blurry")
        assert graph["3"]["inputs"]["text"] == "ugly blurry"

    def test_resolution_set_in_node_4(self) -> None:
        graph = self._build(width=1024, height=768)
        assert graph["4"]["inputs"]["width"] == 1024
        assert graph["4"]["inputs"]["height"] == 768

    def test_seed_in_ksampler(self) -> None:
        graph = self._build(seed=999)
        assert graph["5"]["inputs"]["seed"] == 999

    def test_steps_in_ksampler(self) -> None:
        graph = self._build(steps=30)
        assert graph["5"]["inputs"]["steps"] == 30

    def test_cfg_in_ksampler(self) -> None:
        graph = self._build(cfg=8.5)
        assert graph["5"]["inputs"]["cfg"] == 8.5

    def test_sampler_name_in_ksampler(self) -> None:
        graph = self._build(sampler_name="dpmpp_2m")
        assert graph["5"]["inputs"]["sampler_name"] == "dpmpp_2m"

    def test_scheduler_in_ksampler(self) -> None:
        graph = self._build(scheduler="karras")
        assert graph["5"]["inputs"]["scheduler"] == "karras"

    def test_save_image_node_present(self) -> None:
        graph = self._build(filename_prefix="myprefix")
        assert graph["7"]["class_type"] == "SaveImage"
        assert graph["7"]["inputs"]["filename_prefix"] == "myprefix"

    def test_two_calls_return_independent_dicts(self) -> None:
        b = _make_builder()
        g1 = b.build_txt2img("a", "", 512, 512, 20, 7.0, "euler", "normal", 1)
        g2 = b.build_txt2img("b", "", 512, 512, 20, 7.0, "euler", "normal", 2)
        g1["5"]["inputs"]["seed"] = 9999
        assert g2["5"]["inputs"]["seed"] == 2  # mutation of g1 doesn't affect g2

    def test_checkpoint_override(self) -> None:
        b = _make_builder()
        graph = b.build_txt2img("p", "", 512, 512, 20, 7.0, "euler", "normal", 0,
                                checkpoint="override.safetensors")
        assert graph["1"]["inputs"]["ckpt_name"] == "override.safetensors"

    def test_batch_size_default_is_one(self) -> None:
        graph = self._build()
        assert graph["4"]["inputs"]["batch_size"] == 1

    def test_batch_size_override(self) -> None:
        graph = self._build(batch_size=4)
        assert graph["4"]["inputs"]["batch_size"] == 4


# ---------------------------------------------------------------------------
# LoRA injection
# ---------------------------------------------------------------------------

class TestLoRAInjection:
    def _build_with_lora(self, **lora_kwargs) -> dict:
        b = _make_builder()
        lora = LoRAConfig(filename="test_lora.safetensors", **lora_kwargs)
        return b.build_txt2img(
            "test", "", 512, 512, 20, 7.0, "euler", "normal", 0, lora=lora
        )

    def test_lora_node_inserted(self) -> None:
        graph = self._build_with_lora()
        assert "8" in graph
        assert graph["8"]["class_type"] == "LoraLoader"

    def test_lora_filename_correct(self) -> None:
        graph = self._build_with_lora()
        assert graph["8"]["inputs"]["lora_name"] == "test_lora.safetensors"

    def test_lora_strengths_default(self) -> None:
        graph = self._build_with_lora()
        assert graph["8"]["inputs"]["strength_model"] == 0.8
        assert graph["8"]["inputs"]["strength_clip"] == 0.8

    def test_lora_strengths_custom(self) -> None:
        graph = self._build_with_lora(strength_model=0.6, strength_clip=0.5)
        assert graph["8"]["inputs"]["strength_model"] == 0.6
        assert graph["8"]["inputs"]["strength_clip"] == 0.5

    def test_ksampler_model_rewired_to_lora(self) -> None:
        graph = self._build_with_lora()
        assert graph["5"]["inputs"]["model"] == ["8", 0]

    def test_positive_clip_rewired_to_lora(self) -> None:
        graph = self._build_with_lora()
        assert graph["2"]["inputs"]["clip"] == ["8", 1]

    def test_negative_clip_rewired_to_lora(self) -> None:
        graph = self._build_with_lora()
        assert graph["3"]["inputs"]["clip"] == ["8", 1]

    def test_no_lora_node_when_none(self) -> None:
        b = _make_builder()
        graph = b.build_txt2img("p", "", 512, 512, 20, 7.0, "euler", "normal", 0, lora=None)
        assert "8" not in graph

    def test_original_graph_not_mutated(self) -> None:
        b = _make_builder()
        base = b.build_txt2img("p", "", 512, 512, 20, 7.0, "euler", "normal", 0)
        original_model_input = base["5"]["inputs"]["model"]
        lora = LoRAConfig(filename="x.safetensors")
        b._inject_lora(base, lora)
        # base should be unchanged
        assert base["5"]["inputs"]["model"] == original_model_input


# ---------------------------------------------------------------------------
# build_img2img
# ---------------------------------------------------------------------------

class TestBuildImg2img:
    def _build(self, **kwargs) -> dict:
        b = _make_builder()
        defaults = dict(
            positive="refine this",
            negative="ugly",
            image_path="input.png",
            steps=20,
            cfg=7.0,
            sampler_name="euler",
            scheduler="normal",
            seed=0,
            denoise=0.75,
        )
        defaults.update(kwargs)
        return b.build_img2img(**defaults)

    def test_has_load_image_node(self) -> None:
        graph = self._build()
        assert graph["4"]["class_type"] == "LoadImage"

    def test_has_vae_encode_node(self) -> None:
        graph = self._build()
        assert "10" in graph
        assert graph["10"]["class_type"] == "VAEEncode"

    def test_image_path_set_correctly(self) -> None:
        graph = self._build(image_path="my_source.png")
        assert graph["4"]["inputs"]["image"] == "my_source.png"

    def test_ksampler_uses_vae_encode_latent(self) -> None:
        graph = self._build()
        assert graph["5"]["inputs"]["latent_image"] == ["10", 0]

    def test_denoise_set_in_ksampler(self) -> None:
        graph = self._build(denoise=0.5)
        assert graph["5"]["inputs"]["denoise"] == 0.5


# ---------------------------------------------------------------------------
# build_upscale_pass
# ---------------------------------------------------------------------------

class TestBuildUpscalePass:
    def _base(self) -> dict:
        return _make_builder().build_txt2img(
            "p", "", 512, 512, 20, 7.0, "euler", "normal", 0
        )

    def test_adds_upscale_nodes(self) -> None:
        b = _make_builder()
        graph = b.build_upscale_pass(self._base())
        assert "20" in graph
        assert "21" in graph
        assert "22" in graph

    def test_upscale_model_loader_class(self) -> None:
        b = _make_builder()
        graph = b.build_upscale_pass(self._base())
        assert graph["20"]["class_type"] == "UpscaleModelLoader"

    def test_upscale_model_filename(self) -> None:
        b = _make_builder()
        graph = b.build_upscale_pass(self._base(), upscale_model="RealESRGAN_x4.pth")
        assert graph["20"]["inputs"]["model_name"] == "RealESRGAN_x4.pth"

    def test_base_workflow_not_mutated(self) -> None:
        b = _make_builder()
        base = self._base()
        original_keys = set(base.keys())
        b.build_upscale_pass(base)
        assert set(base.keys()) == original_keys  # no new keys added to base


# ---------------------------------------------------------------------------
# from_template
# ---------------------------------------------------------------------------

class TestFromTemplate:
    def test_loads_template(self, tmp_workflows_dir: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_workflows_dir)
        graph = b.from_template("test_workflow")
        assert isinstance(graph, dict)
        assert "1" in graph

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            b.from_template("does_not_exist")

    def test_patches_are_applied(self, tmp_workflows_dir: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_workflows_dir)
        graph = b.from_template("test_workflow", patches={"2.text": "patched prompt"})
        assert graph["2"]["inputs"]["text"] == "patched prompt"

    def test_multiple_patches(self, tmp_workflows_dir: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_workflows_dir)
        graph = b.from_template("test_workflow", patches={
            "2.text": "pos",
            "3.text": "neg",
            "5.seed": 777,
        })
        assert graph["2"]["inputs"]["text"] == "pos"
        assert graph["3"]["inputs"]["text"] == "neg"
        assert graph["5"]["inputs"]["seed"] == 777

    def test_bad_patch_key_raises_value_error(self, tmp_workflows_dir: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_workflows_dir)
        with pytest.raises(ValueError, match="node_id"):
            b.from_template("test_workflow", patches={"no_dot_key": "value"})

    def test_nonexistent_node_patch_raises_value_error(self, tmp_workflows_dir: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_workflows_dir)
        with pytest.raises(ValueError, match="non-existent node"):
            b.from_template("test_workflow", patches={"999.text": "value"})


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------

class TestListTemplates:
    def test_returns_list(self, tmp_workflows_dir: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_workflows_dir)
        result = b.list_templates()
        assert isinstance(result, list)

    def test_includes_seeded_template(self, tmp_workflows_dir: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_workflows_dir)
        templates = b.list_templates()
        assert "test_workflow" in templates

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_path)
        assert b.list_templates() == []

    def test_nonexistent_dir_returns_empty_list(self, tmp_path: Path) -> None:
        b = WorkflowBuilder(workflows_dir=tmp_path / "nonexistent")
        assert b.list_templates() == []
