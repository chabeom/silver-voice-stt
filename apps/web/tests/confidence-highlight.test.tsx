import React from "react";
import { render, screen } from "@testing-library/react";

import { ConfidenceHighlight } from "@/components/confidence-highlight";

describe("ConfidenceHighlight", () => {
  it("renders warning message for low confidence segments", () => {
    render(
      <ConfidenceHighlight
        segment={{
          id: "seg-1",
          segment_index: 0,
          start_sec: 0,
          end_sec: 1.5,
          text: "테스트",
          normalized_text: "테스트",
          confidence: 0.4,
          is_low_confidence: true
        }}
      />
    );

    expect(screen.getByText("낮은 confidence 구간입니다. 원본 오디오와 함께 다시 확인해 주세요.")).toBeInTheDocument();
  });

  it("renders the assigned speaker", () => {
    render(
      <ConfidenceHighlight
        segment={{
          id: "seg-speaker",
          segment_index: 0,
          start_sec: 0,
          end_sec: 1.5,
          text: "안녕하세요",
          normalized_text: "안녕하세요",
          confidence: 0.9,
          speaker_display_name: "화자 2",
          speaker_confidence: 0.8,
          is_low_confidence: false
        }}
      />
    );

    expect(screen.getByText("화자 2")).toBeInTheDocument();
    expect(screen.getByText("화자 배정 일치도 80.0%")).toBeInTheDocument();
  });
});
