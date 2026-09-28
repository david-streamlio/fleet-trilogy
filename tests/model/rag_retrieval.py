"""In-memory, dependency-minimal retrieval over `escalation_precedents.py` for
the RAG experiment. Deliberately skips a vector DB (Chroma etc.) -- at ~24
short precedent strings, persistent indexed storage is unnecessary machinery;
plain cosine similarity over a numpy array is simpler, equally correct at this
scale, and doesn't hide a dependency's real weight behind a nicer API. See
`docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md`'s RAG section for why this
matters for a "greenest token" talk specifically.

Uses sentence-transformers' all-MiniLM-L6-v2 -- one of the smallest embedding
models with real retrieval quality, but its own dependency (torch) is not
small; that real footprint is measured, not assumed, by the eval script that
calls this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tests.model.escalation_precedents import ESCALATION_PRECEDENTS, EscalationPrecedent

_MODEL_NAME = "all-MiniLM-L6-v2"
_encoder = None  # lazy, module-level cache -- load once per process


def _get_encoder():
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        _encoder = SentenceTransformer(_MODEL_NAME)
    return _encoder


@dataclass
class PrecedentIndex:
    precedents: tuple[EscalationPrecedent, ...]
    embeddings: np.ndarray  # (n, d), L2-normalized rows


def build_index(precedents: tuple[EscalationPrecedent, ...] = ESCALATION_PRECEDENTS) -> PrecedentIndex:
    encoder = _get_encoder()
    texts = [p.as_query_text() for p in precedents]
    raw = np.asarray(encoder.encode(texts))
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    normalized = raw / np.clip(norms, 1e-9, None)
    return PrecedentIndex(precedents=precedents, embeddings=normalized)


def retrieve_top_k(index: PrecedentIndex, query_text: str, k: int = 2) -> list[EscalationPrecedent]:
    encoder = _get_encoder()
    query_vec = np.asarray(encoder.encode([query_text]))[0]
    query_vec = query_vec / max(np.linalg.norm(query_vec), 1e-9)
    scores = index.embeddings @ query_vec
    top_indices = np.argsort(-scores)[:k]
    return [index.precedents[i] for i in top_indices]


def render_precedents_block(precedents: list[EscalationPrecedent]) -> str:
    lines = ["Similar past cases and their correct outcome (for reference only -- decide this case on its own merits):"]
    for p in precedents:
        lines.append(
            f"- Weather: {p.weather_condition}. Cargo: {p.cargo_type}. Dispatch: {p.dispatch_status}. "
            f"Correct escalation: {p.expected_direction}."
        )
    return "\n".join(lines)
