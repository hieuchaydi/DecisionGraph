import { useMemo, useState } from 'react'
import type { Locale } from '../types/docs'

type CheckDef = {
  id: string
  label: Record<Locale, string>
  path: string
  method: 'GET' | 'POST'
  body?: Record<string, unknown>
}

type CheckResult = {
  id: string
  label: string
  path: string
  method: 'GET' | 'POST'
  status: 'pass' | 'fail'
  code: number | 'ERR'
  latencyMs: number
  detail: string
}

const CHECKS: CheckDef[] = [
  {
    id: 'health',
    label: { vi: 'Health Check', en: 'Health Check' },
    path: '/health',
    method: 'GET',
  },
  {
    id: 'decisions',
    label: { vi: 'Decisions Listing', en: 'Decisions Listing' },
    path: '/api/decisions?limit=1',
    method: 'GET',
  },
  {
    id: 'query',
    label: { vi: 'Semantic Query', en: 'Semantic Query' },
    path: '/api/query',
    method: 'POST',
    body: { question: 'Why cap payment retries at 2 attempts?' },
  },
  {
    id: 'guardrail',
    label: { vi: 'Guardrail', en: 'Guardrail' },
    path: '/api/guardrail',
    method: 'POST',
    body: { change_request: 'Increase payment retries from 2 to 5', limit: 2 },
  },
  {
    id: 'schema',
    label: { vi: 'Schema Info', en: 'Schema Info' },
    path: '/api/schema/info',
    method: 'GET',
  },
]

const BASE_URL_STORAGE_KEY = 'decisiongraph.docs.base_url'

function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''
  return trimmed.replace(/\/+$/, '')
}

function scoreToLabel(locale: Locale, score: number): string {
  if (score >= 90) return locale === 'vi' ? 'Sẵn sàng cao' : 'High readiness'
  if (score >= 70) return locale === 'vi' ? 'Khá ổn' : 'Mostly healthy'
  if (score >= 40) return locale === 'vi' ? 'Cần rà thêm' : 'Needs attention'
  return locale === 'vi' ? 'Đang có lỗi' : 'Unstable'
}

function formatRuntimeError(locale: Locale, error: unknown): string {
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      return locale === 'vi' ? 'Timeout (8s)' : 'Timeout (8s)'
    }

    return error.message
  }

  return locale === 'vi' ? 'Không rõ lỗi' : 'Unknown error'
}

export function ReadinessConsole({ locale }: { locale: Locale }) {
  const [baseUrl, setBaseUrl] = useState(() => {
    if (typeof window === 'undefined') return 'http://127.0.0.1:8000'
    return localStorage.getItem(BASE_URL_STORAGE_KEY) ?? 'http://127.0.0.1:8000'
  })
  const [apiKey, setApiKey] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [lastRunAt, setLastRunAt] = useState<string | null>(null)
  const [results, setResults] = useState<CheckResult[]>([])

  const passedCount = useMemo(() => results.filter((item) => item.status === 'pass').length, [results])

  const score = useMemo(() => {
    if (!results.length) return 0
    return Math.round((passedCount / results.length) * 100)
  }, [passedCount, results.length])

  async function runChecks() {
    const normalizedBaseUrl = normalizeBaseUrl(baseUrl)
    if (!normalizedBaseUrl) return

    if (typeof window !== 'undefined') {
      localStorage.setItem(BASE_URL_STORAGE_KEY, normalizedBaseUrl)
    }

    setIsRunning(true)

    const nextResults: CheckResult[] = []

    for (const check of CHECKS) {
      const controller = new AbortController()
      const timeout = window.setTimeout(() => controller.abort(), 8000)
      const start = performance.now()

      try {
        const headers: Record<string, string> = {
          Accept: 'application/json',
        }

        if (check.method === 'POST') {
          headers['Content-Type'] = 'application/json'
        }

        if (apiKey.trim()) {
          headers['x-api-key'] = apiKey.trim()
        }

        const response = await fetch(`${normalizedBaseUrl}${check.path}`, {
          method: check.method,
          headers,
          body: check.body ? JSON.stringify(check.body) : undefined,
          signal: controller.signal,
        })

        const latencyMs = Math.round(performance.now() - start)
        const payload = await response
          .clone()
          .json()
          .catch(() => null)

        const ok = response.ok
        let detail = ok
          ? locale === 'vi'
            ? 'Pass'
            : 'Pass'
          : locale === 'vi'
            ? 'HTTP lỗi'
            : 'HTTP error'

        if (!ok) {
          const errorDetail = payload && typeof payload === 'object' && 'detail' in payload ? String(payload.detail) : ''
          detail = errorDetail || detail
        } else if (check.id === 'health' && payload && typeof payload === 'object' && 'mode' in payload) {
          detail = `${locale === 'vi' ? 'mode' : 'mode'}=${String(payload.mode)}`
        }

        nextResults.push({
          id: check.id,
          label: check.label[locale],
          path: check.path,
          method: check.method,
          status: ok ? 'pass' : 'fail',
          code: response.status,
          latencyMs,
          detail,
        })
      } catch (error) {
        const latencyMs = Math.round(performance.now() - start)
        nextResults.push({
          id: check.id,
          label: check.label[locale],
          path: check.path,
          method: check.method,
          status: 'fail',
          code: 'ERR',
          latencyMs,
          detail: formatRuntimeError(locale, error),
        })
      } finally {
        window.clearTimeout(timeout)
      }
    }

    setResults(nextResults)
    setLastRunAt(new Date().toLocaleTimeString())
    setIsRunning(false)
  }

  function resetChecks() {
    setResults([])
    setLastRunAt(null)
  }

  return (
    <section id="live-console" className="card readiness-card">
      <div className="readiness-head">
        <div>
          <h2>{locale === 'vi' ? 'Live Readiness Console' : 'Live Readiness Console'}</h2>
          <p className="summary">
            {locale === 'vi'
              ? 'Chạy check thật với API để đo độ sẵn sàng: status, latency, score.'
              : 'Run real API checks to measure readiness: status, latency, and score.'}
          </p>
        </div>
        <div className="score-pill" data-state={score >= 70 ? 'good' : score >= 40 ? 'warn' : 'bad'}>
          <strong>{score}%</strong>
          <span>{scoreToLabel(locale, score)}</span>
        </div>
      </div>

      <div className="readiness-controls">
        <label>
          <span>{locale === 'vi' ? 'Base URL' : 'Base URL'}</span>
          <input
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
            placeholder="http://127.0.0.1:8000"
            autoComplete="off"
          />
        </label>

        <label>
          <span>{locale === 'vi' ? 'API Key (tuỳ chọn)' : 'API Key (optional)'}</span>
          <input
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="x-api-key"
            autoComplete="off"
          />
        </label>
      </div>

      <div className="readiness-actions">
        <button type="button" onClick={runChecks} disabled={isRunning || !normalizeBaseUrl(baseUrl)}>
          {isRunning ? (locale === 'vi' ? 'Đang kiểm tra...' : 'Running checks...') : locale === 'vi' ? 'Chạy kiểm tra' : 'Run checks'}
        </button>
        <button type="button" className="ghost" onClick={resetChecks} disabled={isRunning || !results.length}>
          {locale === 'vi' ? 'Reset' : 'Reset'}
        </button>
        {lastRunAt ? (
          <p className="last-run">
            {locale === 'vi' ? 'Lần chạy gần nhất:' : 'Last run:'} {lastRunAt}
          </p>
        ) : null}
      </div>

      {results.length ? (
        <div className="readiness-table" role="table" aria-label="Readiness checks">
          <div className="readiness-row readiness-row-head" role="row">
            <span>{locale === 'vi' ? 'Check' : 'Check'}</span>
            <span>{locale === 'vi' ? 'Endpoint' : 'Endpoint'}</span>
            <span>{locale === 'vi' ? 'Kết quả' : 'Result'}</span>
            <span>{locale === 'vi' ? 'Latency' : 'Latency'}</span>
          </div>
          {results.map((result) => (
            <div className="readiness-row" role="row" key={result.id}>
              <span>{result.label}</span>
              <span className="endpoint">{result.method} {result.path}</span>
              <span>
                <em data-state={result.status} className="status-badge">
                  {result.status === 'pass' ? 'PASS' : 'FAIL'} ({result.code})
                </em>
                <small>{result.detail}</small>
              </span>
              <span>{result.latencyMs}ms</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="readiness-hint">
          {locale === 'vi'
            ? 'Gợi ý: mở backend bằng `decisiongraph serve --host 127.0.0.1 --port 8000` rồi bấm “Chạy kiểm tra”.'
            : 'Tip: run backend with `decisiongraph serve --host 127.0.0.1 --port 8000` then click “Run checks”.'}
        </p>
      )}
    </section>
  )
}
