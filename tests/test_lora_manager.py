"""Tests for backend/lora_manager.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.lora_manager import LoRAManager, LoRANotFoundError, _stem_to_slug
from backend.rain_backend_config import LoRAConfig, LORA_MAPPINGS


# ---------------------------------------------------------------------------
# _stem_to_slug (module-level helper)
# ---------------------------------------------------------------------------

class TestStemToSlug:
    def test_lowercase_passthrough(self) -> None:
        assert _stem_to_slug("synthwave_v2") == "synthwave_v2"

    def test_uppercase_lowercased(self) -> None:
        assert _stem_to_slug("SynthWave") == "synthwave"

    def test_spaces_replaced_with_underscores(self) -> None:
        assert _stem_to_slug("my lora file") == "my_lora_file"

    def test_special_chars_removed(self) -> None:
        assert _stem_to_slug("My LoRA File (v3)") == "my_lora_file_v3"

    def test_leading_trailing_underscores_stripped(self) -> None:
        result = _stem_to_slug("---test---")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_numbers_preserved(self) -> None:
        assert "2" in _stem_to_slug("lora_v2")


# ---------------------------------------------------------------------------
# LoRAManager construction — seeded from static config
# ---------------------------------------------------------------------------

class TestLoRAManagerInit:
    def test_registry_seeded_from_config(self) -> None:
        mgr = LoRAManager()
        for key in LORA_MAPPINGS:
            assert key in mgr, f"Config key {key!r} missing from registry"

    def test_len_reflects_config(self) -> None:
        mgr = LoRAManager()
        assert len(mgr) >= len(LORA_MAPPINGS)

    def test_contains_operator(self) -> None:
        mgr = LoRAManager()
        assert "synthwave" in mgr

    def test_repr_contains_class_name(self) -> None:
        mgr = LoRAManager()
        assert "LoRAManager" in repr(mgr)


# ---------------------------------------------------------------------------
# LoRAManager.scan
# ---------------------------------------------------------------------------

class TestLoRAManagerScan:
    def test_scan_returns_sorted_list(self, tmp_lora_dir: Path) -> None:
        mgr = LoRAManager(lora_dir=tmp_lora_dir)
        names = mgr.scan()
        assert names == sorted(names)

    def test_scan_discovers_safetensors_files(self, tmp_lora_dir: Path) -> None:
        mgr = LoRAManager(lora_dir=tmp_lora_dir)
        names = mgr.scan()
        # tmp_lora_dir has "synthwave_v2.safetensors" and "custom_style_v1.safetensors"
        # synthwave_v2.safetensors is already registered via LORA_MAPPINGS (under "synthwave")
        # custom_style_v1 is a new file — it should be discovered
        assert "custom_style_v1" in names

    def test_scan_includes_config_entries(self, tmp_lora_dir: Path) -> None:
        mgr = LoRAManager(lora_dir=tmp_lora_dir)
        names = mgr.scan()
        for key in LORA_MAPPINGS:
            assert key in names

    def test_scan_nonexistent_dir_returns_config_entries(self, tmp_path: Path) -> None:
        mgr = LoRAManager(lora_dir=tmp_path / "nonexistent")
        names = mgr.scan()
        # Config entries still visible
        for key in LORA_MAPPINGS:
            assert key in names

    def test_scan_discovers_new_files(self, tmp_lora_dir: Path) -> None:
        mgr = LoRAManager(lora_dir=tmp_lora_dir)
        mgr.scan()
        (tmp_lora_dir / "brand_new_lora.safetensors").write_bytes(b"\x00")
        names = mgr.scan()
        assert "brand_new_lora" in names


# ---------------------------------------------------------------------------
# LoRAManager.get / load
# ---------------------------------------------------------------------------

class TestLoRAManagerGetLoad:
    def test_get_known_entry_returns_config(self) -> None:
        mgr = LoRAManager()
        cfg = mgr.get("synthwave")
        assert cfg is not None
        assert isinstance(cfg, LoRAConfig)

    def test_get_unknown_entry_returns_none(self) -> None:
        mgr = LoRAManager()
        assert mgr.get("zzz_does_not_exist_xyz") is None

    def test_load_known_entry_returns_config(self) -> None:
        mgr = LoRAManager()
        cfg = mgr.load("synthwave")
        assert isinstance(cfg, LoRAConfig)

    def test_load_unknown_raises_lora_not_found_error(self) -> None:
        mgr = LoRAManager()
        with pytest.raises(LoRANotFoundError):
            mgr.load("zzz_totally_unknown")


# ---------------------------------------------------------------------------
# LoRAManager.available
# ---------------------------------------------------------------------------

class TestLoRAManagerAvailable:
    def test_available_returns_sorted_list(self) -> None:
        mgr = LoRAManager()
        names = mgr.available()
        assert names == sorted(names)

    def test_available_includes_all_config_keys(self) -> None:
        mgr = LoRAManager()
        names = set(mgr.available())
        for key in LORA_MAPPINGS:
            assert key in names


# ---------------------------------------------------------------------------
# LoRAManager.build_loader_node
# ---------------------------------------------------------------------------

class TestLoRAManagerBuildLoaderNode:
    def test_returns_dict_with_required_keys(self) -> None:
        mgr = LoRAManager()
        node = mgr.build_loader_node("synthwave")
        assert "lora_name" in node
        assert "strength_model" in node
        assert "strength_clip" in node

    def test_raises_for_unknown_lora(self) -> None:
        mgr = LoRAManager()
        with pytest.raises(LoRANotFoundError):
            mgr.build_loader_node("totally_unknown_xyz")

    def test_strength_overrides_applied(self) -> None:
        mgr = LoRAManager()
        node = mgr.build_loader_node("synthwave", strength_model=0.3, strength_clip=0.4)
        assert node["strength_model"] == 0.3
        assert node["strength_clip"] == 0.4

    def test_default_strength_from_registry(self) -> None:
        mgr = LoRAManager()
        cfg = mgr.get("synthwave")
        node = mgr.build_loader_node("synthwave")
        assert node["strength_model"] == cfg.strength_model
        assert node["strength_clip"] == cfg.strength_clip


# ---------------------------------------------------------------------------
# LoRAManager.build_lora_chain
# ---------------------------------------------------------------------------

class TestBuildLoraChain:
    def _base_graph(self) -> dict:
        """Minimal valid workflow graph."""
        return {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "test.safetensors"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "pos", "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "neg", "clip": ["1", 1]}},
            "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0]}},
        }

    def test_injects_single_lora(self) -> None:
        mgr = LoRAManager()
        graph = mgr.build_lora_chain(self._base_graph(), [("synthwave", 0.8, 0.8)])
        assert "100" in graph
        assert graph["100"]["class_type"] == "LoraLoader"

    def test_ksampler_rewired_to_lora_output(self) -> None:
        mgr = LoRAManager()
        graph = mgr.build_lora_chain(self._base_graph(), [("synthwave", 0.8, 0.8)])
        assert graph["5"]["inputs"]["model"] == ["100", 0]

    def test_clip_encoders_rewired(self) -> None:
        mgr = LoRAManager()
        graph = mgr.build_lora_chain(self._base_graph(), [("synthwave", 0.8, 0.8)])
        assert graph["2"]["inputs"]["clip"] == ["100", 1]
        assert graph["3"]["inputs"]["clip"] == ["100", 1]

    def test_two_loras_chain(self) -> None:
        mgr = LoRAManager()
        graph = mgr.build_lora_chain(
            self._base_graph(),
            [("synthwave", 0.8, 0.8), ("cyberpunk", 0.6, 0.6)],
        )
        assert "100" in graph
        assert "101" in graph
        # KSampler should use the last LoRA output
        assert graph["5"]["inputs"]["model"] == ["101", 0]

    def test_empty_loras_raises_value_error(self) -> None:
        mgr = LoRAManager()
        with pytest.raises(ValueError, match="empty"):
            mgr.build_lora_chain(self._base_graph(), [])

    def test_base_graph_not_mutated(self) -> None:
        mgr = LoRAManager()
        base = self._base_graph()
        original_model = base["5"]["inputs"]["model"]
        mgr.build_lora_chain(base, [("synthwave", 0.8, 0.8)])
        assert base["5"]["inputs"]["model"] == original_model


# ---------------------------------------------------------------------------
# LoRAManager.merge_configs
# ---------------------------------------------------------------------------

class TestMergeConfigs:
    def _cfg(self, filename: str, sm: float = 0.8, sc: float = 0.8) -> LoRAConfig:
        return LoRAConfig(filename=filename, strength_model=sm, strength_clip=sc)

    def test_average_blend(self) -> None:
        a = self._cfg("a.safetensors", sm=0.6, sc=0.4)
        b = self._cfg("b.safetensors", sm=1.0, sc=0.8)
        merged = LoRAManager.merge_configs(a, b, blend_mode="average")
        assert merged.strength_model == pytest.approx(0.8)
        assert merged.strength_clip == pytest.approx(0.6)

    def test_max_blend(self) -> None:
        a = self._cfg("a.safetensors", sm=0.3, sc=0.3)
        b = self._cfg("b.safetensors", sm=0.9, sc=0.7)
        merged = LoRAManager.merge_configs(a, b, blend_mode="max")
        assert merged.strength_model == 0.9
        assert merged.strength_clip == 0.7

    def test_sum_clamp_blend(self) -> None:
        a = self._cfg("a.safetensors", sm=0.7, sc=0.7)
        b = self._cfg("b.safetensors", sm=0.7, sc=0.7)
        merged = LoRAManager.merge_configs(a, b, blend_mode="sum_clamp")
        assert merged.strength_model == 1.0
        assert merged.strength_clip == 1.0

    def test_raises_with_single_config(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            LoRAManager.merge_configs(self._cfg("a.safetensors"))

    def test_raises_with_unknown_blend_mode(self) -> None:
        a, b = self._cfg("a.safetensors"), self._cfg("b.safetensors")
        with pytest.raises(ValueError, match="blend_mode"):
            LoRAManager.merge_configs(a, b, blend_mode="unknown_mode")

    def test_combined_filename_contains_inputs(self) -> None:
        a = self._cfg("alpha.safetensors")
        b = self._cfg("beta.safetensors")
        merged = LoRAManager.merge_configs(a, b)
        assert "alpha.safetensors" in merged.filename
        assert "beta.safetensors" in merged.filename

    def test_three_configs_average(self) -> None:
        configs = [self._cfg(f"{i}.sf", sm=float(i) / 10) for i in range(1, 4)]
        merged = LoRAManager.merge_configs(*configs, blend_mode="average")
        expected = (0.1 + 0.2 + 0.3) / 3
        assert merged.strength_model == pytest.approx(expected, abs=1e-4)


# ---------------------------------------------------------------------------
# LoRAManager.as_dict / summary
# ---------------------------------------------------------------------------

class TestLoRAManagerSummary:
    def test_as_dict_contains_all_keys(self) -> None:
        mgr = LoRAManager()
        d = mgr.as_dict()
        for key in LORA_MAPPINGS:
            assert key in d

    def test_as_dict_entry_has_required_fields(self) -> None:
        mgr = LoRAManager()
        for name, entry in mgr.as_dict().items():
            assert "filename" in entry, f"Missing 'filename' in {name}"
            assert "strength_model" in entry
            assert "strength_clip" in entry

    def test_summary_has_required_keys(self) -> None:
        mgr = LoRAManager()
        s = mgr.summary()
        assert "lora_dir" in s
        assert "total" in s
        assert "loras" in s

    def test_summary_total_matches_len(self) -> None:
        mgr = LoRAManager()
        assert mgr.summary()["total"] == len(mgr)
