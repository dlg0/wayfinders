from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class PlaceholderProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenAIProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key_env: str = "OPENAI_API_KEY"
    model: str = "gpt-image-1"


class ProvidersConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    placeholder: Optional[PlaceholderProviderConfig] = None
    openai: Optional[OpenAIProviderConfig] = None


class WFConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_provider: str = "placeholder"
    providers: ProvidersConfig = ProvidersConfig()

    @field_validator("default_provider")
    @classmethod
    def validate_default_provider(cls, v: str) -> str:
        if not v:
            raise ValueError("default_provider cannot be empty")
        return v

    @model_validator(mode="after")
    def check_default_provider_exists(self) -> "WFConfig":
        provider_names = set()
        if self.providers.placeholder is not None:
            provider_names.add("placeholder")
        if self.providers.openai is not None:
            provider_names.add("openai")
        for name in self.providers.model_extra or {}:
            provider_names.add(name)
        if not provider_names:
            provider_names.add("placeholder")
        if self.default_provider not in provider_names:
            raise ValueError(
                f"default_provider '{self.default_provider}' is not configured. "
                f"Available providers: {sorted(provider_names)}"
            )
        return self


class ConfigError(Exception):
    def __init__(self, message: str, path: Optional[Path] = None, line: Optional[int] = None):
        self.path = path
        self.line = line
        if path:
            loc = f"{path}"
            if line:
                loc += f":{line}"
            message = f"{loc}: {message}"
        super().__init__(message)


def load_config(config_path: Path) -> WFConfig:
    if not config_path.exists():
        raise ConfigError(
            f"Config file not found: {config_path}\n"
            "Run 'wf init' or copy wf.toml.example to wf.toml",
            path=config_path,
        )

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    try:
        text = config_path.read_text()
        data = tomllib.loads(text)
    except Exception as e:
        raise ConfigError(f"Failed to parse TOML: {e}", path=config_path) from e

    try:
        return WFConfig.model_validate(data)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}", path=config_path) from e


def find_config(start_dir: Optional[Path] = None) -> Path:
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()
    while current != current.parent:
        candidate = current / "wf.toml"
        if candidate.exists():
            return candidate
        current = current.parent

    return start_dir / "wf.toml"
