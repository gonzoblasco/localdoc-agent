from agent.calc import fmt_ars, sum_totals


def test_sum_contract_totals():
    chunks = [
        {"chunk_id": 1, "text": "**Monto Total:** $8.400,00", "document": "contract2"},
        {"chunk_id": 6, "text": "**Monto Total:** $15.000,00", "document": "contract1"},
    ]
    total, citations = sum_totals(chunks)
    assert total == 23400.0
    assert len(citations) == 2
    assert {c["chunk_id"] for c in citations} == {1, 6}


def test_fmt_ars():
    assert fmt_ars(23400) == "$23.400,00"
