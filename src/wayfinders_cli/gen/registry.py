from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import ConfigError, WFConfig, find_config, load_config
from .provider import ImageProvider
from .providers.placeholder import PlaceholderProvider


class ProviderRegistry:
    def __init__(self, config: WFConfig):
        self._config = config
        self._providers: dict[str, ImageProvider] = {}

    @classmethod
    def from_config_file(cls, config_path: Optional[Path] = None) -> "ProviderRegistry":
        if config_path is None:
            config_path = find_config()
        config = load_config(config_path)
        return cls(config)

    @property
    def config(self) -> WFConfig:
        return self._config

    def get_provider(self, name: str) -> ImageProvider:
        if name in self._providers:
            return self._providers[name]

        provider = self._instantiate_provider(name)
        self._providers[name] = provider
        return provider

    def get_default_provider(self) -> ImageProvider:
        return self.get_provider(self._config.default_provider)

    def _instantiate_provider(self, name: str) -> ImageProvider:
        if name == "placeholder":
            return PlaceholderProvider(self._config.providers.placeholder)

        if name == "openai":
            if self._config.providers.openai is None:
                raise ConfigError(
                    "Provider 'openai' is not configured in wf.toml. "
                    "Add [providers.openai] section."
                )
            raise NotImplementedError("OpenAI provider not yet implemented")

        available = self._get_available_providers()
        raise ConfigError(
            f"Unknown provider: '{name}'. Available providers: {sorted(available)}"
        )

    def _get_available_providers(self) -> set[str]:
        providers = {"placeholder"}
        if self._config.providers.openai is not None:
            providers.add("openai")
        return providers
