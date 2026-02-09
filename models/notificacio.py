"""
Model de Notificacio (versio web — identic al desktop).
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Notificacio:
    id: str
    de: str
    per_a: str
    projecte: str
    tasca: str
    accio: str
    missatge: str = ""
    data: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    llegida: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "de": self.de,
            "per_a": self.per_a,
            "projecte": self.projecte,
            "tasca": self.tasca,
            "accio": self.accio,
            "missatge": self.missatge,
            "data": self.data,
            "llegida": self.llegida,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Notificacio":
        return cls(
            id=data.get("id", ""),
            de=data.get("de", ""),
            per_a=data.get("per_a", ""),
            projecte=data.get("projecte", ""),
            tasca=data.get("tasca", ""),
            accio=data.get("accio", ""),
            missatge=data.get("missatge", ""),
            data=data.get("data", ""),
            llegida=data.get("llegida", False),
        )
