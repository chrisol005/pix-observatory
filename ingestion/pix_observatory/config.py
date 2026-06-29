"""Project-wide configuration, loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root if present (idempotent).
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Read-only settings bundle.

    Why a frozen dataclass instead of pydantic-settings: keeps the dependency
    footprint small for this first iteration. Migrate to pydantic-settings
    once we add more fields with non-trivial validation.
    """

    bacen_api_base: str = field(
        default_factory=lambda: os.getenv(
            "BACEN_API_BASE",
            "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata",
        )
    )

    # Local data lake roots (S3 paths replace these later).
    data_root: Path = field(default_factory=lambda: Path(os.getenv("PIXO_DATA_ROOT", "./data")))

    @property
    def raw_root(self) -> Path:
        return self.data_root / "raw"

    @property
    def processed_root(self) -> Path:
        return self.data_root / "processed"


settings = Settings()
