import { JobsList } from "@/components/jobs-list";

export default function JobsPage() {
  return (
    <section className="space-y-6">
      <div className="page-hero">
        <p className="section-kicker">Personal Timeline</p>
        <h2 className="section-title mt-3">내 작업 목록</h2>
        <p className="section-copy mt-3">
          업로드한 음성의 처리 상태와 평균 신뢰도를 카드 단위로 정리해, 다시 확인해야 할 작업과 완료된 작업을
          빠르게 구분할 수 있습니다.
        </p>
      </div>

      <JobsList />
    </section>
  );
}
