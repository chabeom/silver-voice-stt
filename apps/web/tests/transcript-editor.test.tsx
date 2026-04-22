import { fireEvent, render, screen } from "@testing-library/react";

import { TranscriptEditor } from "@/components/transcript-editor";

vi.mock("@/lib/api", () => ({
  saveCorrection: vi.fn(() => Promise.resolve({}))
}));

describe("TranscriptEditor", () => {
  it("allows editing transcript text", () => {
    render(
      <TranscriptEditor
        token="test-token"
        detail={{
          id: "job-1",
          user_id: "user-1",
          original_filename: "sample.wav",
          mime_type: "audio/wav",
          file_size_bytes: 100,
          upload_source: "file",
          status: "completed",
          progress: 1,
          average_confidence: 0.9,
          created_at: "2025-01-01T00:00:00Z",
          updated_at: "2025-01-01T00:00:00Z",
          transcript: {
            id: "t-1",
            job_id: "job-1",
            language: "ko",
            full_text: "원문",
            normalized_text: "정리된 문장",
            average_confidence: 0.9,
            low_confidence_ratio: 0.1,
            total_duration: 3,
            processing_ms: 1200,
            segments: []
          }
        }}
      />
    );

    const textarea = screen.getByDisplayValue("정리된 문장");
    fireEvent.change(textarea, { target: { value: "사용자 수정 문장" } });
    expect(screen.getByDisplayValue("사용자 수정 문장")).toBeInTheDocument();
  });
});

