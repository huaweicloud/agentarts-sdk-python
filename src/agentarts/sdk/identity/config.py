import json
import logging
from pathlib import Path
from typing import Optional, Any, Dict

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class Config(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    workload_identity_name: Optional[str] = None
    user_id: Optional[str] = None
    path: Path = Field(default=Path(".agent_identity.json"), repr=False, exclude=True)

    @classmethod
    def load(cls, path: str = ".agent_identity.json") -> "Config":
        config_path = Path(path)
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data: Dict[str, Any] = json.load(f) or {}
                    return cls(**data, path=config_path)
            except Exception:
                logger.warning("Could not load existing config from %s", path)
        return cls(path=config_path)

    def save(self) -> None:
        try:
            data: Dict[str, Any] = self.model_dump()
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            logger.warning("Could not write config to %s", self.path)
