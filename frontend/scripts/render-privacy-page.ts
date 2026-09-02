/**
 * Renders the public `/privacy.html` page from the single policy source in
 * `privacy-policy.ts`, so the published page can never drift from the
 * one the app shows. Called from the Vite plugin in vite.config.ts at build time; the page stays
 * self-contained (no external resources), as the PH-706 design requires.
 */
import {
  PRIVACY_POLICY,
  policyMeta,
  type PolicyBlock,
  type PolicyDocument,
  type PolicyRun,
} from "../src/lib/privacy-policy.ts";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderRuns(runs: PolicyRun[]): string {
  return runs
    .map((run) => (typeof run === "string"
      ? escapeHtml(run)
      : `<strong>${escapeHtml(run.strong)}</strong>`))
    .join("");
}

function renderBlock(block: PolicyBlock): string {
  if (block.kind === "list") {
    const items = block.items
      .map((item) => `      <li>${renderRuns(item)}</li>`)
      .join("\n");
    return `    <ul>\n${items}\n    </ul>`;
  }
  const className = block.quiet ? ' class="quiet"' : "";
  return `    <p${className}>${renderRuns(block.runs)}</p>`;
}

const STYLES = `
    :root {
      color-scheme: light;
      --ink: #2f2a26;
      --muted: #6f655c;
      --paper: #faf6f0;
      --card: #ffffff;
      --line: #ece4da;
      --accent: #b5854f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      line-height: 1.6;
      font-size: 16px;
    }
    main {
      max-width: 680px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }
    header { border-bottom: 1px solid var(--line); padding-bottom: 20px; margin-bottom: 28px; }
    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 12px;
      color: var(--muted);
      margin: 0 0 8px;
    }
    h1 { font-size: 28px; margin: 0 0 8px; }
    .meta { color: var(--muted); font-size: 14px; margin: 0; }
    section {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 20px 22px;
      margin-bottom: 16px;
    }
    h2 { font-size: 19px; margin: 0 0 10px; }
    ul { padding-left: 20px; margin: 8px 0; }
    li { margin: 4px 0; }
    .quiet { color: var(--muted); }
    a { color: var(--accent); }
    footer { text-align: center; color: var(--muted); font-size: 13px; margin-top: 28px; }`;

export function renderPolicyPage(policy: PolicyDocument = PRIVACY_POLICY): string {
  const sections = policy.sections
    .map((section) => [
      "  <section>",
      `    <h2>${escapeHtml(section.heading)}</h2>`,
      ...section.blocks.map(renderBlock),
      "  </section>",
    ].join("\n"))
    .join("\n\n");

  return `<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(policy.title)} — Похвали себя</title>
  <style>${STYLES}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">${escapeHtml(policy.eyebrow)}</p>
    <h1>${escapeHtml(policy.title)}</h1>
    <p class="meta">${escapeHtml(policyMeta(policy))}</p>
  </header>

${sections}

  <footer>${escapeHtml(policy.footer)}</footer>
</main>
</body>
</html>
`;
}
