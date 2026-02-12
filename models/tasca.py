"""
Model de Tasca (versio web — sense dependencia de config desktop).
"""
from dataclasses import dataclass, field
from datetime import datetime

ESTAT_PENDENT = "pendent"


@dataclass
class Tasca:
    nom: str
    estat: str = ESTAT_PENDENT
    assignat: str = ""
    observacions: str = ""
    document: str = ""
    documents_historial: list[str] = field(default_factory=list)
    data_modificacio: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        d = {
            "nom": self.nom,
            "estat": self.estat,
            "assignat": self.assignat,
            "observacions": self.observacions,
            "document": self.document,
            "data_modificacio": self.data_modificacio,
        }
        if self.documents_historial:
            d["documents_historial"] = self.documents_historial
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Tasca":
        return cls(
            nom=data.get("nom", ""),
            estat=data.get("estat", ESTAT_PENDENT),
            assignat=data.get("assignat", ""),
            observacions=data.get("observacions", ""),
            document=data.get("document", ""),
            documents_historial=data.get("documents_historial", []),
            data_modificacio=data.get(
                "data_modificacio",
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

    def actualitzar_estat(self, nou_estat: str):
        self.estat = nou_estat
        self.data_modificacio = datetime.now().isoformat(timespec="seconds")

    def assignar_a(self, usuari: str):
        self.assignat = usuari
        self.data_modificacio = datetime.now().isoformat(timespec="seconds")
