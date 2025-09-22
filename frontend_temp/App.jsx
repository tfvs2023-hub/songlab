import { useState } from "react";
import { motion } from "framer-motion";
import { Mic, Gauge, BarChart3, Play, ChevronRight, ShieldCheck, Youtube, Cpu, Zap, CheckCircle2 } from "lucide-react";

// 기본 단일 파일 컴포넌트. Tailwind 기반. 필요 시 섹션별 텍스트만 바꿔서 사용하세요.
export default function LandingPage() {
  const [email, setEmail] = useState("");

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-slate-50 text-slate-900">
      {/* NAVBAR */}
      <header className="sticky top-0 z-40 bg-white/70 backdrop-blur border-b border-slate-200">
        <nav className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-sky-600 flex items-center justify-center text-white font-bold">S</div>
            <span className="font-semibold tracking-tight">SongLab</span>
            <span className="ml-2 text-xs text-slate-500">내 목소리 사용설명서</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm">
            <a href="#features" className="hover:text-slate-700">기능</a>
            <a href="#how" className="hover:text-slate-700">사용방법</a>
            <a href="#recommend" className="hover:text-slate-700">추천강의</a>
            <a href="#faq" className="hover:text-slate-700">FAQ</a>
          </div>
          <div className="flex items-center gap-2">
                        <button className="inline-flex items-center gap-2 rounded-xl bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-700">
              무료로 시작
              <ChevronRight className="h-4 w-4"/>
            </button>
          </div>
        </nav>
      </header>

      {/* HERO */}
      <section className="relative">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-16 sm:py-24 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <motion.h1 initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} transition={{duration:0.6}} className="text-3xl sm:text-5xl font-extrabold leading-tight">
              내 목소리 사용설명서
              <span className="block text-sky-600">분석 30초, 결과 즉시</span>
            </motion.h1>
            <p className="mt-4 text-slate-600">스마트폰 20–30초 녹음만 올리면, 밝기·두께·선명도·음압 4축과 브릿지/내전 이슈까지 자동 분석. 당신의 목소리를 위한 유튜브 추천을 바로 제공합니다.</p>

            <div className="mt-6 flex flex-col sm:flex-row gap-3">
              <button className="inline-flex items-center gap-2 rounded-xl bg-sky-600 px-5 py-3 font-semibold text-white hover:bg-sky-700">
                <Mic className="h-5 w-5"/> 내 목소리 분석하기
              </button>
              <button className="inline-flex items-center gap-2 rounded-xl border px-5 py-3 hover:bg-slate-50">
                <Play className="h-5 w-5"/> 데모 보기
              </button>
            </div>
            <div className="mt-4 flex items-center gap-3 text-sm text-slate-500">
              <ShieldCheck className="h-4 w-4"/>
              개인정보 최소 수집, 분석 원본 보호, 1클릭 삭제 지원
            </div>
          </div>

          {/* Score Preview Card */}
          <motion.div initial={{opacity:0, y:20}} animate={{opacity:1, y:0}} transition={{duration:0.6, delay:0.1}} className="relative">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-10 w-10 rounded-xl bg-slate-900 text-white flex items-center justify-center"><Mic className="h-5 w-5"/></div>
                  <div>
                    <p className="text-sm text-slate-500">분석 미리보기</p>
                    <p className="font-semibold">Sample Voice • 27s</p>
                  </div>
                </div>
                <span className="text-xs rounded-full bg-sky-50 text-sky-700 px-3 py-1">v1.0 • Beta</span>
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4">
                {[
                  {name: "밝기", value: +42},
                  {name: "두께", value: -18},
                  {name: "선명도", value: +65},
                  {name: "음압", value: -5},
                ].map((s, i) => (
                  <div key={i} className="rounded-xl border p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-600">{s.name}</span>
                      <Gauge className="h-4 w-4 text-slate-400"/>
                    </div>
                    <div className="mt-2 text-2xl font-bold">{s.value > 0 ? "+" : ""}{s.value}</div>
                    <div className="mt-3 h-2 rounded-full bg-slate-100">
                      <div className={`h-2 rounded-full ${s.value >= 0 ? "bg-sky-500" : "bg-slate-400"}`} style={{width: `${Math.min(Math.abs(s.value),100)}%`}}></div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-xl bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-sm">
                  <BarChart3 className="h-4 w-4 text-slate-400"/>
                  <span className="font-semibold">진단</span>
                </div>
                <ul className="mt-2 text-sm list-disc pl-5 text-slate-600 space-y-1">
                  <li>브릿지 전환 시 약간의 풀림: 내전 유지 훈련 권장</li>
                  <li>음압 저하 구간 존재: 아포지오 호흡 & SOVT 루틴</li>
                  <li>고음 잠재력 중상: 벨팅 가능성, 단계적 피치 상승 권고</li>
                </ul>
              </div>
            </div>
            <div className="absolute -inset-2 -z-10 blur-2xl opacity-30 bg-gradient-to-tr from-sky-200 to-fuchsia-200 rounded-3xl"/>
          </motion.div>
        </div>
      </section>

      {/* TRUST BADGES */}
      <section>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-6">
          <div className="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500">
            <div className="inline-flex items-center gap-2"><Cpu className="h-4 w-4"/> AI 기반 4축 분석</div>            <div className="inline-flex items-center gap-2"><Youtube className="h-4 w-4"/> 외부 강의 큐레이션</div>
            <div className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4"/> 개인정보 최소 수집</div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" className="py-16 sm:py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-2xl sm:text-3xl font-extrabold">핵심 기능</h2>
          <p className="mt-2 text-slate-600">검사부터 훈련까지, 노력을 헛돌지 않게 만드는 최소한의 도구 세트.</p>

          <div className="mt-8 grid md:grid-cols-3 gap-6">
            {[
              {
                icon: <Gauge className="h-5 w-5"/>,
                title: "4축 점수 (±100)",
                desc: "밝기·두께·선명도·음압. 구간별 편차와 안정성까지 함께 계산합니다.",
              },
              {
                icon: <BarChart3 className="h-5 w-5"/>,
                title: "문제유형 진단",
                desc: "브릿지 전환 난이도, 성대 내전 유지, 지름/벨팅 가능성 등 리포트 제공.",
              },
              {
                icon: <Youtube className="h-5 w-5"/>,
                title: "맞춤 강의 추천",
                desc: "점수와 이슈에 맞는 외부 강의 6개를 자동 큐레이션합니다.",
              },
                            {
                icon: <ShieldCheck className="h-5 w-5"/>,
                title: "데이터 보호",
                desc: "원본 비공개 저장, 익명 분석, 1클릭 영구삭제를 기본으로 합니다.",
              },
              {
                icon: <Zap className="h-5 w-5"/>,
                title: "빠른 분석",
                desc: "스마트폰 20–30초만으로 평균 10초 내 리포트 제공.",
              },
            ].map((f, i) => (
              <div key={i} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="h-10 w-10 rounded-xl bg-slate-900 text-white flex items-center justify-center">{f.icon}</div>
                <h3 className="mt-4 font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="py-16 bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-2xl sm:text-3xl font-extrabold">사용 방법</h2>
          <div className="mt-8 grid md:grid-cols-4 gap-6">
            {[
              {step: 1, title: "녹음 업로드", desc: "스마트폰 보이스메모 20–30초. 모노 16kHz 권장."},
              {step: 2, title: "자동분석", desc: "소음·클리핑 체크 후 4축 점수/이슈 산출."},
              {step: 3, title: "리포트 확인", desc: "강점/약점 요약, 브릿지·내전 진단, 그래프 제공."},
              {step: 4, title: "훈련 시작", desc: "추천 유튜브 강의 바로 실행."},
            ].map((s, i) => (
              <div key={i} className="rounded-2xl border bg-slate-50 p-6">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold">{s.step}</div>
                  <h3 className="font-semibold">{s.title}</h3>
                </div>
                <p className="mt-2 text-sm text-slate-600">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* RECOMMENDATIONS */}
      <section id="recommend" className="py-16 sm:py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex items-end justify-between">
            <div>
              <h2 className="text-2xl sm:text-3xl font-extrabold">맞춤 강의 추천</h2>
              <p className="mt-2 text-slate-600">결과에 따라 자동 큐레이션된 외부 강의 6개가 썸네일로 노출됩니다.</p>
            </div>
            <button className="hidden sm:inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm hover:bg-slate-50">
              더 보기 <ChevronRight className="h-4 w-4"/>
            </button>
          </div>


          <div className="mt-8 grid sm:grid-cols-2 md:grid-cols-3 gap-6">
            {Array.from({length:6}).map((_, i) => (
              <div key={i} className="group rounded-2xl border bg-white overflow-hidden shadow-sm hover:shadow-md">
                <div className="aspect-video bg-slate-200 grid place-items-center">
                  <Youtube className="h-10 w-10 text-slate-500 group-hover:scale-105 transition-transform"/>
                </div>
                <div className="p-4">
                  <p className="text-sm text-slate-500">추천 카테고리</p>
                  <h3 className="font-semibold">예: 아포지오 호흡 루틴</h3>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA STRIP */}
      <section className="py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="rounded-2xl border bg-gradient-to-r from-sky-600 to-indigo-600 p-6 sm:p-10 text-white">
            <div className="grid md:grid-cols-2 gap-6 items-center">
              <div>
                <h3 className="text-2xl font-extrabold">지금 바로 내 목소리 분석 시작</h3>
                <p className="mt-2 text-white/80">무료 베타 기간. 30초면 충분합니다.</p>
              </div>
              <div className="flex flex-col sm:flex-row gap-3 justify-end">
                <button className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 font-semibold text-slate-900 hover:bg-slate-100">
                  <Mic className="h-5 w-5"/> 녹음 업로드
                </button>
                              </div>
            </div>
          </div>
        </div>
      </section>

      {/* EMAIL CAPTURE (선택) */}
      <section className="py-12">
        <div className="mx-auto max-w-xl px-4 sm:px-6 text-center">
          <h3 className="text-xl font-bold">업데이트를 이메일로 받아보기</h3>
          <p className="mt-2 text-sm text-slate-600">신규 기능, 베타 초대, 할인 쿠폰을 보내드립니다.</p>
          <div className="mt-4 flex gap-2">
            <input value={email} onChange={(e)=>setEmail(e.target.value)} placeholder="name@email.com" className="flex-1 rounded-xl border px-4 py-3 outline-none focus:ring-2 focus:ring-sky-500"/>
            <button className="rounded-xl bg-slate-900 text-white px-5 py-3 font-semibold">구독</button>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="py-16 bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-2xl sm:text-3xl font-extrabold">자주 묻는 질문</h2>
          <div className="mt-8 grid md:grid-cols-2 gap-6">
            {[
              {q:"분석 정확도는 어느 정도인가요?", a:"스마트폰 기준 환경에서 신호대잡음비·클리핑을 보정해 ±100 스케일로 산출합니다. 동일 조건 반복 측정 안정성을 최우선으로 설계했습니다."},
              {q:"개인정보와 원본 파일은 안전한가요?", a:"원본은 비공개 보관되며 익명화된 특징량만 모델 개선에 사용됩니다. 언제든 1클릭 영구삭제가 가능합니다."},
              {q:"추천 강의는 어떻게 선정되나요?", a:"4축 프로파일과 문제유형 매칭 룰셋을 통해 자동 큐레이션됩니다. 특정 채널 제외 옵션도 지원합니다."},
              {q:"레슨 없이도 효과가 있나요?", a:"기초 체계가 잡히도록 핵심 루틴과 체크포인트를 제공합니다. 이후 코칭과 병행하면 개선 속도가 빨라집니다."},
            ].map((f, i) => (
              <div key={i} className="rounded-2xl border p-6">
                <h3 className="font-semibold">{f.q}</h3>
                <p className="mt-2 text-sm text-slate-600">{f.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-10 border-t bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-xl bg-sky-600 text-white font-bold grid place-items-center">S</div>
                <span className="font-semibold">SongLab</span>
              </div>
              <p className="mt-2 text-xs text-slate-500">© {new Date().getFullYear()} SongLab. All rights reserved.</p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <a className="text-slate-600 hover:text-slate-900" href="#features">기능</a>
              <a className="text-slate-600 hover:text-slate-900" href="#how">사용방법</a>
              <a className="text-slate-600 hover:text-slate-900" href="#recommend">추천강의</a>
              <a className="text-slate-600 hover:text-slate-900" href="#faq">FAQ</a>
            </div>
          </div>
          <div className="mt-6 text-xs text-slate-400 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4"/> Beta 서비스 고지: 본 서비스는 학습·연구 목적의 베타 단계로, 상업적 의사결정에 단독 근거로 사용하지 마세요.
          </div>
        </div>
      </footer>
    </div>
  );
}
