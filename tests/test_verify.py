from agent.verify import (
    _normalize,
    extract_literals,
    verify_answer_literals,
    verify_citations,
)


def test_normalize_ligatures_quotes_and_hyphenation():
    chunk = "The \ufb01nal \u201cre-\nnewal\u201d notice is 30 days."
    quote = 'The final "renewal" notice is 30 days.'
    assert _normalize(quote) in _normalize(chunk)


def test_invented_quote_is_invalid():
    chunks = {1: "The contract term is 12 months from the signature date."}
    valid, invalid = verify_citations(
        [{"chunk_id": 1, "quote": "The contract expires on December 15."}], chunks
    )
    assert valid == []
    assert len(invalid) == 1


def test_string_chunk_id_is_coerced_to_int():
    chunks = {1: "The contract term is 12 months."}
    valid, invalid = verify_citations(
        [{"chunk_id": "1", "quote": "12 months"}], chunks
    )
    assert invalid == []
    assert len(valid) == 1


def test_real_quote_that_does_not_support_the_claim_is_flagged():
    chunks = {
        1: "4.2 The renewal notice period is thirty (30) days before the end of the term. "
        "The contract expires on 2026-12-15."
    }
    citations = [{"chunk_id": 1, "quote": "thirty (30) days"}]
    valid, invalid = verify_citations(citations, chunks)
    assert invalid == []

    missing = verify_answer_literals(
        "The contract expires on December 15, 2026, according to clause 4.2.", valid
    )
    assert {m["kind"] for m in missing} == {"date", "clause"}


def test_supported_date_in_a_different_format_passes():
    citations = [{"chunk_id": 1, "quote": "The contract expires on 2026-12-15."}]
    assert verify_answer_literals(
        "It expires on December 15, 2026.", citations
    ) == []


def test_supported_amount_in_a_different_format_passes():
    citations = [{"chunk_id": 1, "quote": "The total is $15.000,00."}]
    assert verify_answer_literals("The total is $15,000.00.", citations) == []


def test_supported_clause_passes():
    citations = [{"chunk_id": 1, "quote": "Section 4.2 covers renewal."}]
    assert verify_answer_literals("See clause 4.2.", citations) == []


def test_derived_total_is_skipped_only_for_deterministic_calc():
    citations = [
        {"chunk_id": 1, "quote": "Monto Total: $15.000,00"},
        {"chunk_id": 2, "quote": "Monto Total: $8.400,00"},
    ]
    answer = "La suma de los montos totales de los dos contratos es $23.400,00."
    assert verify_answer_literals(answer, citations, method="deterministic_calc") == []
    assert verify_answer_literals(answer, citations, method="llm") != []


def test_extract_literals_canonicalizes_dates_amounts_and_clauses():
    literals = extract_literals(
        "On 2026-12-15 the total is $15.000,00, 99,5% of clause 4.2."
    )
    keys = {(item["kind"], item["canonical"]) for item in literals}
    assert ("date", "2026-12-15") in keys
    assert ("amount", "15000.00") in keys
    assert ("amount", "99.50%") in keys
    assert ("clause", "4.2") in keys


def test_no_literals_means_no_missing():
    citations = [{"chunk_id": 1, "quote": "No mention of dates here."}]
    assert verify_answer_literals("I could not find it in the documents.", citations) == []
