from stt_inference.diarization import assign_speakers_to_segments


def test_assigns_speaker_with_largest_time_overlap():
    segments = [
        {"segment_index": 0, "start_sec": 0.0, "end_sec": 2.0, "text": "첫 문장"},
        {"segment_index": 1, "start_sec": 2.0, "end_sec": 4.0, "text": "두 번째 문장"},
    ]
    turns = [
        {"speaker_label": "SPEAKER_00", "start_sec": 0.0, "end_sec": 1.8},
        {"speaker_label": "SPEAKER_01", "start_sec": 1.8, "end_sec": 4.0},
    ]

    assigned = assign_speakers_to_segments(segments, turns)

    assert assigned[0]["speaker_label"] == "SPEAKER_00"
    assert assigned[0]["speaker_display_name"] == "화자 1"
    assert assigned[1]["speaker_label"] == "SPEAKER_01"
    assert assigned[1]["speaker_display_name"] == "화자 2"
