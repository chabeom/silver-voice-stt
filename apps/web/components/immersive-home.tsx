"use client";

import Link from "next/link";
import type { CSSProperties, PointerEvent } from "react";
import { useEffect, useRef, useState } from "react";

const showcaseCards = [
  { title: "업로드 워크스페이스", subtitle: "진행률, 파일 검증, 모델 선택", tone: "blue" },
  { title: "실시간 상태 추적", subtitle: "SSE 기반 단계별 상태 스트리밍", tone: "mint" },
  { title: "문장별 신뢰도 검토", subtitle: "낮은 점수 구간 자동 강조", tone: "peach" },
  { title: "관리자 대시보드", subtitle: "모델 버전, 오류율, 처리 시간 분석", tone: "violet" },
  { title: "정정 데이터 적재", subtitle: "재학습용 correction 루프 연결", tone: "yellow" },
  { title: "오디오 전처리", subtitle: "16kHz 변환, VAD, 노이즈 감소", tone: "ice" },
];

const solutionCards = [
  {
    title: "고령자 특화 한국어 STT",
    description:
      "Whisper 계열 모델을 고령자와 구음장애 사용자 데이터에 맞춰 운영 가능한 STT 서비스로 재구성합니다.",
    badges: ["한국어 STT", "Whisper", "고령자 특화"],
  },
  {
    title: "비동기 처리 파이프라인",
    description:
      "업로드부터 전처리, 추론, 후처리, 결과 저장까지 Redis와 Celery 기반 비동기 흐름으로 안정적으로 연결합니다.",
    badges: ["FastAPI", "Celery", "Redis"],
  },
  {
    title: "운영형 관리자 시스템",
    description:
      "처리 시간, 평균 신뢰도, 오류율, 실패 케이스, 모델 버전 비교를 한 화면에서 관리할 수 있게 설계합니다.",
    badges: ["대시보드", "통계", "모델 비교"],
  },
  {
    title: "재학습 데이터 루프",
    description:
      "사용자 정정 결과와 세그먼트 정보, 환경 메타데이터를 구조적으로 저장해 다음 학습 파이프라인으로 이어줍니다.",
    badges: ["Correction", "Manifest", "Fine-tuning"],
  },
];

const partnerMarks = [
  "FastAPI",
  "Next.js",
  "PostgreSQL",
  "Redis",
  "MinIO",
  "Whisper",
  "faster-whisper",
  "Docker",
];

type PointerState = {
  x: number;
  y: number;
  glowX: string;
  glowY: string;
};

const idlePointer: PointerState = {
  x: 0,
  y: 0,
  glowX: "58%",
  glowY: "38%",
};

function duplicatedCards() {
  return [...showcaseCards, ...showcaseCards];
}

export function ImmersiveHome() {
  const frameRef = useRef<number | null>(null);
  const pendingPointerRef = useRef({ x: 0, y: 0 });
  const [pointer, setPointer] = useState<PointerState>(idlePointer);

  useEffect(() => {
    return () => {
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, []);

  function applyPointer(x: number, y: number) {
    setPointer({
      x,
      y,
      glowX: `${58 + x * 10}%`,
      glowY: `${38 + y * 8}%`,
    });
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
    const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;

    pendingPointerRef.current = { x, y };

    if (frameRef.current === null) {
      frameRef.current = window.requestAnimationFrame(() => {
        frameRef.current = null;
        applyPointer(pendingPointerRef.current.x, pendingPointerRef.current.y);
      });
    }
  }

  function handlePointerLeave() {
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    }

    setPointer(idlePointer);
  }

  const visualStyle = {
    "--hero-transform": `perspective(1800px) rotateX(${-pointer.y * 6}deg) rotateY(${pointer.x * 7}deg)`,
    "--hero-glow-x": pointer.glowX,
    "--hero-glow-y": pointer.glowY,
    "--hero-card-a": `translate3d(${pointer.x * 16}px, ${pointer.y * -12}px, 80px) rotateX(${-pointer.y * 6}deg) rotateY(${pointer.x * 8}deg)`,
    "--hero-card-b": `translate3d(${pointer.x * -14}px, ${pointer.y * 10}px, 80px) rotateX(${-pointer.y * 5}deg) rotateY(${pointer.x * 7}deg)`,
    "--hero-card-c": `translate3d(${pointer.x * 12}px, ${pointer.y * 12}px, 80px) rotateX(${-pointer.y * 5}deg) rotateY(${pointer.x * 7}deg)`,
  } as CSSProperties;

  return (
    <div className="webon-home">
      <section className="webon-hero">
        <div className="webon-hero__copy">
          <div className="webon-hero__brand">silver voice</div>
          <h1 className="webon-hero__title">
            정확한 분석과 기술로
            한국어 STT의 여정을 함께합니다.
          </h1>
          <p className="webon-hero__description">
            고령자와 구음장애 사용자를 위한 한국어 음성 인식 서비스를 서비스형 MVP로 구축합니다.
            업로드, 추론, 정정, 관리자 분석, 재학습 루프까지 한 제품 흐름으로 연결합니다.
          </p>
        </div>

        <div
          className="webon-hero__visual"
          style={visualStyle}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
        >
          <div className="webon-hero__gradient webon-hero__gradient--left" />
          <div className="webon-hero__gradient webon-hero__gradient--right" />

          <article className="webon-hero-card webon-hero-card--primary">
            <span className="webon-hero-card__eyebrow">실시간 음성 인식 허브</span>
            <strong>whisper-ko-elderly-v1</strong>
            <p>전처리, 추론, 후처리, correction 저장까지 한 화면 흐름으로 연결</p>
          </article>

          <article className="webon-hero-card webon-hero-card--secondary">
            <span className="webon-hero-card__eyebrow">세그먼트 분석</span>
            <strong>문장별 신뢰도와 타임스탬프</strong>
            <p>낮은 신뢰도 구간을 자동으로 강조하고 수정 기록을 저장합니다.</p>
          </article>

          <article className="webon-hero-card webon-hero-card--accent">
            <span className="webon-hero-card__eyebrow">관리자 운영</span>
            <strong>평균 신뢰도 92.4%</strong>
            <p>모델 버전 비교, 실패 케이스 필터링, 재학습 export 지원</p>
          </article>

          <div className="webon-hero__visual-badge">
            <span>실시간 처리 상태</span>
            <strong>업로드 / 전처리 / 추론 / 완료</strong>
          </div>
        </div>
      </section>

      <section className="webon-intro-section">
        <div className="webon-intro-section__content">
          <h2>
            북극성 같은 길잡이,
            <br />
            운영형 STT 플랫폼으로 연결합니다.
          </h2>
          <p>
            사용자 웹, 관리자 웹, 백엔드 API, 비동기 워커, 모델 추론, correction 데이터 루프까지
            실제 운영 가능한 구조로 연결합니다. 프론트엔드는 서비스 소개 사이트처럼 깔끔한 흐름을
            유지하면서도 제품 화면으로 바로 이어질 수 있게 설계했습니다.
          </p>
          <Link href="/upload" className="webon-button webon-button--dark">
            실버 보이스 서비스 소개
          </Link>
        </div>
      </section>

      <section className="webon-marquee-section">
        <div className="webon-marquee webon-marquee--left">
          <div className="webon-marquee__track">
            {duplicatedCards().map((card, index) => (
              <article key={`${card.title}-${index}`} className={`webon-project-card webon-project-card--${card.tone}`}>
                <div className="webon-project-card__thumb" />
                <div className="webon-project-card__meta">
                  <strong>{card.title}</strong>
                  <span>{card.subtitle}</span>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="webon-marquee__cta">
          <p>
            실버 보이스의 최근 화면 구성을 확인하고
            <br />
            <b>운영형 STT 제품 플로우를 바로 살펴보세요.</b>
          </p>
          <Link href="/jobs" className="webon-button webon-button--light">
            작업 화면 둘러보기
          </Link>
        </div>
      </section>

      <section className="webon-solutions">
        <div className="webon-solutions__header">
          <p className="webon-solutions__eyebrow">핵심 솔루션</p>
          <h2>
            축적된 경험을 바탕으로 하는
            <br />
            실버 보이스의 운영형 구성 요소
          </h2>
        </div>

        <div className="webon-solutions__grid">
          {solutionCards.map((card) => (
            <article key={card.title} className="webon-solution-card">
              <div className="webon-solution-card__orb" />
              <h3>{card.title}</h3>
              <p>{card.description}</p>
              <div className="webon-solution-card__badges">
                {card.badges.map((badge) => (
                  <span key={badge}>{badge}</span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="webon-clients">
        <div className="webon-clients__header">
          <p>연결 기술</p>
          <h2>
            성공적인 서비스 구성을 위해
            <br />
            함께 움직이는 기술 스택이 있습니다.
          </h2>
        </div>

        <div className="webon-clients__grid">
          {partnerMarks.map((mark) => (
            <div key={mark} className="webon-client-pill">
              {mark}
            </div>
          ))}
        </div>
      </section>

      <section className="webon-request-banner">
        <div className="webon-request-banner__inner">
          <div className="webon-request-banner__title">
            <Link href="/upload">지금 바로 실버 보이스를 시작해보세요</Link>
          </div>
          <div className="webon-request-banner__desc">
            복잡하지 않습니다.
            <br />
            <b>음성 파일 업로드부터 결과 검토까지 바로 확인할 수 있습니다.</b>
          </div>
          <Link href="/upload" className="webon-button webon-button--dark">
            빠른 STT 시작
          </Link>
        </div>
      </section>
    </div>
  );
}
