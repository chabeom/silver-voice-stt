from training_pipeline.dataset import (
    build_turn_based_segments,
    extract_aihub_transcript,
    extract_aihub_turns,
    load_corrections_export,
    normalize_transcript_text,
    split_text_by_max_chars,
)
from training_pipeline.manifest import train_valid_test_split


def test_extract_aihub_transcript_prefers_dialogue_turns():
    payload = {
        "qa": [
            {"question": "요즘 어떠세요?", "answer": "많이 편안합니다."},
            {"question": "", "answer": "잠도 잘 자고 있습니다."},
        ]
    }

    transcript = extract_aihub_transcript(payload)

    assert transcript == "요즘 어떠세요? 많이 편안합니다. 잠도 잘 자고 있습니다."


def test_extract_aihub_turns_returns_ordered_turns():
    payload = {
        "qa": [
            {"question": "오늘 기분은?", "answer": "좋습니다."},
            {"question": "", "answer": "산책도 했어요."},
        ]
    }

    turns = extract_aihub_turns(payload)

    assert turns == ["오늘 기분은?", "좋습니다.", "산책도 했어요."]


def test_build_turn_based_segments_splits_long_audio():
    turns = ["첫 번째 문장입니다.", "두 번째 문장입니다.", "세 번째 문장입니다."]

    segments = build_turn_based_segments(turns, total_duration_sec=90.0, target_duration_sec=35.0)

    assert len(segments) >= 2
    assert segments[0]["start_sec"] == 0.0
    assert segments[-1]["end_sec"] == 90.0


def test_build_turn_based_segments_splits_long_text():
    turns = [" ".join([f"word{index}" for index in range(60)])]

    segments = build_turn_based_segments(turns, total_duration_sec=24.0, target_duration_sec=28.0, max_segment_chars=80)

    assert len(segments) > 1
    assert all(len(segment["text"]) <= 80 for segment in segments)
    assert segments[0]["start_sec"] == 0.0
    assert segments[-1]["end_sec"] == 24.0


def test_split_text_by_max_chars_keeps_chunks_bounded():
    chunks = split_text_by_max_chars(" ".join([f"word{index}" for index in range(30)]), 50)

    assert len(chunks) > 1
    assert all(len(chunk) <= 50 for chunk in chunks)


def test_normalize_transcript_text_removes_speaker_markers():
    text = "참석자 1\n안녕하세요.\n\n참석자 2\n반갑습니다."

    normalized = normalize_transcript_text(text)

    assert normalized == "안녕하세요. 반갑습니다."


def test_load_corrections_export_supports_csv(tmp_path):
    csv_path = tmp_path / "corrections.csv"
    csv_path.write_text(
        "correction_id,job_id,original_text,corrected_text\n1,job-1,원문,교정문\n",
        encoding="utf-8",
    )

    rows = load_corrections_export(str(csv_path))

    assert rows[0]["corrected_text"] == "교정문"


def test_train_valid_test_split_keeps_small_dataset_usable():
    records = [
        {"sample_id": f"id-{index}", "audio_path": f"audio-{index}.wav", "speaker_id": None}
        for index in range(5)
    ]

    splits = train_valid_test_split(records, seed=7)

    assert len(splits["train"]) >= 1
    assert len(splits["valid"]) >= 1
    assert len(splits["test"]) >= 1
    assert sum(len(items) for items in splits.values()) == len(records)
