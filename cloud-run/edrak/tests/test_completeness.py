"""Coverage evidence must not reveal demo-only knowledge before consent."""
from app.functions.completeness import build_evidence, check_completeness
from app.agents.data_sufficiency import _guard_unverified_bank_claims


def _customer():
    return {"customer_id": "C1", "salary": 10000}


def _transactions():
    return [
        {
            "transaction_id": "SAL-1",
            "transaction_date": "2026-07-01",
            "transaction_type": "income",
            "amount": 10000,
            "raw_description": "SALARY",
        },
        {
            "transaction_id": "EXP-1",
            "transaction_date": "2026-07-05",
            "transaction_type": "expense",
            "amount": -500,
            "raw_description": "POS MARKET",
        },
    ]


def test_ai_evidence_contains_no_unlinked_bank_identity():
    evidence = build_evidence(
        _customer(), [], _transactions(), [], connected_banks=["ALINMA"]
    )

    assert evidence["connected_banks_ar"] == ["مصرف الإنماء"]
    assert "unlinked_known_banks_ar" not in evidence
    assert "الراجحي" not in str(evidence)


def test_demo_link_suggestion_remains_outside_ai_evidence():
    report = check_completeness(
        _customer(), [], _transactions(), [], connected_banks=["ALINMA"]
    )

    assert report["suggested_banks"] == [
        {"bank_code": "ALRAJHI", "bank_name_ar": "مصرف الراجحي"}
    ]


def test_guessed_unlinked_bank_name_is_replaced_with_uncertainty():
    findings = _guard_unverified_bank_claims(
        ["مصرف الراجحي غير مرتبط وقد توجد فيه نفقات."],
        connected_banks_ar=["مصرف الإنماء"],
    )

    assert findings == [
        "قد تكون بعض مصادر الدخل أو النفقات خارج الحسابات المرتبطة؛ "
        "لا يمكن تحديد البنك قبل موافقتك على الربط."
    ]
