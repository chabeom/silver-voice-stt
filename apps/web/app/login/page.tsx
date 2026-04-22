"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@silver-voice/ui";

import { FeedbackPopup } from "@/components/feedback-popup";
import { getErrorMessage, login } from "@/lib/api";
import { setTokens } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorPopup, setErrorPopup] = useState("");

  async function handleLogin() {
    try {
      const tokens = await login({ email, password });
      setTokens(tokens.access_token, tokens.refresh_token);
      setErrorPopup("");
      router.push("/upload");
    } catch (error) {
      setErrorPopup(getErrorMessage(error, "로그인에 실패했습니다."));
    }
  }

  return (
    <>
      <div className="mx-auto max-w-2xl">
        <Card className="depth-card--hero depth-card--glow overflow-hidden">
          <CardHeader>
            <p className="section-kicker">Secure Access</p>
            <CardTitle className="mt-3">로그인</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <p className="section-copy">
              음성 업로드, 작업 조회, 관리자 화면에 접근하려면 계정으로 로그인해 주세요.
            </p>
            <Input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="이메일" />
            <Input
              value={password}
              type="password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="비밀번호"
            />
            <Button onClick={() => void handleLogin()} className="w-full text-lg">
              로그인
            </Button>
            <div className="signal-banner space-y-2 px-4 py-4">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Demo Account</p>
              <p className="text-base text-slate-800">admin@silvervoice.example.com / Admin123!</p>
            </div>
            <p className="text-base text-slate-700">계정이 없다면 회원가입 후 바로 사용하실 수 있습니다.</p>
            <Link href="/register" className="inline-flex font-semibold text-sky-700">
              회원가입으로 이동
            </Link>
          </CardContent>
        </Card>
      </div>

      <FeedbackPopup
        open={Boolean(errorPopup)}
        title="로그인 실패"
        description={errorPopup}
        onClose={() => setErrorPopup("")}
      />
    </>
  );
}
