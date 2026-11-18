from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model: str = "gemma4:12b"
    embedding_model: str = "bge-m3"
    top_k: int = 8
    db_path: Path = Path("data/index.db")
    output_dir: Path = Path("output")
    private_dir: Path = Path("data/private")


settings = Settings()
