import json

import pytest

from fitts.data.consent import ConsentRecord, ConsentStore


def test_serializes_affirmative_consent(tmp_path):
    store = ConsentStore(tmp_path)
    record = ConsentRecord.affirmative("anonymous-id", "draft-1")
    destination = store.save(record)
    saved = json.loads(destination.read_text(encoding="utf-8"))
    assert saved["participant_id"] == "anonymous-id"
    assert saved["consent_version"] == "draft-1"
    assert saved["consented"] is True
    assert saved["timestamp"].endswith("+00:00")


def test_refuses_to_save_non_affirmative_consent(tmp_path):
    store = ConsentStore(tmp_path)
    record = ConsentRecord("anonymous-id", "draft-1", False, "never")
    with pytest.raises(ValueError, match="affirmative"):
        store.save(record)
    assert not store.path_for("anonymous-id").exists()


def test_repeated_save_for_same_participant_is_idempotent(tmp_path):
    store = ConsentStore(tmp_path)
    first = ConsentRecord.affirmative("anonymous-id", "draft-1")
    store.save(first)
    store.save(ConsentRecord.affirmative("anonymous-id", "draft-1"))
    assert json.loads(store.path_for("anonymous-id").read_text())["timestamp"] == first.timestamp
