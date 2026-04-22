import { AdminDashboard } from "@/components/admin-dashboard";

export default function AdminPage() {
  return (
    <section className="space-y-6">
      <div className="page-hero">
        <p className="section-kicker">Operations Console</p>
        <h2 className="section-title mt-3">관리자 대시보드</h2>
        <p className="section-copy mt-3">
          모델 성능, correction 누적, 실패 케이스를 입체형 카드와 차트 위에 배치해 운영 흐름을 바로 확인할 수
          있도록 구성했습니다.
        </p>
      </div>

      <AdminDashboard />
    </section>
  );
}
