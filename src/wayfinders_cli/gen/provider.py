from __future__ import annotations

from abc import ABC, abstractmethod
from .types import ImageGenRequest, GeneratedAsset


class ImageProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @abstractmethod
    def generate(self, req: ImageGenRequest) -> GeneratedAsset:
        """Generate an asset and write it to req.out_path."""
        raise NotImplementedError
