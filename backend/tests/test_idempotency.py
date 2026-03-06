from app.utils.idempotency import compute_idempotency_key, compute_input_fingerprint


def test_compute_input_fingerprint_is_stable_with_whitespace() -> None:
    a = compute_input_fingerprint(title="  Deep   Work ", authors=" Cal  Newport", description=" Focus   matters ")
    b = compute_input_fingerprint(title="deep work", authors="cal newport", description="focus matters")
    assert a == b


def test_compute_idempotency_key_changes_when_prompt_hash_changes() -> None:
    first = compute_idempotency_key(
        work_id="OL123W",
        section="key_ideas",
        prompt_hash="a" * 64,
        model="gpt-5.2",
    )
    second = compute_idempotency_key(
        work_id="OL123W",
        section="key_ideas",
        prompt_hash="b" * 64,
        model="gpt-5.2",
    )
    assert first != second
