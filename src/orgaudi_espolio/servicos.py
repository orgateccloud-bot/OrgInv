# -*- coding: utf-8 -*-
"""
servicos.py — Camada de serviços e lógica de simulação da reforma tributária.
Centraliza as operações de conversão DTO/Entidade e o cálculo do checksum de integridade.

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations
import hashlib
from datetime import date, datetime
from typing import Optional
from .dominio import Espolio, Herdeiro, Bem, Regime, OpcaoArt23

class EspolioService:
    """Orquestrador de ações de domínio do Espólio na API."""

    @staticmethod
    def converter_para_dominio(data: dict) -> Espolio:
        """Traduz dicionários de dados vindo da API para entidades de domínio."""
        e = Espolio(
            nome=data.get("nome", ""),
            cpf_falecido=data.get("cpf_falecido", ""),
            data_obito=EspolioService._iso(data.get("data_obito")) or date.today(),
            data_partilha=EspolioService._iso(data.get("data_partilha")) or date.today(),
        )
        for h in data.get("herdeiros", []):
            if not h.get("nome", "").strip():
                continue
            e.adicionar_herdeiro(Herdeiro(
                nome=h.get("nome"),
                cpf=h.get("cpf") or "",
                fracao_monte=float(h.get("fracao_monte") or 0.0),
                eh_meeiro=bool(h.get("eh_meeiro", False)),
            ))
        for b in data.get("bens", []):
            if not b.get("identificacao", "").strip():
                continue
            e.adicionar_bem(Bem(
                identificacao=b.get("identificacao"),
                matricula=b.get("matricula") or "",
                municipio=b.get("municipio") or "",
                custo_aquisicao_dirpf=b.get("custo_aquisicao_dirpf"),
                data_aquisicao=EspolioService._iso(b.get("data_aquisicao")),
                valor_partilha=b.get("valor_partilha"),
                valor_venda=b.get("valor_venda"),
                regime=EspolioService._regime(b.get("regime")),
                data_operacao=EspolioService._iso(b.get("data_operacao")),
                opcao=EspolioService._opcao(b.get("opcao")),
                eh_imovel=bool(b.get("eh_imovel", True)),
                # B-2: flag rural — mapeia o campo da API para o domínio
                eh_imovel_rural=bool(b.get("eh_imovel_rural", False)),
            ))
        return e

    @staticmethod
    def calcular_audit_hash(espolio: Espolio) -> str:
        """Gera um checksum de conformidade SHA-256 dos dados essenciais.

        B-4: valores None (lacüna) são representados pelo sentinel "NULL",
        nunca como 0.0. Hash(custo=None) ≠ Hash(custo=0.0), preservando a
        integridade da cadeia de custódia forense.
        """
        def _v(x) -> str:
            """Representa um valor opcional de forma determinística e única."""
            return "NULL" if x is None else str(x)

        hasher = hashlib.sha256()
        hasher.update(hashlib.sha256(espolio.nome.encode("utf-8")).digest())
        hasher.update(espolio.data_obito.isoformat().encode("utf-8"))
        hasher.update(espolio.data_partilha.isoformat().encode("utf-8"))

        for h in sorted(espolio.herdeiros, key=lambda x: x.nome):
            h_name = hashlib.sha256(h.nome.encode("utf-8")).hexdigest()
            h_cpf = hashlib.sha256(h.cpf.encode("utf-8")).hexdigest() if h.cpf else ""
            hasher.update(f"h:{h_name}:{h_cpf}:{h.fracao_monte}:{h.eh_meeiro}".encode("utf-8"))

        for b in sorted(espolio.bens, key=lambda x: x.identificacao):
            # B-4: _v() garante que None != 0.0 no hash
            hasher.update(
                f"b:{b.identificacao}:{b.regime.value}:{b.opcao.value}:"
                f"{_v(b.custo_aquisicao_dirpf)}:{_v(b.valor_partilha)}:{_v(b.valor_venda)}"
                .encode("utf-8")
            )

        return hasher.hexdigest()

    @staticmethod
    def _iso(s: Optional[str]) -> Optional[date]:
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            # A-4: data malformada é registrada, não silenciada.
            # O motor gerará uma pendência de "data ausente"; o profissional
            # precisa saber que havia um valor — apenas ilegível.
            import warnings
            warnings.warn(
                f"Data malformada ignorada: {s!r}. "
                "Verificar o JSON de entrada e corrigir antes da entrega à RFB.",
                stacklevel=4,
            )
            return None

    @staticmethod
    def _regime(s: str | None) -> Regime:
        if not s:
            return Regime.INDETERMINADO
        try:
            return next(r for r in Regime if r.value == s)
        except StopIteration:
            return Regime.INDETERMINADO

    @staticmethod
    def _opcao(s: str | None) -> OpcaoArt23:
        if not s:
            return OpcaoArt23.NAO_APLICAVEL
        try:
            return next(o for o in OpcaoArt23 if o.value == s)
        except StopIteration:
            return OpcaoArt23.NAO_APLICAVEL


class CalculadoraReforma:
    """Simula os impactos tributários previstos com a Reforma Tributária (IBS/CBS)."""

    @staticmethod
    def calcular_cenario_reforma(espolio: Espolio, aliquota_cbs_ibs: float = 26.5) -> dict:
        """
        Projeta a incidência de IBS/CBS sobre o ganho de capital de imóveis,
        respeitando a meação.
        """
        resultados = []
        imposto_reforma_total = 0.0

        # Fração de meação acumulada
        fracao_meacao = sum(h.fracao_monte for h in espolio.herdeiros if h.eh_meeiro)
        fracao_meacao = min(max(fracao_meacao, 0.0), 1.0)
        fracao_heranca = 1.0 - fracao_meacao

        for b in espolio.bens:
            # C-3: lacüna ≠ zero — custo ausente não é zero; registra pendência.
            if b.custo_aquisicao_dirpf is None:
                resultados.append({
                    "bem": b.identificacao,
                    "ganho_total": None,
                    "base_espolio": None,
                    "base_meeiro": None,
                    "imposto_espolio": None,
                    "imposto_meeiro": None,
                    "imposto_total": None,
                    "pendencia": (
                        "Custo de aquisição ausente — simulação não pode ser "
                        "concluída para este bem. NÃO assumir zero (lacüna ≠ zero)."
                    ),
                })
                continue

            custo = b.custo_aquisicao_dirpf
            valor_base = b.valor_venda or b.valor_partilha or 0.0
            
            ganho_total = max(valor_base - custo, 0.0)
            
            # Segregação de meação
            ganho_espolio = ganho_total * fracao_heranca
            ganho_meeiro = ganho_total * fracao_meacao
            
            imposto_espolio = ganho_espolio * (aliquota_cbs_ibs / 100.0)
            imposto_meeiro = ganho_meeiro * (aliquota_cbs_ibs / 100.0)
            
            imposto_reforma_total += imposto_espolio
            
            resultados.append({
                "bem": b.identificacao,
                "ganho_total": round(ganho_total, 2),
                "base_espolio": round(ganho_espolio, 2),
                "base_meeiro": round(ganho_meeiro, 2),
                "imposto_espolio": round(imposto_espolio, 2),
                "imposto_meeiro": round(imposto_meeiro, 2),
                "imposto_total": round(imposto_espolio + imposto_meeiro, 2)
            })

        return {
            "aliquota_simulada": aliquota_cbs_ibs,
            "imposto_reforma_total_espolio": round(imposto_reforma_total, 2),
            "bens": resultados
        }
