import json
from unittest.mock import patch

from agent.agent import answer_question
from agent.models import model_mode

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


def test_cloud_model_needs_explicit_consent_before_any_call():
    with patch("agent.agent.hybrid_search", return_value=CHUNKS) as search, patch(
        "agent.agent.ollama.chat"
    ) as chat:
        result = answer_question(
            None,
            "¿Cuánto debe?",
            model="deepseek-v4.1-flash:cloud",
            allow_cloud=False,
        )
    assert result["verification"] == "consent_required"
    assert result["model_mode"] == "cloud"
    assert result["citations"] == []
    search.assert_not_called()
    chat.assert_not_called()


def test_cloud_model_with_consent_uses_the_same_verifier():
    payload = {
        "answer": "Debe $8.400.",
        "citations": [{"chunk_id": "1", "quote": "El monto total es $8.400,00."}],
        "confidence": 0.9,
    }
    with patch("agent.agent.hybrid_search", return_value=CHUNKS), patch(
        "agent.agent.ollama.chat", return_value=_fake(payload)
    ) as chat:
        result = answer_question(
            None,
            "¿Cuánto debe?",
            model="deepseek-v4.1-flash:cloud",
            allow_cloud=True,
        )
    assert result["verification"] == "first_try"
    assert result["model_mode"] == "cloud"
    assert result["model"] == "deepseek-v4.1-flash:cloud"
    assert len(result["citations"]) == 1
    assert chat.call_args.kwargs["model"] == "deepseek-v4.1-flash:cloud"


def test_model_mode():
    assert model_mode("gemma4:12b-mlx") == "local"
    assert model_mode("deepseek-v4.1-flash:cloud") == "cloud"
    assert model_mode("") == "local"
