# -*- coding: utf-8 -*-
"""
tipos.py — TypedDicts do motor de apuração, para segurança de tipos estática.

B-1: o campo `Bem.resultado` é um `dict` livre, o que permite acesso a chaves
inexistentes sem erro em tempo de execução (ex.: `r.get("ir_espolio")` retorna
None silencioso quando a chave não existe). Esta abordagem é arriscada em
software de auditoria fiscal, onde um None silencioso pode ser interpretado
como "isento" em vez de "dado ausente".

Solução adotada: TypedDicts (PEP 589) que:
  • Documentam O CONTRATO de cada resultado de regime;
  • São verificáveis por mypy/pyright sem alterar o runtime;
  • Não quebram nenhum código existente (dict é compatível com TypedDict).

Uso:
    from orgaudi_espolio.tipos import ResultadoTransmissaoHistorico
    r: ResultadoTransmissaoHistorico = b.resultado  # mypy valida

Para ativar a verificação estática:
    mypy src/ --strict

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

from typing import Optional
from typing_extensions import TypedDict, Required, NotRequired

from .dominio import StatusApuracao
from .fatores_reducao import ResultadoFR


# ────────────────────────────────────────────────────────────────────────
# Base comum a todos os regimes
# ────────────────────────────────────────────────────────────────────────

class ResultadoBase(TypedDict, total=False):
    """Campos presentes em TODOS os resultados do motor."""
    status:          Required[StatusApuracao]
    regime:          NotRequired[str]
    nota:            NotRequired[str]
    alerta_reducao:  NotRequired[Optional[str]]
    ir_espolio:      NotRequired[Optional[float]]
    ir_meeiro:       NotRequired[Optional[float]]


# ────────────────────────────────────────────────────────────────────────
# Resultado — PENDENTE (faltam dados ou regime indeterminado)
# ────────────────────────────────────────────────────────────────────────

class ResultadoPendente(TypedDict):
    """Motor não concluiu a apuração — campos de IR são None."""
    status:         StatusApuracao      # sempre StatusApuracao.PENDENTE
    ir_espolio:     None
    ir_meeiro:      None
    alerta_reducao: Optional[str]


# ────────────────────────────────────────────────────────────────────────
# Resultado — TRANSMISSAO_HERDEIRO §2º (valor histórico)
# ────────────────────────────────────────────────────────────────────────

class ResultadoTransmissaoHistorico(TypedDict):
    """Art. 23 §2º Lei 9.532/97 — sem IR no espólio; ganho diferido ao herdeiro."""
    status:              StatusApuracao      # OK
    regime:              str
    ganho_diferido:      float              # ganho que vai ao herdeiro (paga só na venda)
    ir_espolio:          float              # sempre 0.0
    ir_meeiro:           float              # sempre 0.0
    base_custo_herdeiro: float              # custo histórico proporcional da herança
    base_custo_meeiro:   float              # custo histórico proporcional da meação
    alerta_reducao:      None               # C-4: nulo neste regime
    nota:                str


# ────────────────────────────────────────────────────────────────────────
# Resultado — TRANSMISSAO_HERDEIRO §1º (valor de mercado)
# ────────────────────────────────────────────────────────────────────────

class ResultadoTransmissaoMercado(TypedDict):
    """Art. 23 §1º Lei 9.532/97 — IR no espólio; herdeiro recebe base atualizada."""
    status:              StatusApuracao      # OK
    regime:              str
    ganho_apurado:       float
    ir_espolio:          float              # IR sobre ganho da herança
    ir_meeiro:           float              # sempre 0.0 (meação não é transmissão)
    base_custo_herdeiro: float              # valor de partilha proporcional (base futura)
    base_custo_meeiro:   float              # custo histórico proporcional da meação
    alerta_reducao:      None               # C-4: nulo neste regime
    nota:                str


# ────────────────────────────────────────────────────────────────────────
# Resultado — VENDA_PELO_ESPOLIO
# ────────────────────────────────────────────────────────────────────────

class ResultadoVenda(TypedDict):
    """Venda a terceiro pelo espólio — IR progressivo sobre ganho bruto."""
    status:                  StatusApuracao   # OK
    regime:                  str
    ganho_bruto:             float
    base_tributavel:         float            # fração da herança após FR
    base_tributavel_meeiro:  float            # fração da meação após FR
    fatores_reducao:         ResultadoFR      # FR1/FR2 + Lei 7.713/88
    ir_espolio:              float
    ir_meeiro:               float            # a recolher no CPF do meeiro
    base_custo_herdeiro:     None             # não aplicável em venda
    alerta_reducao:          Optional[str]    # presente quando eh_imovel=True
    nota:                    str


# ────────────────────────────────────────────────────────────────────────
# Resultado — CESSAO_DIREITOS_HEREDITARIOS
# ────────────────────────────────────────────────────────────────────────

class HerdeiroRateio(TypedDict):
    """Rateio de ganho e IR por herdeiro cedente."""
    fracao:          float
    ganho:           float
    base_tributavel: float
    ir:              float    # C-2: calculado sobre base AGREGADA de todos os bens
    eh_meeiro:       bool


class ResultadoCessao(TypedDict):
    """Cessão de direitos — IR nas PFs dos cedentes, não no espólio."""
    status:                 StatusApuracao      # OK
    regime:                 str
    ganho_bruto:            float
    base_tributavel:        float               # fração herança
    base_tributavel_meeiro: float               # fração meação
    fatores_reducao:        ResultadoFR
    ir_espolio:             float               # sempre 0.0
    ir_meeiro:              float               # soma do IR de herdeiros meeiros
    ir_herdeiros:           dict[str, HerdeiroRateio]
    alerta_reducao:         Optional[str]
    nota:                   str


# ────────────────────────────────────────────────────────────────────────
# Resultado — FORA_DO_ESPOLIO
# ────────────────────────────────────────────────────────────────────────

class ResultadoForaEspolio(TypedDict):
    """Bem que não integra o monte — sem IR."""
    status:     StatusApuracao   # OK
    regime:     str
    ir_espolio: float            # sempre 0.0
    ir_meeiro:  float            # sempre 0.0
    nota:       str


# ────────────────────────────────────────────────────────────────────────
# União de todos os tipos possíveis de resultado
# ────────────────────────────────────────────────────────────────────────

ResultadoBem = (
    ResultadoPendente
    | ResultadoTransmissaoHistorico
    | ResultadoTransmissaoMercado
    | ResultadoVenda
    | ResultadoCessao
    | ResultadoForaEspolio
)
"""
Union de todos os TypedDicts de resultado.

Uso com narrowing:
    r: ResultadoBem = b.resultado
    if r["status"] == StatusApuracao.PENDENTE:
        # mypy sabe que r é ResultadoPendente
        assert r["ir_espolio"] is None
"""
