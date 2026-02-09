"""
Model de Projecte (versio web).
"""
from dataclasses import dataclass, field

from models.tasca import Tasca

ESTAT_COMPLETADA = "completada"


@dataclass
class Projecte:
    nom_carpeta: str
    plantilla: str = "projecte_complet"
    tasques: list[Tasca] = field(default_factory=list)
    arxivat: bool = False
    prioritari: bool = False

    @property
    def codi(self) -> str:
        parts = self.nom_carpeta.split("_", 1)
        return parts[0] if parts else ""

    @property
    def descripcio(self) -> str:
        parts = self.nom_carpeta.split("_", 1)
        return parts[1] if len(parts) > 1 else self.nom_carpeta

    @property
    def total_tasques(self) -> int:
        return len(self.tasques)

    @property
    def tasques_completades(self) -> int:
        return len([t for t in self.tasques if t.estat == ESTAT_COMPLETADA])

    @property
    def percentatge(self) -> float:
        total = self.total_tasques
        if total == 0:
            return 0.0
        return (self.tasques_completades / total) * 100

    def to_dict(self) -> dict:
        d = {
            "plantilla": self.plantilla,
            "arxivat": self.arxivat,
            "tasques": [t.to_dict() for t in self.tasques],
        }
        if self.prioritari:
            d["prioritari"] = True
        return d

    @classmethod
    def from_dict(cls, nom_carpeta: str, data: dict) -> "Projecte":
        tasques = [Tasca.from_dict(t) for t in data.get("tasques", [])]
        return cls(
            nom_carpeta=nom_carpeta,
            plantilla=data.get("plantilla", "projecte_complet"),
            tasques=tasques,
            arxivat=data.get("arxivat", False),
            prioritari=data.get("prioritari", False),
        )
