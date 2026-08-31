from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LugarExtraido:
    id: str
    nome: str
    categoria: str | None = None
    endereco: str | None = None
    telefone: str | None = None
    site: str | None = None
    nota: float | None = None
    avaliacoes: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    url_referencia: str = ""
    score: int | None = None

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResultadoExtracao:
    lugares: list[LugarExtraido] = field(default_factory=list)
    duracao_segundos: float = 0.0
    urls_processadas: list[str] = field(default_factory=list)
    ignorados_webrp: int = 0
    ignorados_continuacao: int = 0
    alertas_duplicidade: int = 0


@dataclass
class EventoProcessamento:
    url: str
    status: str
    lugar: LugarExtraido | None = None
    motivo: str = ""


class CaptchaDetectado(Exception):
    def __init__(self, motivo: str = "Captcha ou verificação de segurança do Google") -> None:
        self.motivo = motivo
        super().__init__(motivo)


class ExtracaoCancelada(Exception):
    def __init__(self, resultado: ResultadoExtracao) -> None:
        self.resultado = resultado
        super().__init__("Extração cancelada pelo usuário")
