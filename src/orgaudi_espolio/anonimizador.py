# -*- coding: utf-8 -*-
"""
anonimizador.py — Classe utilitária para de-pseudonimização de dados
pessoais (nomes, CPFs) localmente antes do envio a APIs externas de LLM.

A-2 (correção): o máscara de CPF deixa de usar o formato xxx.xxx.xxx-xx
(que poderia parecer um CPF real e colide para índices > 99) e passa a
usar um sufixo hex-8 irrev. derivado do índice, mantendo o formato
explícito de placeholder: "ANOM-HHHHH" (nunca digitável como CPF).

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations
import copy
import hashlib
from .dominio import Espolio, Herdeiro


def _mask_cpf(indice: int, seed: str = "") -> str:
    """
    Gera um placeholder de CPF não-colidênte e não-formatável como CPF real.
    Usa hash SHA-256 do índice + seed para garantir unicidade e
    irreversibilidade sem tabela.
    """
    h = hashlib.sha256(f"{indice}:{seed}".encode()).hexdigest()[:8].upper()
    return f"ANOM-{h}"


class AnonimizadorPII:
    """
    Substitui dados sensíveis (PII) por chaves fictícias seguras e mapeia
    a reversão localmente no backend.
    """

    @staticmethod
    def anonimizar(espolio: Espolio) -> tuple[Espolio, dict[str, str]]:
        """
        Gera uma cópia do espólio mascarando nomes e CPFs. Retorna o novo
        objeto Espolio e a tabela de de-pseudonimização reversa.
        """
        mapeamento: dict[str, str] = {}

        # 1. Mascara falecido
        nome_orig = espolio.nome
        cpf_orig = espolio.cpf_falecido or ""

        nome_mask = "Autor da Heranca Anonimizado"
        cpf_mask = _mask_cpf(0, seed="falecido")

        mapeamento[nome_mask] = nome_orig
        if cpf_orig:
            mapeamento[cpf_mask] = cpf_orig

        espolio_mascarado = Espolio(
            nome=nome_mask,
            cpf_falecido=cpf_mask,
            data_obito=espolio.data_obito,
            data_partilha=espolio.data_partilha,
        )

        # 2. Clona os bens
        for b in espolio.bens:
            espolio_mascarado.adicionar_bem(copy.deepcopy(b))

        # 3. Mascara herdeiros
        for i, h in enumerate(espolio.herdeiros):
            h_nome_orig = h.nome
            h_cpf_orig = h.cpf or ""

            tipo = "Meeiro" if h.eh_meeiro else "Herdeiro"
            h_nome_mask = f"{tipo} {i + 1} Anonimizado"
            # A-2: placeholder hex-8 — nunca colide, nunca parece CPF real
            h_cpf_mask = _mask_cpf(i + 1, seed=tipo)

            mapeamento[h_nome_mask] = h_nome_orig
            if h_cpf_orig:
                mapeamento[h_cpf_mask] = h_cpf_orig

            espolio_mascarado.adicionar_herdeiro(Herdeiro(
                nome=h_nome_mask,
                cpf=h_cpf_mask,
                fracao_monte=h.fracao_monte,
                eh_meeiro=h.eh_meeiro,
            ))

        return espolio_mascarado, mapeamento

    @staticmethod
    def desanonimizar(texto: str, mapeamento: dict[str, str]) -> str:
        """
        Substitui os placeholders do texto de volta pelos dados reais.
        Ordena as chaves por tamanho decrescente para evitar substituições parciais.
        """
        if not texto or not mapeamento:
            return texto
        out = texto
        for mask, orig in sorted(mapeamento.items(), key=lambda x: len(x[0]), reverse=True):
            out = out.replace(mask, orig)
        return out
