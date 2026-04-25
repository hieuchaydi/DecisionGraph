from __future__ import annotations

HOME_HTML = """\
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>DecisionGraph</title>
    <style>
      :root {
        --bg: #eef4f8;
        --panel: #ffffff;
        --text: #102435;
        --accent: #0a7f6f;
        --accent-2: #d55a2a;
        --border: #cad8e4;
      }
      body { margin: 0; font-family: "Segoe UI", Tahoma, sans-serif; background:
        radial-gradient(circle at 10% 10%, #e4f4ef 0, transparent 45%),
        radial-gradient(circle at 90% 0%, #ffe6d7 0, transparent 35%),
        linear-gradient(120deg, #eff5fa, #f8fafc); color: var(--text);}
      .wrap { max-width: 980px; margin: 28px auto; padding: 0 16px; }
      .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 14px; }
      h1 { margin: 0 0 6px; font-size: 30px; }
      .muted { color: #4f6b7a; }
      textarea, input { width: 100%; box-sizing: border-box; border: 1px solid var(--border); border-radius: 10px; padding: 10px; font-size: 14px; }
      button { background: var(--accent); color: #fff; border: 0; border-radius: 10px; padding: 10px 14px; font-weight: 600; cursor: pointer; }
      .warn { background: var(--accent-2); }
      pre { white-space: pre-wrap; background: #f7fbfd; border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
      ul { padding-left: 18px; }
      li { margin-bottom: 8px; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="card">
        <h1>DecisionGraph</h1>
        <div class="muted">Engineering Decision Memory System (MVP)</div>
      </div>

      <div class="card">
        <h3>Query decision history</h3>
        <textarea id="q" rows="3" placeholder="Why did we cap payment retries at 2 attempts?"></textarea>
        <div style="margin-top:10px;"><button onclick="runQuery()">Ask</button></div>
        <pre id="answer">No query yet.</pre>
      </div>

      <div class="card">
        <h3>Ingest raw text</h3>
        <input id="sid" placeholder="source id (e.g. PR-412)" />
        <textarea id="txt" rows="5" placeholder="Paste note, RFC excerpt, or incident summary..."></textarea>
        <div style="margin-top:10px;"><button onclick="runIngest()">Ingest</button></div>
      </div>

      <div class="card">
        <h3>Guardrail check before code change</h3>
        <textarea id="change" rows="4" placeholder="I want to simplify refresh token rotation and retry behavior..."></textarea>
        <div style="margin-top:10px;"><button class="warn" onclick="runGuardrail()">Run Guardrail</button></div>
        <pre id="guardrail">No guardrail run yet.</pre>
      </div>

      <div class="card">
        <h3>Recent decisions</h3>
        <button onclick="loadDecisions()">Refresh list</button>
        <ul id="list"></ul>
      </div>

      <div class="card">
        <h3>Contradictions and stale assumptions</h3>
        <button onclick="loadSignals()">Refresh signals</button>
        <pre id="signals">No signals loaded yet.</pre>
      </div>
    </div>
    <script>
      async function runQuery() {
        const question = document.getElementById("q").value.trim();
        if (!question) return;
        const res = await fetch("/api/query", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({question})
        });
        const data = await res.json();
        const related = (data.related || []).map(x => "- " + x.title).join("\\n");
        document.getElementById("answer").textContent = data.answer + "\\n\\nConfidence: " + data.confidence + "\\n\\nRelated:\\n" + (related || "None");
      }

      async function runIngest() {
        const source_id = document.getElementById("sid").value.trim() || "manual-note";
        const text = document.getElementById("txt").value.trim();
        if (!text) return;
        const res = await fetch("/api/ingest", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({source_id, text, source_type: "note"})
        });
        await res.json();
        await loadDecisions();
        await loadSignals();
      }

      async function runGuardrail() {
        const change_request = document.getElementById("change").value.trim();
        if (!change_request) return;
        const res = await fetch("/api/guardrail", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({change_request, limit: 3})
        });
        const data = await res.json();
        const related = (data.related_decisions || []).map(x => "- " + x.title).join("\\n");
        const stale = (data.stale_assumptions || []).map(x => `- ${x.decision_id}: ${x.assumption} (actual=${x.actual})`).join("\\n");
        document.getElementById("guardrail").textContent =
          "Blocked: " + data.blocked + "\\n" +
          "Warnings: " + ((data.warnings || []).join(", ") || "none") + "\\n\\n" +
          "Related decisions:\\n" + (related || "None") + "\\n\\n" +
          "Stale assumptions:\\n" + (stale || "None");
      }

      async function loadDecisions() {
        const res = await fetch("/api/decisions?limit=20");
        const data = await res.json();
        const ul = document.getElementById("list");
        ul.innerHTML = "";
        for (const item of data.items) {
          const li = document.createElement("li");
          li.textContent = item.title + " (" + (item.date || "unknown") + ")";
          ul.appendChild(li);
        }
      }

      async function loadSignals() {
        const [cRes, sRes] = await Promise.all([
          fetch("/api/contradictions"),
          fetch("/api/assumptions/stale")
        ]);
        const cData = await cRes.json();
        const sData = await sRes.json();
        const contradictions = (cData.items || []).slice(0, 5).map(x => `- ${x.topic}: ${x.reason} (${x.decision_a_id} vs ${x.decision_b_id})`).join("\\n");
        const stale = (sData.items || []).slice(0, 5).map(x => `- ${x.metric_key}: ${x.assumption} (actual=${x.actual})`).join("\\n");
        document.getElementById("signals").textContent =
          "Contradictions:\\n" + (contradictions || "None") + "\\n\\nStale assumptions:\\n" + (stale || "None");
      }

      loadDecisions();
      loadSignals();
    </script>
  </body>
</html>
"""
