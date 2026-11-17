"""CSV exports backed by durable per-trial transactions and active checkpoints.

The journal is authoritative after a crash. Recovery writes a separate export;
it never changes the original event files or a finalized session.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fitts.data.models import Demographics

SCHEMAS = {
    "demographics": "participant_id,age,computer_hours_per_week,mouse_hand,dominant_hand",
    "device_info": "participant_id,os_name,os_version,cpu_model,cpu_architecture,cpu_count,ram_gb,python_version,pygame_version,display_width,display_height,window_width,window_height,display_scale,refresh_rate_hz,input_device,mouse_dpi",
    "trial_sequence": "participant_id,block_number,trial_number,overall_trial_number,direction,target_width_px,target_distance_px,target_center_x,target_center_y",
    "trials": "participant_id,session_id,block_number,trial_number,overall_trial_number,direction,target_width_px,target_distance_px,start_x,start_y,target_x,target_y,start_time_ns,end_time_ns,movement_time_ms,path_length_px,miss_count,total_clicks,success,status",
    "mouse_events": "participant_id,session_id,block_number,trial_number,event_type,timestamp_ns,relative_time_ms,x,y,direction,button",
    "clicks": "participant_id,session_id,block_number,trial_number,timestamp_ns,relative_time_ms,click_x,click_y,hit_target,click_number,button",
}
SCHEMAS = {key: value.split(",") for key, value in SCHEMAS.items()}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, document: dict) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_csv(path: Path, schema: list[str], rows, *, append: bool = False) -> None:
    with path.open("a" if append else "x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=schema, extrasaction="ignore")
        if not append:
            writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())


class Recorder:
    def __init__(self, folder: Path, participant_id: str, config: dict):
        self.folder = Path(folder)
        consent = json.loads((self.folder / "consent.json").read_text(encoding="utf-8"))
        if consent.get("consented") is not True or consent.get("participant_id") != participant_id:
            raise PermissionError("Affirmative consent is required before collection")
        if (self.folder / "session.json").exists():
            raise FileExistsError("Session already exists; use recovery for an interrupted session")
        self.journal = self.folder / "journal"
        self.journal.mkdir(exist_ok=False)
        self.session = dict(participant_id=participant_id, session_id=uuid.uuid4().hex,
                            created_at=utc_now(), status="onboarding", config=config,
                            random_seed=config["random_seed"], finalized=False,
                            completed_trials=0, total_missed_clicks=0, total_active_movement_time_ms=0.0,
                            focus_policy="End session incomplete on focus loss; active trial is interrupted.",
                            clock="time.perf_counter_ns; timestamps are event processing times",
                            checkpoint_interval_seconds=1)
        self.finalized = False
        self.committed = set()
        for name in SCHEMAS:
            write_csv(self.folder / f"{name}.csv", SCHEMAS[name], [])
        self.save_session()

    def save_session(self):
        self._writable()
        atomic_json(self.folder / "session.json", self.session)

    def _writable(self):
        if self.finalized:
            raise RuntimeError("Finalized data is immutable")

    def save_demographics(self, demographics: Demographics):
        self._writable()
        if self.session["status"] != "onboarding":
            raise RuntimeError("Responses cannot change after experimental trials begin")
        if demographics.participant_id != self.session["participant_id"]:
            raise ValueError("participant mismatch")
        temporary = self.folder / "demographics.new.csv"
        temporary.unlink(missing_ok=True)
        write_csv(temporary, SCHEMAS["demographics"], [asdict(demographics)])
        os.replace(temporary, self.folder / "demographics.csv")
        self.session["demographics"] = asdict(demographics)
        self.save_session()

    def save_onboarding(self, demographics: Demographics, device: dict):
        self._writable()
        if demographics.participant_id != self.session["participant_id"] or device["participant_id"] != demographics.participant_id:
            raise ValueError("participant mismatch")
        if self.session["status"] != "onboarding":
            raise RuntimeError("Responses cannot change after experimental trials begin")
        # Responses may be reviewed during onboarding. Replace only these two snapshots.
        for name, row in (("demographics", asdict(demographics)), ("device_info", device)):
            temporary = self.folder / f"{name}.new.csv"
            if temporary.exists():
                temporary.unlink()
            write_csv(temporary, SCHEMAS[name], [row])
            os.replace(temporary, self.folder / f"{name}.csv")
        self.session.update(demographics=asdict(demographics), device_info=device)
        self.save_session()

    def save_schedule(self, schedule, window_size):
        self._writable()
        if self.session.get("assigned_trials"):
            raise RuntimeError("The saved schedule cannot be regenerated")
        rows = []
        for assigned in schedule:
            trial = assigned.condition
            center, _ = trial.circle(*window_size)
            rows.append(dict(participant_id=self.session["participant_id"], block_number=assigned.block_number,
                             trial_number=assigned.trial_number, overall_trial_number=assigned.overall_trial_number,
                             direction=trial.direction, target_width_px=trial.target_width,
                             target_distance_px=trial.distance, target_center_x=center[0], target_center_y=center[1]))
        temporary = self.folder / "sequence.new.csv"
        write_csv(temporary, SCHEMAS["trial_sequence"], rows)
        os.replace(temporary, self.folder / "trial_sequence.csv")
        self.session.update(assigned_trials=len(rows), status="running", started_at=utc_now())
        self.save_session()

    def checkpoint(self, transaction: dict):
        self._writable()
        atomic_json(self.journal / "active.json", transaction)

    def commit(self, transaction: dict):
        self._writable()
        row = transaction["trial"]
        number = row["overall_trial_number"]
        if number in self.committed:
            raise RuntimeError("Trial already committed")
        destination = self.journal / f"trial_{number:04d}.json"
        if destination.exists():
            raise RuntimeError("Trial journal already exists; recover the session")
        atomic_json(destination, transaction)
        # A crash between CSV appends is repaired from the complete journal transaction.
        for name, rows in (("mouse_events", transaction["events"]), ("clicks", transaction["clicks"]), ("trials", [row])):
            write_csv(self.folder / f"{name}.csv", SCHEMAS[name], rows, append=True)
        self.committed.add(number)
        self.session["completed_trials"] += int(row["success"])
        self.session["total_missed_clicks"] += row["miss_count"]
        self.session["total_active_movement_time_ms"] += row["movement_time_ms"] or 0
        self.save_session()
        (self.journal / "active.json").unlink(missing_ok=True)

    def finalize(self, status: str):
        self._writable()
        if status == "completed" and self.session["completed_trials"] != self.session.get("assigned_trials"):
            raise ValueError("Cannot finalize an incomplete experiment as completed")
        self.session.update(status=status, finalized=True, ended_at=utc_now())
        self.save_session()
        self.finalized = True


def recover_session(folder: Path, output: Path):
    """Rebuild an interrupted export in a new directory, preserving source bytes."""
    import shutil
    folder, output = Path(folder), Path(output)
    if folder.resolve() == output.resolve():
        raise ValueError("Recovery output must be a separate new directory")
    session = json.loads((folder / "session.json").read_text(encoding="utf-8"))
    if session.get("finalized"):
        raise ValueError("Session is finalized; original exports are immutable")
    transactions = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((folder / "journal").glob("trial_*.json"))]
    numbers = {t["trial"]["overall_trial_number"] for t in transactions}
    active = folder / "journal" / "active.json"
    if active.exists():
        transaction = json.loads(active.read_text(encoding="utf-8"))
        if transaction["trial"]["overall_trial_number"] not in numbers:
            transaction["trial"].update(status="interrupted", success=False, end_time_ns=None, movement_time_ms=None)
            transactions.append(transaction)
    output.mkdir(parents=True, exist_ok=False)
    for name in ("consent.json", "demographics.csv", "device_info.csv", "trial_sequence.csv"):
        shutil.copyfile(folder / name, output / name)
    for name, key in (("trials", "trial"), ("mouse_events", "events"), ("clicks", "clicks")):
        rows = [row for t in transactions for row in ([t[key]] if key == "trial" else t[key])]
        write_csv(output / f"{name}.csv", SCHEMAS[name], rows)
    session.update(status="incomplete", finalized=True, recovered_at=utc_now(),
                   completed_trials=sum(bool(t["trial"]["success"]) for t in transactions),
                   total_missed_clicks=sum(t["trial"]["miss_count"] for t in transactions),
                   total_active_movement_time_ms=sum(t["trial"]["movement_time_ms"] or 0 for t in transactions))
    atomic_json(output / "session.json", session)


def main():
    parser = argparse.ArgumentParser(description="Recover CSVs from an interrupted session into a NEW directory")
    parser.add_argument("session", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    recover_session(args.session, args.output)


if __name__ == "__main__":
    main()
