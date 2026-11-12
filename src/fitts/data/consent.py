"""Consent record persistence, kept independent from the Pygame UI."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    participant_id: str
    consent_version: str
    consented: bool
    timestamp: str

    @classmethod
    def affirmative(cls, participant_id: str, consent_version: str) -> "ConsentRecord":
        if not participant_id:
            raise ValueError("participant_id cannot be empty")
        return cls(
            participant_id=participant_id,
            consent_version=consent_version,
            consented=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class ConsentStore:
    def __init__(self, data_directory: str | Path) -> None:
        self.data_directory = Path(data_directory)

    def path_for(self, participant_id: str) -> Path:
        return self.data_directory / participant_id / "consent.json"

    def save(self, record: ConsentRecord) -> Path:
        if not record.consented:
            raise ValueError("only affirmative consent may be saved")
        destination = self.path_for(record.participant_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("x", encoding="utf-8") as handle:
                json.dump(asdict(record), handle, indent=2)
                handle.write("\n")
        except FileExistsError:
            existing = json.loads(destination.read_text(encoding="utf-8"))
            if existing.get("participant_id") != record.participant_id or not existing.get("consented"):
                raise FileExistsError(f"refusing to overwrite existing consent record: {destination}")
            # Navigating back and continuing again is idempotent for this participant.
        return destination
