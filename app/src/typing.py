from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional


class UF(str, Enum):
    AC="AC"; AL="AL"; AP="AP"; AM="AM"; BA="BA"; CE="CE"; DF="DF"; ES="ES"; GO="GO"; MA="MA"
    MT="MT"; MS="MS"; MG="MG"; PA="PA"; PB="PB"; PR="PR"; PE="PE"; PI="PI"; RJ="RJ"; RN="RN"
    RS="RS"; RO="RO"; RR="RR"; SC="SC"; SP="SP"; SE="SE"; TO="TO"


def _digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _normalize_phone(phone: Optional[str]) -> str:
    return _digits(phone or "")


def _normalize_cnpj(cnpj: Optional[str]) -> str:
    return _digits(cnpj or "")


def _is_valid_cnpj(cnpj: str) -> bool:
    n = _digits(cnpj)
    if len(n) != 14 or len(set(n)) == 1:
        return False
    def dv(nums: str) -> int:
        pesos = [6,5,4,3,2,9,8,7,6,5,4,3,2]
        s = sum(int(d)*pesos[i+1-len(nums)] for i,d in enumerate(nums, start=0))
        r = s % 11
        return 0 if r < 2 else 11 - r
    d1 = dv(n[:12])
    d2 = dv(n[:12] + str(d1))
    return n[-2:] == f"{d1}{d2}"


@dataclass
class LeadData:
    # --- Campos principais (agora realmente opcionais onde faz sentido) ---
    phone: str = ""
    name: str = ""
    email: str = ""
    address: str = ""
    cnpj: str = ""
    corporate_reason: str = ""          # razão social
    uf: Optional[UF] = None             # pode ser None
    cidade: str = ""
    quantidade_usuarios: Optional[int] = None  # pode ser None
    sistema_atual: str = "Não informado"
    desafios: str = "Não  informado"
    videos_enviados: str = ""

    # --- Controles opcionais ---
    validate_cnpj: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self):
        # Normalizações “se houver valor”
        self.phone = _normalize_phone(self.phone)
        self.cnpj = _normalize_cnpj(self.cnpj)

        if self.quantidade_usuarios is not None:
            # Só normaliza se veio valor; senão, deixa None
            try:
                self.quantidade_usuarios = max(1, int(self.quantidade_usuarios))
            except (TypeError, ValueError):
                self.quantidade_usuarios = None

        self.sistema_atual = (self.sistema_atual or "").strip()
        self.name = (self.name or "").strip()
        self.email = (self.email or "").strip()
        self.address = (self.address or "").strip()
        self.corporate_reason = (self.corporate_reason or "").strip()
        self.cidade = (self.cidade or "").strip()

        # UF pode ser str, Enum ou None; converte str válida para Enum
        if isinstance(self.uf, str):
            try:
                self.uf = UF(self.uf)
            except ValueError:
                self.uf = None  # inválido -> None (sem quebrar o fluxo)

        # Validação de CNPJ só se habilitada e houver valor
        if self.validate_cnpj and self.cnpj and not _is_valid_cnpj(self.cnpj):
            raise ValueError("CNPJ inválido")

    # ---------- API fluente (mutável porém previsível) ----------
    def update(self, **patch: Any) -> "LeadData":
        """
        Atualiza campos granularmente. Aceita None (inclusive para limpar dados).
        Aplica saneamento apenas quando houver valor.
        """
        for k, v in patch.items():
            if not hasattr(self, k):
                raise AttributeError(f"Campo desconhecido: {k}")

            if k == "phone":
                v = _normalize_phone(v)
            elif k == "cnpj":
                v = _normalize_cnpj(v)
                if self.validate_cnpj and v and not _is_valid_cnpj(v):
                    raise ValueError("CNPJ inválido")
            elif k == "quantidade_usuarios":
                if v is None:
                    pass  # permite None
                else:
                    try:
                        v = max(1, int(v))
                    except (TypeError, ValueError):
                        v = None
            elif k == "sistema_atual":
                v = (v or "").strip() if v is not None else None
            elif k in {"name", "email", "address", "corporate_reason", "cidade"}:
                v = (v or "").strip() if v is not None else None
            elif k == "uf":
                if isinstance(v, str):
                    try:
                        v = UF(v)
                    except ValueError:
                        v = None  # inválido -> None
                # se já vier Enum ou None, aceita direto

            setattr(self, k, v)
        return self

    # Conveniências
    def set_phone(self, phone: Optional[str]) -> "LeadData":
        return self.update(phone=phone)

    def set_cnpj(self, cnpj: Optional[str]) -> "LeadData":
        return self.update(cnpj=cnpj)

    # ---------- Serialização segura ----------
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Converte Enum -> string; preserva None ou string se já estiver assim
        uf = self.uf
        d["uf"] = uf.value if isinstance(uf, UF) else uf  # pode ser "SP" ou None
        d.pop("validate_cnpj", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeadData":
        return cls(**data)  # __post_init__ faz a coerção/limpeza
