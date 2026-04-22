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

    expect(screen.getByText("이 구간은 다시 확인하는 것을 권장합니다.")).toBeInTheDocument();
  });
});

