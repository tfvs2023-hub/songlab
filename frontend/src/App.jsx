import { useMemo, useRef, useState } from 'react'
import './App.css'

const DEFAULT_DEV_API_BASE = 'http://localhost:8000'

const sanitizeBaseUrl = (value) => (value ? value.replace(/\/$/, '') : '')

const resolveApiBase = () => {
  const envBase = import.meta.env.VITE_API_BASE_URL
  if (envBase) {
    return sanitizeBaseUrl(envBase)
  }

  if (import.meta.env.DEV) {
    return sanitizeBaseUrl(DEFAULT_DEV_API_BASE)
  }

  if (typeof window !== 'undefined') {
    return sanitizeBaseUrl(window.location.origin)
  }

  return ''
}

const PLACEHOLDER_THUMB = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="480" height="270" viewBox="0 0 480 270"><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="%23c7d2fe"/><stop offset="100%" stop-color="%23e0e7ff"/></linearGradient></defs><rect fill="url(%23grad)" width="480" height="270"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%235267d9" font-family="Inter, sans-serif" font-size="32">SongLab</text></svg>'

const HERO_METRIC_CONFIG = [
  {
    id: 'brightness',
    label: '밝기',
    minLabel: '어두움',
    maxLabel: '밝음',
    metricKey: 'f2_hz',
    minValue: 400,
    maxValue: 2800,
    formatter: (value) => `${Math.round(value)} Hz`,
    negativeCode: 'D',
    positiveCode: 'B',
  },
  {
    id: 'thickness',
    label: '두께',
    minLabel: '얇음',
    maxLabel: '두꺼움',
    metricKey: 'chest_head_ratio',
    minValue: 0.5,
    maxValue: 3.5,
    formatter: (value) => value.toFixed(2),
    negativeCode: 'L',
    positiveCode: 'T',
  },
  {
    id: 'clarity',
    label: '선명도',
    minLabel: '에어리',
    maxLabel: '클린',
    metricKey: 'clarity',
    minValue: 0,
    maxValue: 1,
    formatter: (value) => `${Math.round(value * 100)}%`,
    negativeCode: 'A',
    positiveCode: 'C',
  },
  {
    id: 'power',
    label: '파워',
    minLabel: '소프트',
    maxLabel: '에너지',
    metricKey: 'power_db',
    minValue: -60,
    maxValue: 10,
    formatter: (value) => `${value.toFixed(1)} dB`,
    negativeCode: 'S',
    positiveCode: 'P',
  },
]

const SAMPLE_RESULT = {
  metrics: {
    f0_mean_hz: 348,
    f0_median_hz: 342,
    f1_hz: 520,
    f2_hz: 1890,
    f3_hz: 2680,
    chest_head_ratio: 1.42,
    clarity: 0.68,
    power_db: -11.7,
  },
  interpretation:
    '고음역으로 갈수록 공명은 안정적으로 유지되고 있으며, 흉성과 두성의 비율도 균형에 가깝습니다. 고음 구간에서 지나친 성대 압박이 느껴지므로 호흡을 더 넓게 쓰면서 공명 위치를 고정해 보세요.',
  recommendations: [
    {
      video_id: 'aW1rLuHBmNo',
      title: 'How to Sing for Beginners',
      channel: 'New York Vocal Coaching',
      description: '기초 보컬 메커니즘과 워밍업 루틴을 정리한 20분 가이드.',
      published_at: '2023-09-18T00:00:00Z',
    },
    {
      video_id: 'G5aH6UJ1vI0',
      title: 'Mixed Voice Balance Workout',
      channel: 'Tristan Paredes',
      description: '믹스 보이스 밸런스를 위한 단계별 연습 세트.',
      published_at: '2024-02-05T00:00:00Z',
    },
    {
      video_id: 'gkV6glbexMA',
      title: 'Resonance Training for Clear Tone',
      channel: 'Madeleine Harvey',
      description: '명료도를 높이는 공명 포커싱 훈련.',
      published_at: '2024-04-22T00:00:00Z',
    },
    {
      video_id: '-p4qZiGLYuk',
      title: 'Breath Support Exercise Set',
      channel: "Jacob\'s Vocal Academy",
      description: '흉성 지지와 호흡 제어를 강화하는 루틴.',
      published_at: '2022-11-14T00:00:00Z',
    },
    {
      video_id: 'Hwx1S69GOrU',
      title: 'Powerful Belting without Strain',
      channel: "Dr. Dan\'s Voice Essentials",
      description: '벨팅 시 압박을 줄이면서 파워를 유지하는 방법.',
      published_at: '2021-07-08T00:00:00Z',
    },
    {
      video_id: 'ARpS9Q8Y1EI',
      title: 'Daily Vocal Warm-Up for All Ranges',
      channel: 'Justin Stoney',
      description: '전 음역을 커버하는 15분 데일리 워밍업.',
      published_at: '2024-01-27T00:00:00Z',
    },
  ],
}

const toLabel = {
  f0_mean_hz: '평균 음정 (Hz)',
  f0_median_hz: '중앙 음정 (Hz)',
  f1_hz: 'F1 (Hz)',
  f2_hz: 'F2 (Hz)',
  f3_hz: 'F3 (Hz)',
  chest_head_ratio: 'Chest / Head Ratio',
  clarity: 'Clarity',
  power_db: 'Power (dB)',
}

const clampValue = (value, min, max) => {
  if (!Number.isFinite(value)) {
    return (min + max) / 2
  }
  return Math.min(Math.max(value, min), max)
}

const clampScore = (value) => {
  if (!Number.isFinite(value)) {
    return 0
  }
  return Math.min(Math.max(value, -100), 100)
}

const formatScore = (score) => (score > 0 ? `+${score}` : `${score}`)
const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

const hzToNote = (hz) => {
  if (!Number.isFinite(hz) || hz <= 0) {
    return '–'
  }
  const noteNumber = Math.round(12 * Math.log2(hz / 440) + 69)
  const octave = Math.floor(noteNumber / 12) - 1
  const noteIndex = ((noteNumber % 12) + 12) % 12
  const name = NOTE_NAMES[noteIndex]
  return `${name}${octave}`
}

const shiftPitch = (hz, semitone) => {
  if (!Number.isFinite(hz) || hz <= 0) {
    return Number.NaN
  }
  return hz * 2 ** (semitone / 12)
}

const formatPitchRange = (centerHz, lowerSemitone, upperSemitone) => {
  if (!Number.isFinite(centerHz) || centerHz <= 0) {
    return null
  }
  const lowerHz = shiftPitch(centerHz, lowerSemitone)
  const upperHz = shiftPitch(centerHz, upperSemitone)
  if (!Number.isFinite(lowerHz) || !Number.isFinite(upperHz)) {
    return null
  }
  return `${hzToNote(lowerHz)} ~ ${hzToNote(upperHz)}`
}

const derivePitchZones = (metrics) => {
  const fallback = '데이터를 준비 중입니다.'
  if (!metrics) {
    return {
      stability: fallback,
      practice: fallback,
    }
  }

  const median = metrics.f0_median_hz
  const ratio = metrics.chest_head_ratio
  const clarity = metrics.clarity

  const stabilityRange = formatPitchRange(median, -2, 2)

  let practiceCenter = median
  let lowerSpread = -2
  let upperSpread = 2

  if (Number.isFinite(ratio) && ratio < 1.1) {
    practiceCenter = shiftPitch(median, 3)
    lowerSpread = -1
    upperSpread = 5
  } else if (Number.isFinite(ratio) && ratio > 2.5) {
    practiceCenter = shiftPitch(median, -3)
    lowerSpread = -5
    upperSpread = 1
  } else if (Number.isFinite(clarity) && clarity < 0.45) {
    practiceCenter = median
    lowerSpread = -1
    upperSpread = 3
  }

  const practiceRange = formatPitchRange(practiceCenter, lowerSpread, upperSpread)

  return {
    stability: stabilityRange ?? fallback,
    practice: practiceRange ?? fallback,
  }
}

const buildHeroMetrics = (metrics) => {
  return HERO_METRIC_CONFIG.map((config) => {
    const rawValue = metrics?.[config.metricKey]
    const fallback = (config.minValue + config.maxValue) / 2
    const baseValue = Number.isFinite(rawValue) ? rawValue : fallback
    const value = clampValue(baseValue, config.minValue, config.maxValue)
    const percent = ((value - config.minValue) / (config.maxValue - config.minValue)) * 100
    const midPoint = (config.minValue + config.maxValue) / 2
    const halfRange = (config.maxValue - config.minValue) / 2
    const rawScore = ((value - midPoint) / halfRange) * 100
    const score = Math.round(clampScore(rawScore))
    const position = (score + 100) / 2

    return {
      ...config,
      rawValue: value,
      displayValue: config.formatter ? config.formatter(value) : value.toFixed(2),
      percent: Math.round(percent),
      score,
      position,
    }
  })
}

const deriveVocalCode = (metrics) => {
  if (!metrics?.length) {
    return 'NNNN'
  }
  return metrics
    .map((metric) => (metric.score >= 0 ? metric.positiveCode : metric.negativeCode))
    .join('')
}

const buildInterpretationSegments = (text) => {
  const fallback = '데이터를 준비 중입니다.'
  if (!text) {
    return {
      tone: fallback,
      strength: fallback,
      caution: fallback,
      routine: fallback,
      insight: fallback,
    }
  }

  const sentences = text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .flatMap((line) => line.split(/(?<=\.)\s+/))
    .map((line) => line.replace(/^[-•]\s*/, '').trim())
    .filter(Boolean)

  return {
    tone: sentences[0] ?? fallback,
    strength: sentences[1] ?? sentences[0] ?? fallback,
    caution: sentences[2] ?? fallback,
    routine: sentences[3] ?? sentences[2] ?? fallback,
    insight: text.trim(),
  }
}



const ScoreCard = ({ metric, variant = 'default' }) => {
  const position = Math.min(Math.max(metric.position, 0), 100)

  return (
    <article className={`score-card score-card--${variant}`}>
      <div className="score-card__header">
        <span className="score-card__label">{metric.label}</span>
        <span className="score-card__score">{formatScore(metric.score)}</span>
      </div>
      <p className="score-card__value">{metric.displayValue}</p>
      <div className="score-card__scale">
        <span>{metric.minLabel}</span>
        <span>{metric.maxLabel}</span>
      </div>
      <div className="score-card__bar">
        <div className="score-card__zero" />
        <div className="score-card__indicator" style={{ left: `${position}%` }} />
      </div>
      <div className="score-card__axis">
        <span>-100</span>
        <span>0</span>
        <span>+100</span>
      </div>
    </article>
  )
}

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  const apiBase = useMemo(resolveApiBase, [])
  const heroMetrics = useMemo(() => buildHeroMetrics(result?.metrics ?? SAMPLE_RESULT.metrics), [result])
  const analysisMetrics = useMemo(() => (result?.metrics ? buildHeroMetrics(result.metrics) : []), [result])
  const vocalCode = useMemo(() => deriveVocalCode(analysisMetrics), [analysisMetrics])
  const interpretationSegments = useMemo(
    () => buildInterpretationSegments(result?.interpretation),
    [result?.interpretation],
  )
  const pitchZones = useMemo(() => derivePitchZones(result?.metrics), [result?.metrics])
  const limitedRecommendations = useMemo(
    () => (result?.recommendations ? result.recommendations.slice(0, 6) : []),
    [result?.recommendations],
  )
  const topRecommendation = limitedRecommendations[0]
  const hasRecommendations = limitedRecommendations.length > 0

  const handleFileChange = (event) => {
    const selected = event.target.files?.[0]
    setFile(selected || null)
    setResult(null)
    setError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!file) {
      setError('먼저 분석할 음성 파일을 선택해주세요.')
      return
    }

    setIsLoading(true)
    setError('')
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const endpoint = apiBase ? `${apiBase}/api/analyze` : '/api/analyze'
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const message = await response.text()
        throw new Error(message || '분석 요청이 실패했습니다.')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message || '알 수 없는 오류가 발생했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSample = () => {
    setResult(SAMPLE_RESULT)
    setError('')
  }

  const handleReset = () => {
    setResult(null)
    setFile(null)
    setError('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleShare = async () => {
    const summaryText = `SongLab Vocal MBTI - ${vocalCode}\n${interpretationSegments.insight}`

    try {
      if (typeof navigator !== 'undefined' && navigator.share) {
        await navigator.share({
          title: 'SongLab Vocal MBTI',
          text: summaryText,
          url: typeof window !== 'undefined' ? window.location.href : undefined,
        })
        return
      }
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(summaryText)
        window.alert('요약을 클립보드에 복사했습니다.')
        return
      }
    } catch (shareError) {
      console.error('공유에 실패했습니다.', shareError)
    }
    window.alert('현재 브라우저에서 공유 기능을 지원하지 않습니다.')
  }

  return (
    <div className="app">
      <div className="app__glow" />

      <header className="app__nav">
        <div className="brand">
          <div className="brand__mark">SL</div>
          <div>
            <strong>SongLab</strong>
            <span>VOCAL MBTI STUDIO</span>
          </div>
        </div>
        <nav className="nav-links">
          <a href="#features">보컬 MBTI</a>
          <a href="#insights">기능</a>
          <a href="#process">프로세스</a>
        </nav>
        <div className="nav-actions">
          <button type="button" className="btn btn-ghost" onClick={handleSample}>
            샘플 결과 보기
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
          >
            {isLoading ? '업로드 중…' : '무료 분석 시작'}
          </button>
        </div>
      </header>

      <main className="app__hero">
        <section className="hero__content">
          <span className="hero__badge">MBTI Inspired Voice Intelligence</span>
          <h1 className="hero__title">내 목소리 사용설명서</h1>
          <p className="hero__headline">SongLab</p>
          <p className="hero__copy">
            20초만 업로드하면 목소리의 특징을 분석해 맞춤형 유튜브 강의를 추천합니다.
          </p>

          <form className="hero__form" onSubmit={handleSubmit}>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              onChange={handleFileChange}
              className="hero__file-input"
            />
            <div className="hero__cta">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
              >
                내 음성 업로드
              </button>
              <button
                type="submit"
                className="btn btn-secondary"
                disabled={isLoading || !file}
              >
                {isLoading ? '분석 중…' : '분석 시작'}
              </button>
            </div>
            {error ? <p className="hero__error">{error}</p> : null}
            {file ? (
              <p className="hero__hint">
                선택한 파일: <strong>{file.name}</strong>
              </p>
            ) : null}
          </form>

          <ul className="hero__stats">
            <li><strong>16가지</strong> MBTI 보이스 타입</li>
            <li><strong>4대 핵심 지표</strong> 실시간 추적</li>
            <li><strong>30초</strong> 이내 인사이트 생성</li>
          </ul>
        </section>

        <section className="hero__panel">
          <div className="hero-panel__header">
            <span className="hero-panel__eyebrow">AI가 감지한 오늘의 보이스 스펙트럼</span>
            <p>샘플 음원의 평균값을 기반으로 MBTI 축을 실시간 그려줍니다.</p>
          </div>
          <div className="score-grid">
            {heroMetrics.map((metric) => (
              <ScoreCard key={metric.id} metric={metric} variant="hero" />
            ))}
          </div>
          <footer className="hero-panel__footer">무료 분석 · AI 기반 유튜브 추천 강의 제공 · 보컬 루틴 설계</footer>
        </section>
      </main>

      {result ? (
        <section className="analysis" id="insights">
          <article className="analysis-card analysis-card--hero" id="features">
            <div>
              <span className="analysis-card__badge">SongLab</span>
              <h2>SongLab Vocal MBTI</h2>
              <p>분석이 완료되면 상세한 설명이 표시됩니다.</p>
            </div>
            <span className="analysis-card__code">{vocalCode}</span>
          </article>

          <article className="analysis-card analysis-card--metrics">
            <div className="score-grid score-grid--analysis">
              {analysisMetrics.map((metric) => (
                <ScoreCard key={metric.id} metric={metric} variant="analysis" />
              ))}
            </div>
          </article>

          <article className="analysis-card analysis-card--ranges">
            <div>
              <h3>현재 안정 구간</h3>
              <p>{pitchZones.stability}</p>
            </div>
            <div>
              <h3>권장 연습 구간</h3>
              <p>{pitchZones.practice}</p>
            </div>
          </article>

          <div className="analysis-pill-grid" id="process">
            {[
              { title: '톤 특징', body: interpretationSegments.tone },
              { title: '강점', body: interpretationSegments.strength },
              { title: '주의할 점', body: interpretationSegments.caution },
              { title: '연습 루틴', body: interpretationSegments.routine },
            ].map((item) => (
              <article className="analysis-pill" key={item.title}>
                <h4>{item.title}</h4>
                <p>{item.body}</p>
              </article>
            ))}
          </div>

          <article className="analysis-card analysis-card--videos" id="videos">
            <div className="analysis-card__body">
              <h3>추천 강의</h3>
              <p>SongLab이 선택한 학습 영상을 확인해 보세요.</p>
            </div>
            {hasRecommendations ? (
              <div className="recommendation-grid">
                {limitedRecommendations.map((video) => {
                  const thumbnail = `https://i.ytimg.com/vi/${video.video_id}/hqdefault.jpg`
                  const publishedLabel = video.published_at
                    ? new Date(video.published_at).toLocaleDateString()
                    : ''

                  return (
                    <a
                      className="recommendation-grid__item"
                      key={video.video_id || video.title}
                      href={`https://www.youtube.com/watch?v=${video.video_id}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <div className="recommendation-grid__thumb">
                        <img
                          src={thumbnail}
                          alt={video.title}
                          loading="lazy"
                          onError={(event) => {
                            event.currentTarget.onerror = null
                            event.currentTarget.src = PLACEHOLDER_THUMB
                          }}
                        />
                      </div>
                      <div className="recommendation-grid__info">
                        <h4>{video.title}</h4>
                        <span className="recommendation-grid__channel">{video.channel}</span>
                        {publishedLabel ? (
                          <time dateTime={video.published_at}>{publishedLabel}</time>
                        ) : null}
                      </div>
                    </a>
                  )
                })}
              </div>
            ) : (
              <p className="analysis-card__placeholder">추천할 영상을 찾지 못했습니다. 다른 음성으로 다시 분석해보세요.</p>
            )}
          </article>

          <article className="analysis-card analysis-card--insight">
            <div className="analysis-card__body">
              <h3>추천 인사이트</h3>
              <p>{interpretationSegments.insight}</p>
            </div>
            {topRecommendation ? (
              <div className="insight-cta">
                <div className="insight-cta__text">
                  <span className="insight-cta__label">추천 강의</span>
                  <strong>{topRecommendation.title}</strong>
                  <span className="insight-cta__meta">{topRecommendation.channel}</span>
                </div>
                <a
                  className="btn btn-secondary"
                  href={`https://www.youtube.com/watch?v=${topRecommendation.video_id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  추천 강의로 이동
                </a>
              </div>
            ) : null}
          </article>

          <div className="analysis-actions">
            <button type="button" className="btn btn-ghost" onClick={handleShare}>
              결과 공유
            </button>
            <button type="button" className="btn btn-primary" onClick={handleReset}>
              다시 분석하기
            </button>
          </div>
        </section>
      ) : null}

      <footer className="app__footer">© {new Date().getFullYear()} SongLab — AI Vocal Lab</footer>
    </div>
  )
}

export default App










