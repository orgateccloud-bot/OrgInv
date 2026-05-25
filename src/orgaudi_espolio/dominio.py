# -*- coding: utf-8 -*-
"""
dominio.py — Camada de domínio do motor de apuração de espólio.

Define O QUE existe no problema: bens, herdeiros, regimes tributários e
opções legais. Não contém cálculo nem regra de decisão — só estrutura.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
Autor técnico: Warley Veloso
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Regime(str, Enum):
    """
    Regime tributário de uma operação sucessória. Determina QUAL fórmula
    o motor aplica. A escolha entre estes regimes é decisão profissional
    baseada em fatos (data e titularidade da alienação), não do software.
    """
    TRANSMISSAO_HERDEIRO         = "Transmissão a herdeiro (partilha)"
    VENDA_PELO_ESPOLIO           = "Venda pelo espólio a terceiro"
    CESSAO_DIREITOS_HEREDITARIOS = "Cessão de direitos hereditários"
    FORA_DO_ESPOLIO              = "Fora do monte partilhável"
    INDETERMINADO                = "Indeterminado — requer classificação"


class OpcaoArt23(str, Enum):
    """
    Opção da Lei 9.532/97, Art. 23 — aplicável APENAS ao regime
    TRANSMISSAO_HERDEIRO. A opção determina, de forma vinculada, a base
    de custo com que o herdeiro recebe o bem. Não há escolha campo a campo.
    """
    VALOR_HISTORICO = "Valor histórico (§2º — sem IR; ganho diferido)"
    VALOR_MERCADO   = "Valor de mercado (§1º — IR no espólio agora)"
    NAO_APLICAVEL   = "Não aplicável a este regime"


class StatusApuracao(str, Enum):
    OK       = "Conclusivo"
    PENDENTE = "Pendente — faltam dados ou classificação"


@dataclass
class Herdeiro:
    """Um sucessor e sua fração no monte partilhável."""
    nome: str
    cpf: str
    fracao_monte: float          # ex.: 0.2506 para 25,06%
    eh_meeiro: bool = False      # cônjuge/companheiro com meação

    def __post_init__(self):
        if not (0.0 <= self.fracao_monte <= 1.0):
            raise ValueError(
                f"Fração de {self.nome} fora de [0,1]: {self.fracao_monte}")


@dataclass
class Bem:
    """
    Um imóvel ou direito sujeito a apuração na sucessão.

    Campos de VALOR são Optional de propósito: None significa
    "desconhecido" e dispara pendência. Nunca usar 0.0 para representar
    ausência de dado — zero é um valor, não uma lacuna.
    """
    identificacao: str
    matricula: str = ""
    municipio: str = ""

    # valores monetários — None = desconhecido (≠ zero)
    custo_aquisicao_dirpf: Optional[float] = None
    data_aquisicao: Optional[date] = None
    valor_partilha: Optional[float] = None
    valor_venda: Optional[float] = None

    # classificação tributária
    regime: Regime = Regime.INDETERMINADO
    data_operacao: Optional[date] = None
    opcao: OpcaoArt23 = OpcaoArt23.NAO_APLICAVEL

    # natureza do bem — determina se FR1/FR2 (Lei 11.196/05) se aplicam.
    # True para imóveis; False para cotas societárias, veículos, etc.
    eh_imovel: bool = True

    # B-2: flag rural — imóveis rurais seguem regras de custo distintas
    # (Lei 9.393/96 — VTN do DIAT como valor de aquisição quando não há
    # escritura pública declarando custo). O motor DEVE sinalizar se este
    # flag estiver ativo mas a implementação rural ainda não estiver disponível.
    # Próximo passo: implementar módulo rural.py com cálculo do VTN.
    eh_imovel_rural: bool = False

    # M-2: bem particular — bem adquirido antes do casamento, recebido por
    # doação/herança individual ou sub-rogado de bem particular (CC/2002
    # arts. 1.659, 1.661, 1.668). Nesses casos, a fração de meação deste
    # bem específico é ZERO, independente do regime global do espólio.
    # O motor deve ignorar a fração de meação global e tratar o bem
    # como 100% pertencente à herança transmitida.
    eh_bem_particular: bool = False

    # proveniência — de onde vieram os números (auditabilidade)
    fonte_custo: str = ""
    fonte_valores: str = ""
    observacao: str = ""

    # preenchidos pelo motor
    pendencias: list[str] = field(default_factory=list)
    resultado: dict = field(default_factory=dict)


# B-2: aviso que o motor injeta automaticamente para imóveis rurais.
# Centralizado aqui para que qualquer alteração de texto ou base legal
# seja feita em um único lugar.
AVISO_IMOVEL_RURAL = (
    "[B-2 PENDENTE IMPLEMENT.] Imóvel rural identificado (eh_imovel_rural=True). "
    "A Lei 9.393/96 (Art. 14) prevê regras específicas de custo de aquisição "
    "(VTN do DIAT, Valor da Terra Nua), que diferem do custo DIRPF urbano. "
    "O motor ainda aplica a regra de imóvel urbano. REVISÃO OBRIGATÓRIA antes "
    "da entrega à RFB. Verificar o DIAT do ano de aquisição junto à Receita Federal."
)


@dataclass
class Espolio:
    """Agregado raiz: o espólio e seus metadados."""
    nome: str
    cpf_falecido: str
    data_obito: date
    data_partilha: date
    herdeiros: list[Herdeiro] = field(default_factory=list)
    bens: list[Bem] = field(default_factory=list)

    def adicionar_bem(self, bem: Bem) -> None:
        self.bens.append(bem)

    def adicionar_herdeiro(self, h: Herdeiro) -> None:
        self.herdeiros.append(h)

    def soma_fracoes(self) -> float:
        return round(sum(h.fracao_monte for h in self.herdeiros), 4)
