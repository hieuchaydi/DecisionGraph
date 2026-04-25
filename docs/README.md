# DecisionGraph Docs Frontend

## VI
Đây là app tài liệu cho DecisionGraph (React + TypeScript + Vite), tối ưu đọc nhanh trên cả desktop và mobile.

### Điểm nhấn mới (ăn điểm)
- **Live Readiness Console** ngay trong docs UI:
  - Chạy check thật vào API (`/health`, `/api/decisions`, `/api/query`, `/api/guardrail`, `/api/schema/info`).
  - Đo latency từng check + tính readiness score tổng thể.
  - Hỗ trợ `x-api-key` để test môi trường protected.
  - Hiển thị lỗi chi tiết để debug nhanh khi demo/release check.

### Docs scope (đã mở rộng)
- Overview + when-to-use theo góc nhìn vận hành team.
- Architecture + project structure để onboarding nhanh.
- Quickstart đầy đủ cho backend, docs frontend, MCP.
- Env Setup (`.env`) với lệnh tạo file + mẫu cấu hình.
- CLI/API/MCP reference theo nhóm tính năng.
- Environment config, troubleshooting, FAQ.
- Prompt playbook VI/EN + flow validation nhiều lượt.

### Responsive behavior
- Desktop: sidebar mục lục cố định, đọc dạng knowledge base.
- Mobile/tablet: quick-nav dạng chip ngang để nhảy section nhanh.
- Anchor section có `scroll-margin` để không bị che bởi sticky topbar.

### Run local
```bash
npm install
npm run dev
```

### Backend `.env` setup (khuyến nghị)
```powershell
Copy-Item ..\.env.example ..\.env
```
Sau đó chỉnh `..\.env` (không commit secret):
- `DECISIONGRAPH_ENV`
- `DECISIONGRAPH_DATA_PATH`
- `DECISIONGRAPH_API_TOKEN` (tuỳ chọn)
- `DECISIONGRAPH_CORS_ORIGINS` (nếu gọi API từ domain khác)
- `DECISIONGRAPH_GITHUB_TOKEN` / `DECISIONGRAPH_GITHUB_BASE_URL` (tuỳ chọn)
- `GROQ_API_KEY` / `GROQ_MODELS` (tuỳ chọn)

### Quality check
```bash
npm run lint
npm run build
npm run preview
```

## EN
This is the documentation frontend for DecisionGraph (React + TypeScript + Vite), optimized for fast reading on both desktop and mobile.

### New standout feature
- **Live Readiness Console** inside the docs UI:
  - Runs real checks against API endpoints (`/health`, `/api/decisions`, `/api/query`, `/api/guardrail`, `/api/schema/info`).
  - Measures per-check latency and computes an overall readiness score.
  - Supports `x-api-key` for protected environments.
  - Surfaces failure details for faster demo/release troubleshooting.

### Expanded docs scope
- Overview + when-to-use from an engineering operations perspective.
- Architecture + project structure for faster onboarding.
- Complete quickstart for backend, docs frontend, and MCP.
- Env Setup (`.env`) with file bootstrap commands and sample config.
- CLI/API/MCP references grouped by capabilities.
- Environment config, troubleshooting, and FAQ.
- VI/EN prompt playbook + multi-pass flow validation.

### Responsive behavior
- Desktop: sticky sidebar for knowledge-base style navigation.
- Mobile/tablet: horizontal quick-nav chips for fast section jumps.
- Section anchors use `scroll-margin` to avoid sticky-header overlap.

### Run local
```bash
npm install
npm run dev
```

### Recommended backend `.env` setup
```bash
cp ../.env.example ../.env
```
Then edit `../.env` (do not commit real secrets):
- `DECISIONGRAPH_ENV`
- `DECISIONGRAPH_DATA_PATH`
- `DECISIONGRAPH_API_TOKEN` (optional)
- `DECISIONGRAPH_CORS_ORIGINS` (when frontend runs on another origin)
- `DECISIONGRAPH_GITHUB_TOKEN` / `DECISIONGRAPH_GITHUB_BASE_URL` (optional)
- `GROQ_API_KEY` / `GROQ_MODELS` (optional)

### Quality check
```bash
npm run lint
npm run build
npm run preview
```
