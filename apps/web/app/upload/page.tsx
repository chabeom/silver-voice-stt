import { UploadWorkspace } from "@/components/upload-workspace";

export default function UploadPage() {
  return (
    <section className="space-y-6">
      <div className="page-hero">
        <p className="section-kicker">Capture & Queue</p>
        <h2 className="section-title mt-3">파일 업로드와 녹음을 하나의 입체 작업 공간으로</h2>
        <p className="section-copy mt-3">
          파일 업로드와 브라우저 녹음을 같은 화면에서 처리하고, 현재 작업 상태를 실시간 패널로 분리해 흐름을
          한눈에 파악할 수 있게 구성했습니다.
        </p>
      </div>

      <UploadWorkspace />
    </section>
  );
}
