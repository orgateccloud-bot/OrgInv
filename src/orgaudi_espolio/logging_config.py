# -*- coding: utf-8 -*-
"""
logging_config.py — Configuração de logging estruturado (JSON) para o OrgAudi.

B-5: o backend não tinha logging. Falhas na extração de PDF, timeouts do
Anthropic e erros de parsing eram silenciosos ou retornavam apenas o texto
da exceção ao cliente, sem rastreabilidade operacional.

Este módulo configura:
  • Formatter JSON com campos: timestamp, level, logger, message, request_id,
    espolio_hash, exc_info.
  • Um handler de console (stdout) adequado para Docker/Windows Service.
  • Níveis configuráveis por env-var LOG_LEVEL (padrão: INFO).

Uso:
    from orgaudi_espolio.logging_config import get_logger
    log = get_logger(__name__)
    log.info("apuracao concluida", extra={"espolio_hash": hash_str})

Sistema OrgAudi · ORGATEC CONTABILIDADE E AUDITORIA
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """Serializa cada registro como uma linha JSON — ideal para coleta por agentes."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
        }

        # campos extras injetados via extra={...} no log.info(...)
        for key in ("request_id", "espolio_hash", "endpoint", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        if record.exc_info:
            payload["exc_info"] = "".join(
                traceback.format_exception(*record.exc_info)
            )

        return json.dumps(payload, ensure_ascii=False)


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    return handler


def configure_logging() -> None:
    """
    Configura o logger raiz do OrgAudi. Chamar UMA VEZ no startup da API.
    Nível controlado pela env var LOG_LEVEL (DEBUG/INFO/WARNING/ERROR).
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger("orgaudi")
    if root.handlers:
        return  # já configurado (evita duplicação em reload do uvicorn)

    root.setLevel(level)
    root.addHandler(_build_handler())
    root.propagate = False

    root.info(
        "logging estruturado inicializado",
        extra={"level_configurado": level_name},
    )


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger filho de 'orgaudi', configurado automaticamente."""
    configure_logging()
    return logging.getLogger(f"orgaudi.{name}")
