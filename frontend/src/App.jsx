import { useMemo, useState } from 'react'
import './App.css'

const DEFAULT_API_BASE = 'http://localhost:8000'

const toLabel = {
  f1_hz: 'F1 (Hz)',
  f2_hz: 'F2 (Hz)',
  f3_hz: 'F3 (Hz)',
  chest_head_ratio: 'Chest / Head Ratio',
  clarity: 'Clarity',
  power_db: 'Power (dB)',
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '–'
  }
  return Number(value).toFixed(digits)
}

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const apiBase = useMemo(() => {
    const raw = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE
    return raw.replace(/\/$/, '')
  }, [])

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

      const response = await fetch(`${apiBase}/api/analyze`, {
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

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1>SongLab</h1>
          <p className="app__subtitle">AI 기반 목소리 분석과 맞춤형 학습 추천</p>
        </div>
      </header>

      <main className="app__content">
        <section className="panel">
          <h2>1. 음성 파일 업로드</h2>
          <p className="panel__description">
            10초 이상의 모노 음성 파일(WAV/FLAC)을 업로드하면 SongLab이 포먼트, 흉·두성 비율, 명료도,
            파워를 분석하고 맞춤 가이드를 생성합니다.
          </p>

          <form className="upload-form" onSubmit={handleSubmit}>
            <input
              type="file"
              accept="audio/*"
              onChange={handleFileChange}
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading}>
              {isLoading ? '분석 중…' : '분석 시작'}
            </button>
          </form>

          {error ? <p className="panel__error">{error}</p> : null}
          {file ? (
            <p className="panel__hint">
              선택한 파일: <strong>{file.name}</strong>
            </p>
          ) : null}
        </section>

        {result ? (
          <>
            <section className="panel">
              <h2>2. 핵심 발성 지표</h2>
              <div className="metrics-grid">
                {Object.entries(result.metrics || {}).map(([key, value]) => (
                  <article className="metric-card" key={key}>
                    <h3>{toLabel[key] ?? key}</h3>
                    <p className="metric-card__value">{formatNumber(value)}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel">
              <h2>3. SongLab AI 코멘트</h2>
              <div className="interpretation">
                <p>{result.interpretation || '추가 코멘트가 없습니다.'}</p>
              </div>
            </section>

            <section className="panel">
              <h2>4. 추천 강의</h2>
              {result.recommendations && result.recommendations.length > 0 ? (
                <ul className="video-list">
                  {result.recommendations.map((video) => (
                    <li key={video.video_id} className="video-card">
                      <div className="video-card__content">
                        <h3>{video.title}</h3>
                        <p className="video-card__meta">
                          {video.channel} · {new Date(video.published_at).toLocaleDateString()}
                        </p>
                        <p className="video-card__description">{video.description}</p>
                      </div>
                      <a
                        className="video-card__link"
                        href={`https://www.youtube.com/watch?v=${video.video_id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        YouTube에서 보기
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="panel__hint">추천할 영상을 찾지 못했습니다. 다른 발성으로 다시 시도해보세요.</p>
              )}
            </section>
          </>
        ) : null}
      </main>

      <footer className="app__footer">
        <small>SongLab — AI Vocal Lab</small>
      </footer>
    </div>
  )
}

export default App
