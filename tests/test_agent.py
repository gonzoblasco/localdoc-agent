import json
from unittest.mock import patch

from agent.agent import answer_question

CHUNKS = [
    {
        "chunk_id": 1,
        "text": "El monto total es $8.400,00.",
        "document": "contract2",
        "page": 1,
        "section": "Datos",
        "clause": "intro",
    }
]


def _fake(payload):
    return {"message": {"content": json.dumps(payload)}}


def test_answer_with_valid_citation():
    payload = {
        "answer": "Debe $8.400.",
        "citations": [{"chunk_id": 1, "quote": "El monto total es $8.400,00."}],
        "confidence": 0.9,
    }
    with patch("agent.agent.hybrid_search", return_value=CHUNKS), patch(
        "agent.agent.ollama.chat", return_value=_fake(payload)
    ):
        result = answer_question(None, "¿Cuánto debe?")
    assert result["answer"] == "Debe $8.400."
    assert len(result["citations"]) == 1
    assert result["sources"][0]["document"] == "contract2"


def test_refusal_on_invalid_citation():
    payload = {
        "answer": "Debe $9.999.",
        "citations": [{"chunk_id": 1, "quote": "texto que no existe"}],
        "confidence": 0.9,
    }
    with patch("agent.agent.hybrid_search", return_value=CHUNKS), patch(
        "agent.agent.ollama.chat", return_value=_fake(payload)
    ):
        result = answer_question(None, "¿Cuánto debe?")
    assert result["citations"] == []
    assert "verificar" in result["answer"] or "reformular" in result["answer"]
