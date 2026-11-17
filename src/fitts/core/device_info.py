"""Fixed study input context; no machine specifications are collected."""


def fixed_input_metadata(participant_id: str, window_size: tuple[int, int]) -> dict:
    # Keep the export schema compatible with earlier sessions, leaving machine
    # properties null. Window geometry is needed to interpret target positions.
    return dict(participant_id=participant_id, input_device="Trackpad",
                window_width=window_size[0], window_height=window_size[1])
