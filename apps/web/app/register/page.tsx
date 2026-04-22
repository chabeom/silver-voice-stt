"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button, Card, CardContent, CardHeader, CardTitle, Input } from "@silver-voice/ui";

import { FeedbackPopup } from "@/components/feedback-popup";
import { getErrorMessage, register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", full_name: "", password: "" });
  const [errorPopup, setErrorPopup] = useState("");

  async function handleRegister() {
    try {
      await register(form);
      setErrorPopup("");
      router.push("/login");
    } catch (error) {
      setErrorPopup(getErrorMessage(error, "회원가입에 실패했습니다."));
    }
  }

  return (
    <>
      <div className="mx-auto max-w-2xl">
        <Card className="depth-card--hero overflow-hidden">
          <CardHeader>
            <p className="section-kicker">Create Workspace Access</p>
            <CardTitle className="mt-3">회원가입</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <p className="section-copy">
              서비스에 접속할 계정을 만들면 바로 업로드와 transcript 교정 기능을 사용할 수 있습니다.
            </p>
            <Input
              placeholder="이름"
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            />
            <Input
              placeholder="이메일"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
            <Input
              placeholder="비밀번호"
              type="password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
            <Button onClick={() => void handleRegister()} className="w-full text-lg">
              계정 만들기
            </Button>
            <p className="text-base text-slate-700">이미 계정이 있다면 로그인 화면에서 바로 접속할 수 있습니다.</p>
            <Link href="/login" className="inline-flex font-semibold text-sky-700">
              로그인으로 이동
            </Link>
          </CardContent>
        </Card>
      </div>

      <FeedbackPopup
        open={Boolean(errorPopup)}
        title="회원가입 실패"
        description={errorPopup}
        onClose={() => setErrorPopup("")}
      />
    </>
  );
}
