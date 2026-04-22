import { AdminJobDetail } from "@/components/admin-job-detail";

export default function AdminJobDetailPage({ params }: { params: { id: string } }) {
  return (
    <section className="space-y-6">
      <div className="page-hero">
        <p className="section-kicker">Deep Inspection</p>
        <h2 className="section-title mt-3">관리자 상세 분석</h2>
        <p className="section-copy mt-3">
          예측문, 수정문, 원본 오디오, 문장별 confidence를 한 화면에서 비교해 실패 케이스를 빠르게 검토할 수
          있습니다.
        </p>
      </div>

      <AdminJobDetail jobId={params.id} />
    </section>
  );
}
