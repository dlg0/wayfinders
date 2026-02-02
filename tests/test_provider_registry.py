from __future__ import annotations

from pathlib import Path

import pytest

from wayfinders_cli.gen.config import ConfigError, load_config
from wayfinders_cli.gen.providers.placeholder import PlaceholderProvider
from wayfinders_cli.gen.registry import ProviderRegistry
from wayfinders_cli.gen.types import ImageGenRequest


class TestLoadConfig:
    def test_load_valid_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        config_file.write_text("""
default_provider = "placeholder"

[providers.placeholder]
""")
        config = load_config(config_file)
        assert config.default_provider == "placeholder"
        assert config.providers.placeholder is not None

    def test_missing_config_produces_helpful_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)

        error_msg = str(exc_info.value)
        assert "not found" in error_msg.lower()
        assert "wf init" in error_msg or "wf.toml.example" in error_msg

    def test_invalid_toml_produces_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        config_file.write_text("this is not valid [toml")

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)
        assert "parse" in str(exc_info.value).lower() or "toml" in str(exc_info.value).lower()

    def test_invalid_default_provider_produces_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        config_file.write_text("""
default_provider = "nonexistent"

[providers.placeholder]
""")
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file)

        error_msg = str(exc_info.value)
        assert "nonexistent" in error_msg
        assert "placeholder" in error_msg


class TestProviderRegistry:
    def test_get_placeholder_provider(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        config_file.write_text("""
default_provider = "placeholder"

[providers.placeholder]
""")
        registry = ProviderRegistry.from_config_file(config_file)
        provider = registry.get_provider("placeholder")

        assert isinstance(provider, PlaceholderProvider)
        assert provider.provider_id == "placeholder"

    def test_get_default_provider(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        config_file.write_text("""
default_provider = "placeholder"

[providers.placeholder]
""")
        registry = ProviderRegistry.from_config_file(config_file)
        provider = registry.get_default_provider()

        assert isinstance(provider, PlaceholderProvider)

    def test_unknown_provider_produces_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        config_file.write_text("""
default_provider = "placeholder"

[providers.placeholder]
""")
        registry = ProviderRegistry.from_config_file(config_file)

        with pytest.raises(ConfigError) as exc_info:
            registry.get_provider("nonexistent")

        error_msg = str(exc_info.value)
        assert "nonexistent" in error_msg
        assert "placeholder" in error_msg

    def test_provider_is_cached(self, tmp_path: Path) -> None:
        config_file = tmp_path / "wf.toml"
        config_file.write_text("""
default_provider = "placeholder"

[providers.placeholder]
""")
        registry = ProviderRegistry.from_config_file(config_file)

        provider1 = registry.get_provider("placeholder")
        provider2 = registry.get_provider("placeholder")

        assert provider1 is provider2


class TestPlaceholderProvider:
    def test_generates_image_successfully(self, tmp_path: Path) -> None:
        provider = PlaceholderProvider()

        out_path = tmp_path / "test_output.png"
        request = ImageGenRequest(
            asset_type="background",
            asset_id="bg_forest",
            template_name="forest_bg",
            resolved_prompt="A dense forest background",
            params={},
            width=1920,
            height=1080,
            out_path=out_path,
            provider_id="placeholder",
        )

        generated = provider.generate(request)

        assert generated.out_path == out_path
        assert out_path.exists()
        assert generated.provider_id == "placeholder"
        assert generated.model_id is None
        assert len(generated.output_hash) == 16
        assert len(generated.cache_key) == 16

    def test_generates_cutout_with_transparency(self, tmp_path: Path) -> None:
        provider = PlaceholderProvider()

        out_path = tmp_path / "cutout.png"
        request = ImageGenRequest(
            asset_type="cutout",
            asset_id="char_scout",
            template_name="character_pose",
            resolved_prompt="Scout character standing",
            params={},
            width=1024,
            height=1024,
            out_path=out_path,
            provider_id="placeholder",
        )

        provider.generate(request)

        assert out_path.exists()
        from PIL import Image

        img = Image.open(out_path)
        assert img.mode == "RGBA"
        corner_pixel = img.getpixel((0, 0))
        assert corner_pixel[3] == 0

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        provider = PlaceholderProvider()

        out_path = tmp_path / "nested" / "dirs" / "output.png"
        request = ImageGenRequest(
            asset_type="prop",
            asset_id="prop_map",
            template_name="prop_template",
            resolved_prompt="A treasure map",
            params={},
            width=512,
            height=512,
            out_path=out_path,
            provider_id="placeholder",
        )

        provider.generate(request)

        assert out_path.exists()
        assert out_path.parent.exists()
