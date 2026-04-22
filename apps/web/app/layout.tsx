import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "실버 보이스 STT",
  description: "고령자 전용 한국어 STT 서비스를 위한 서비스형 프론트엔드",
};

const navItems = [
  { href: "/", label: "홈" },
  { href: "/upload", label: "음성 업로드" },
  { href: "/jobs", label: "작업 조회" },
  { href: "/admin", label: "관리자" },
  { href: "/login", label: "로그인" },
  { href: "/register", label: "회원가입" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body className="scene-shell">
        <div className="ambient-orb ambient-orb-a" />
        <div className="ambient-orb ambient-orb-b" />
        <div className="ambient-orb ambient-orb-c" />
        <div className="noise-overlay" />

        <div className="site-shell">
          <header className="site-chrome">
            <Link href="/" className="site-brand">
              <span className="site-brand__mark" />
              <span>실버 보이스</span>
            </Link>

            <nav className="site-nav">
              <ul>
                {navItems.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href}>{item.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>

            <Link href="/upload" className="site-cta">
              STT 시작하기
            </Link>
          </header>

          <main className="site-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
