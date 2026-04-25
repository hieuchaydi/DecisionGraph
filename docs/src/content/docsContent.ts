import type { DocSection, Locale } from '../types/docs'

export const HERO_TEXT: Record<Locale, { title: string; subtitle: string }> = {
  vi: {
    title: 'Engineering Decision Memory',
    subtitle:
      'DecisionGraph lưu lại bối cảnh, trade-off, quyết định và giả định để team trả lời được câu hỏi “vì sao hệ thống như hiện tại”.',
  },
  en: {
    title: 'Engineering Decision Memory',
    subtitle:
      'DecisionGraph preserves context, trade-offs, decisions, and assumptions so teams can answer the most important question: why the system looks this way.',
  },
}

export const HERO_CHIPS: Record<Locale, string[]> = {
  vi: ['CLI + API + MCP', 'Bilingual Docs (VI/EN)', 'Responsive: Mobile + Desktop', 'Verified: 2026-04-25'],
  en: ['CLI + API + MCP', 'Bilingual Docs (VI/EN)', 'Responsive: Mobile + Desktop', 'Verified: 2026-04-25'],
}

export const DOC_SECTIONS: DocSection[] = [
  {
    id: 'overview',
    title: { vi: 'Overview', en: 'Overview' },
    summary: {
      vi: 'DecisionGraph tập trung vào decision memory: không chỉ biết code thay đổi gì, mà biết vì sao thay đổi.',
      en: 'DecisionGraph is built for decision memory: not only what changed in code, but why it changed.',
    },
    bullets: {
      vi: [
        'Lưu quyết định từ PR, issue, incident, docs, commit và dữ liệu tích hợp.',
        'Truy vấn ngữ nghĩa để trả lời why/who/when/what-changed nhanh hơn.',
        'Dùng guardrail để giảm rủi ro thay đổi sai khi thiếu context lịch sử.',
      ],
      en: [
        'Stores decisions from PRs, issues, incidents, docs, commits, and integration feeds.',
        'Supports semantic why/who/when/what-changed queries for faster answers.',
        'Uses guardrails to reduce risky changes caused by missing historical context.',
      ],
    },
  },
  {
    id: 'when-to-use',
    title: { vi: 'When To Use', en: 'When To Use' },
    summary: {
      vi: 'Các tình huống phù hợp để áp dụng DecisionGraph trong team engineering.',
      en: 'Typical situations where DecisionGraph is valuable for engineering teams.',
    },
    bullets: {
      vi: [
        'Onboarding dev mới: hiểu nhanh lý do kiến trúc và các quyết định nhạy cảm.',
        'Incident review: truy ngược assumption và risk đã được chấp nhận trước đó.',
        'AI-assisted coding: bổ sung context để model không đề xuất ngược quyết định cũ.',
        'Release planning: rà contradiction/stale assumptions trước khi rollout.',
      ],
      en: [
        'New developer onboarding: understand architecture rationale quickly.',
        'Incident review: trace assumptions and accepted risks from prior decisions.',
        'AI-assisted coding: inject context so models avoid reversing prior decisions.',
        'Release planning: check contradictions and stale assumptions before rollout.',
      ],
    },
  },
  {
    id: 'architecture',
    title: { vi: 'Architecture', en: 'Architecture' },
    summary: {
      vi: 'Thiết kế tách lớp để dễ mở rộng và giữ bề mặt tích hợp ổn định.',
      en: 'Layered design to keep interfaces stable while scaling features.',
    },
    bullets: {
      vi: [
        'Core: models + extractor + store + service (trung tâm xử lý decision reasoning).',
        'Surfaces: CLI (automation), API (web/service), MCP (agent tooling).',
        'Insights/Ops/Strategy: lớp mở rộng cho đánh giá chất lượng và vận hành.',
      ],
      en: [
        'Core: models + extractor + store + service as reasoning backbone.',
        'Surfaces: CLI (automation), API (web/service), MCP (agent tooling).',
        'Insights/Ops/Strategy: extension layer for quality and operations.',
      ],
    },
  },
  {
    id: 'quickstart',
    title: { vi: 'Quickstart', en: 'Quickstart' },
    summary: {
      vi: 'Luồng chạy tối thiểu cho backend, docs web, và MCP server.',
      en: 'Minimal startup flow for backend, docs frontend, and MCP server.',
    },
    code: [
      '# 1) Install backend',
      'python -m pip install -e ".[dev]"',
      '',
      '# 2) Seed data',
      'decisiongraph init --reset',
      'decisiongraph seed-demo',
      '',
      '# 3) Run API server',
      'decisiongraph serve --host 127.0.0.1 --port 8000',
      '',
      '# 4) Run docs frontend',
      'cd docs',
      'npm install',
      'npm run dev',
      '',
      '# 5) Run MCP server',
      'decisiongraph mcp',
    ].join('\n'),
  },
  {
    id: 'env-setup',
    title: { vi: 'Env Setup (.env)', en: 'Env Setup (.env)' },
    summary: {
      vi: 'Thiết lập biến môi trường từ `.env.example` để chạy local/CI đúng chuẩn.',
      en: 'Set environment variables from `.env.example` for consistent local/CI runs.',
    },
    bullets: {
      vi: [
        'Bước 1: tạo file `.env` từ `.env.example`.',
        'Bước 2: chỉnh giá trị theo môi trường (đặc biệt token và CORS).',
        'Bước 3: restart terminal/server sau khi đổi `.env`.',
        'Không commit `.env` thật lên git, chỉ commit `.env.example`.',
      ],
      en: [
        'Step 1: create `.env` from `.env.example`.',
        'Step 2: adjust values for your environment (especially token and CORS).',
        'Step 3: restart terminal/server after `.env` changes.',
        'Never commit real `.env` secrets; only commit `.env.example`.',
      ],
    },
    code: [
      '# Windows (PowerShell)',
      'Copy-Item .env.example .env',
      '',
      '# Windows (Command Prompt / cmd)',
      'copy .env.example .env',
      '',
      '# macOS/Linux',
      'cp .env.example .env',
      '',
      '# Example .env',
      'DECISIONGRAPH_ENV=development',
      'DECISIONGRAPH_DATA_PATH=data/decisiongraph.json',
      '# DECISIONGRAPH_API_TOKEN=change-me',
      '# DECISIONGRAPH_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:5173',
      '# DECISIONGRAPH_GITHUB_TOKEN=ghp_xxx',
      '# DECISIONGRAPH_GITHUB_BASE_URL=https://api.github.com',
      '# GROQ_API_KEY=gsk_xxx',
      '# GROQ_MODELS=llama-3.3-70b-versatile,llama-3.1-8b-instant',
    ].join('\n'),
  },
  {
    id: 'readiness-lab',
    title: { vi: 'Readiness Lab', en: 'Readiness Lab' },
    summary: {
      vi: 'Tính năng nổi bật: Live Readiness Console để chạy kiểm tra trực tiếp từ docs UI.',
      en: 'Standout feature: Live Readiness Console that runs real checks directly from the docs UI.',
    },
    bullets: {
      vi: [
        'Chạy nhiều endpoint quan trọng: health, decisions, query, guardrail, schema.',
        'Đo latency từng check và tính readiness score tổng quan.',
        'Hiển thị FAIL detail để xử lý nhanh trong quá trình demo hoặc release check.',
      ],
      en: [
        'Runs key endpoints: health, decisions, query, guardrail, schema.',
        'Measures per-check latency and computes an overall readiness score.',
        'Shows FAIL details for faster debugging during demos or release checks.',
      ],
    },
  },
  {
    id: 'project-structure',
    title: { vi: 'Project Structure', en: 'Project Structure' },
    summary: {
      vi: 'Các thư mục chính và vai trò tương ứng.',
      en: 'Main directories and their responsibilities.',
    },
    code: [
      'DecisionGraph/',
      '  src/decisiongraph/          # core backend package',
      '    cli_commands/             # CLI modules by domain',
      '    api_routes/               # API routers by domain',
      '    mcp_toolsets/             # MCP tools grouped by concern',
      '  docs/                       # React + TS + Vite docs frontend',
      '  tests/                      # backend test suite',
      '  data/                       # local decision store',
      '  temp_smoke/                 # smoke run outputs',
    ].join('\n'),
  },
  {
    id: 'cli-reference',
    title: { vi: 'CLI Reference', en: 'CLI Reference' },
    summary: {
      vi: 'Nhóm lệnh CLI quan trọng dùng hàng ngày.',
      en: 'High-impact CLI command groups used daily.',
    },
    bullets: {
      vi: [
        'Core: init, seed-demo, query, list, get, guardrail, contradictions, stale-assumptions.',
        'Ingestion: ingest, ingest-dir, ingest-git, ingest-jsonl, ingest-github, ingest-slack-export, ingest-jira-json.',
        'Insights: scenarios, kpi, eval-dataset, research-score, research-script, design-partner-progress.',
        'Ops/Strategy: strategy-*, doctor, runbook, release-check, security-audit, schema-info.',
      ],
      en: [
        'Core: init, seed-demo, query, list, get, guardrail, contradictions, stale-assumptions.',
        'Ingestion: ingest, ingest-dir, ingest-git, ingest-jsonl, ingest-github, ingest-slack-export, ingest-jira-json.',
        'Insights: scenarios, kpi, eval-dataset, research-score, research-script, design-partner-progress.',
        'Ops/Strategy: strategy-*, doctor, runbook, release-check, security-audit, schema-info.',
      ],
    },
  },
  {
    id: 'cli-cmd',
    title: { vi: 'CLI (Windows CMD)', en: 'CLI (Windows CMD)' },
    summary: {
      vi: 'Lệnh CLI dành cho Command Prompt (`cmd`) để chạy nhanh mà không cần web UI.',
      en: 'CLI commands for Command Prompt (`cmd`) users who prefer terminal-only workflows.',
    },
    code: [
      'REM Install + init',
      'py -m pip install -e ".[dev]"',
      'decisiongraph init --reset',
      'decisiongraph seed-demo',
      '',
      'REM Interactive CLI',
      'decisiongraph chat',
      '',
      'REM Non-interactive examples',
      'decisiongraph list --limit 10',
      'decisiongraph query "Why did we cap payment retries at 2?"',
      'decisiongraph guardrail "Increase payment retries from 2 to 5"',
      '',
      'REM If decisiongraph is not in PATH',
      'py -m decisiongraph list',
      'py -m decisiongraph query "Why did we cap payment retries at 2?"',
    ].join('\n'),
  },
  {
    id: 'api-reference',
    title: { vi: 'API Reference', en: 'API Reference' },
    summary: {
      vi: 'Nhóm endpoint chính theo chức năng.',
      en: 'Primary endpoint groups by capability.',
    },
    bullets: {
      vi: [
        'System: /health, /api/report/summary, /.',
        'Decision: /api/decisions, /api/query, /api/guardrail, /api/contradictions, /api/assumptions/stale, /api/metrics, /api/graph.',
        'Ingestion: /api/ingest/* (directory, git, jsonl, github, slack-export, jira-json).',
        'Intelligence: /api/scenarios/run, /api/kpi/snapshot, /api/eval/dataset, /api/research/*, /api/strategy/*, /api/ops/*, /api/schema/info.',
      ],
      en: [
        'System: /health, /api/report/summary, /.',
        'Decision: /api/decisions, /api/query, /api/guardrail, /api/contradictions, /api/assumptions/stale, /api/metrics, /api/graph.',
        'Ingestion: /api/ingest/* (directory, git, jsonl, github, slack-export, jira-json).',
        'Intelligence: /api/scenarios/run, /api/kpi/snapshot, /api/eval/dataset, /api/research/*, /api/strategy/*, /api/ops/*, /api/schema/info.',
      ],
    },
  },
  {
    id: 'mcp-reference',
    title: { vi: 'MCP Reference', en: 'MCP Reference' },
    summary: {
      vi: 'Tooling cho agent, đã tách theo nhóm để dễ mở rộng.',
      en: 'Agent tooling grouped by domain for easier extension.',
    },
    bullets: {
      vi: [
        'Core tools: query/list/guardrail/contradictions/stale/metric/graph/report.',
        'Ingestion tools: git/jsonl/github/slack/jira.',
        'Insights tools: scenarios/kpi/eval/research scorecard/interview/design partner progress.',
        'Strategy & Ops tools: strategy sections/search + doctor/runbook/release/security/schema.',
      ],
      en: [
        'Core tools: query/list/guardrail/contradictions/stale/metric/graph/report.',
        'Ingestion tools: git/jsonl/github/slack/jira.',
        'Insights tools: scenarios/kpi/eval/research scorecard/interview/design partner progress.',
        'Strategy & Ops tools: strategy sections/search + doctor/runbook/release/security/schema.',
      ],
    },
  },
  {
    id: 'env-config',
    title: { vi: 'Environment Config', en: 'Environment Config' },
    summary: {
      vi: 'Biến môi trường thường dùng khi chạy local/CI.',
      en: 'Common environment variables for local and CI runs.',
    },
    bullets: {
      vi: [
        'DECISIONGRAPH_ENV: chọn môi trường (development/staging/production).',
        'DECISIONGRAPH_DATA_PATH: đổi vị trí file data store.',
        'DECISIONGRAPH_API_TOKEN: bật bảo vệ API bằng x-api-key.',
        'DECISIONGRAPH_CORS_ORIGINS: cấu hình CORS cho frontend domain.',
        'DECISIONGRAPH_GITHUB_TOKEN / DECISIONGRAPH_GITHUB_BASE_URL: ingest GitHub API.',
        'GROQ_API_KEY / GROQ_MODELS: cấu hình model Groq cho luồng AI (nếu tích hợp).',
      ],
      en: [
        'DECISIONGRAPH_ENV: runtime environment (development/staging/production).',
        'DECISIONGRAPH_DATA_PATH: override local data store path.',
        'DECISIONGRAPH_API_TOKEN: enable API protection via x-api-key.',
        'DECISIONGRAPH_CORS_ORIGINS: configure CORS for frontend domains.',
        'DECISIONGRAPH_GITHUB_TOKEN / DECISIONGRAPH_GITHUB_BASE_URL: enable GitHub ingestion.',
        'GROQ_API_KEY / GROQ_MODELS: configure Groq model access for AI integrations.',
      ],
    },
  },
  {
    id: 'prompt-playbook',
    title: { vi: 'Prompt Playbook', en: 'Prompt Playbook' },
    summary: {
      vi: 'Mẫu prompt chuẩn để giao việc theo 3 vòng mà không lệch format.',
      en: 'Canonical prompt template for three-round delivery with consistent formatting.',
    },
    codeLocalized: {
      vi: [
        '1) Vòng 1: hoàn thiện core reasoning + test.',
        '2) Vòng 2: hoàn thiện connector + API/CLI/MCP.',
        '3) Vòng 3: hoàn thiện insights + ops + docs.',
        'Yêu cầu: tài liệu song ngữ Việt/Anh, responsive UI, không phá backward compatibility.',
      ].join('\n'),
      en: [
        '1) Round 1: finish core reasoning + tests.',
        '2) Round 2: finish connectors + API/CLI/MCP.',
        '3) Round 3: finish insights + ops + docs.',
        'Requirements: bilingual VI/EN docs, responsive UI, no backward compatibility breaks.',
      ].join('\n'),
    },
  },
  {
    id: 'flow-validation',
    title: { vi: 'Flow Validation', en: 'Flow Validation' },
    summary: {
      vi: 'Luồng đã được rà nhiều lượt để đồng bộ code và tài liệu.',
      en: 'Flows are verified in multiple passes to keep docs and runtime aligned.',
    },
    bullets: {
      vi: [
        'Quality pass: pytest 24/24 pass, docs lint pass, docs build pass.',
        'CLI pass: init -> seed-demo -> list/query/guardrail chạy đúng.',
        'API pass: health/decisions/query/guardrail trả về 200.',
        'MCP pass: list_tools = 28.',
      ],
      en: [
        'Quality pass: pytest 24/24 passed, docs lint passed, docs build passed.',
        'CLI pass: init -> seed-demo -> list/query/guardrail executed successfully.',
        'API pass: health/decisions/query/guardrail returned 200.',
        'MCP pass: list_tools = 28.',
      ],
    },
  },
  {
    id: 'troubleshooting',
    title: { vi: 'Troubleshooting', en: 'Troubleshooting' },
    summary: {
      vi: 'Sự cố thường gặp và cách xử lý nhanh.',
      en: 'Frequent issues and fast fixes.',
    },
    bullets: {
      vi: [
        'Lỗi ModuleNotFoundError: chạy lại `python -m pip install -e ".[dev]"`.',
        'API 401: kiểm tra `DECISIONGRAPH_API_TOKEN` và header `x-api-key`.',
        'Lỗi CORS trên frontend: cấu hình `DECISIONGRAPH_CORS_ORIGINS` đúng domain.',
        'Docs build fail: xóa `node_modules`, chạy lại `npm install` và `npm run build`.',
      ],
      en: [
        'ModuleNotFoundError: rerun `python -m pip install -e ".[dev]"`.',
        'API 401: verify `DECISIONGRAPH_API_TOKEN` and `x-api-key` header.',
        'Frontend CORS issue: configure `DECISIONGRAPH_CORS_ORIGINS` with correct domain.',
        'Docs build fails: remove `node_modules`, then rerun `npm install` and `npm run build`.',
      ],
    },
  },
  {
    id: 'faq',
    title: { vi: 'FAQ', en: 'FAQ' },
    bullets: {
      vi: [
        'Q: Có cần chạy cả API và MCP cùng lúc? A: Không bắt buộc, tùy luồng tích hợp.',
        'Q: Data lưu ở đâu? A: Mặc định trong `data/decisiongraph.json`.',
        'Q: Có thể dùng docs frontend độc lập không? A: Có, đây là app React tách biệt.',
      ],
      en: [
        'Q: Do I need API and MCP running at the same time? A: Not required, depends on your integration flow.',
        'Q: Where is data stored? A: By default in `data/decisiongraph.json`.',
        'Q: Can docs frontend run independently? A: Yes, it is a standalone React app.',
      ],
    },
  },
]
