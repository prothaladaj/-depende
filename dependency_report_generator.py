#!/usr/bin/env python3
"""Generate a human-readable dependency report in English or Polish.

The generator is intentionally standalone and public-safe:
it does not know any private host names, production paths, or project names.
It only reads JSON files provided by the operator.

Expected inputs:
  - inventory JSON: a file with a top-level "rows" list,
  - optional outdated cache JSON: keys like "project/path::npm" or
    "project/path::composer".

The inventory shape is compatible with the report files produced during the
maintenance workflow:

{
  "rows": [
    {
      "dir": "example/project",
      "kinds": ["npm", "composer"],
      "locks": ["package-lock.json", "composer.lock"],
      "deps": {
        "npm_runtime": 3,
        "npm_dev": 8,
        "composer_runtime": 5,
        "composer_dev": 7
      }
    }
  ]
}
"""

from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Dependency Report",
        "subtitle": "Human-readable overview of manifests, lockfiles and outdated direct dependencies.",
        "generated_from": "Generated from",
        "summary": "Summary",
        "manifest_dirs": "manifest directories",
        "work_dirs": "working directories",
        "with_lock": "with lockfile",
        "without_lock": "without lockfile",
        "third_party": "third-party / generated",
        "how_to_read": "How to read this report",
        "how_to_read_text": "A manifest declares dependencies. A lockfile records exact resolved versions. Runtime dependencies are needed by the application while running. Dev dependencies are used for development, tests or builds. Outdated means a package registry knows a newer direct dependency version.",
        "limitations": "Limitations",
        "limitations_text": "This report is a readable summary, not a full security audit. It only knows what is present in the input JSON files. Python outdated status is shown only if your own cache provides it.",
        "projects": "Projects",
        "ignored": "Ignored / third-party / generated entries",
        "type": "Type",
        "category": "Category",
        "lockfile": "Lockfile",
        "dependencies": "Dependencies",
        "outdated_status": "Outdated status",
        "no_lock": "No lockfile",
        "not_checked": "Not checked",
        "timeout": "Timeout while checking",
        "current": "Up to date according to cache",
        "outdated": "Outdated",
        "major_updates": "Major updates",
        "no_data": "No outdated data available for this project.",
        "runtime": "runtime",
        "dev": "dev",
        "possible_major": "possible major",
        "direct_outdated": "outdated direct dependencies",
        "samples": "Examples",
        "working_app": "working application",
        "local_package": "local module / package",
        "third_party_category": "third-party / generated",
    },
    "pl": {
        "title": "Raport zależności",
        "subtitle": "Czytelny przegląd manifestów, lockfile i przeterminowanych bezpośrednich zależności.",
        "generated_from": "Wygenerowano z",
        "summary": "Podsumowanie",
        "manifest_dirs": "katalogów z manifestami",
        "work_dirs": "katalogów roboczych",
        "with_lock": "z lockfile",
        "without_lock": "bez lockfile",
        "third_party": "third-party / wygenerowane",
        "how_to_read": "Jak czytać ten raport",
        "how_to_read_text": "Manifest deklaruje zależności. Lockfile zapisuje dokładne rozwiązane wersje. Zależności runtime są potrzebne aplikacji w czasie działania. Zależności dev służą do developmentu, testów albo buildów. Przeterminowane oznacza, że rejestr pakietów zna nowszą wersję bezpośredniej zależności.",
        "limitations": "Ograniczenia",
        "limitations_text": "Ten raport jest czytelnym podsumowaniem, a nie pełnym audytem bezpieczeństwa. Wie tylko to, co znajduje się w wejściowych plikach JSON. Status outdated dla Pythona pojawi się tylko wtedy, gdy dostarczy go własny cache.",
        "projects": "Projekty",
        "ignored": "Pomijane / third-party / wygenerowane wpisy",
        "type": "Typ",
        "category": "Kategoria",
        "lockfile": "Lockfile",
        "dependencies": "Zależności",
        "outdated_status": "Stan przeterminowania",
        "no_lock": "Brak lockfile",
        "not_checked": "Nie sprawdzono",
        "timeout": "Timeout podczas sprawdzania",
        "current": "Aktualne według cache",
        "outdated": "Przeterminowane",
        "major_updates": "Duże aktualizacje",
        "no_data": "Brak danych outdated dla tego projektu.",
        "runtime": "runtime",
        "dev": "dev",
        "possible_major": "możliwe major",
        "direct_outdated": "przeterminowanych bezpośrednich zależności",
        "samples": "Przykłady",
        "working_app": "aplikacja robocza",
        "local_package": "lokalny moduł / pakiet",
        "third_party_category": "third-party / wygenerowane",
    },
}


NOISE_PARTS = (
    "node_modules/",
    "vendor/",
    "site-packages/",
    "venv/",
    ".venv/",
    ".next/",
    "third_party/",
    "vendor_prefixed/",
    "vendor-prefixed/",
)


@dataclass(frozen=True)
class Row:
    """Normalized project row used by the HTML renderer."""

    directory: str
    kinds: list[str]
    locks: list[str]
    deps: dict[str, int]


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file as UTF-8."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_rows(raw: dict[str, Any]) -> list[Row]:
    """Convert raw inventory dictionaries into typed Row objects."""

    rows: list[Row] = []
    for item in raw.get("rows", []):
        rows.append(
            Row(
                directory=str(item.get("dir", "")),
                kinds=[str(x) for x in item.get("kinds", [])],
                locks=[str(x) for x in item.get("locks", [])],
                deps={str(k): int(v or 0) for k, v in item.get("deps", {}).items()},
            )
        )
    return rows


def is_noise(directory: str) -> bool:
    """Return true when the row looks like generated or third-party code."""

    return any(part in directory for part in NOISE_PARTS)


def category(row: Row, labels: dict[str, str]) -> str:
    """Classify a row into a human-facing category."""

    directory = row.directory
    if is_noise(directory):
        return labels["third_party_category"]
    if "/" not in directory or any(
        marker in directory
        for marker in ("/backend", "/platform", "/mobile", "/mobile-app", "/frontend", "/web", "/cms", "/apps/api", "/apps/web")
    ):
        return labels["working_app"]
    return labels["local_package"]


def load_outdated_cache(path: Path | None) -> dict[str, Any]:
    """Read optional outdated cache. Missing cache means no outdated data."""

    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Outdated cache not found: {path}")
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def outdated_for(row: Row, cache: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return cached outdated data for a row grouped by tool name."""

    result: dict[str, dict[str, Any]] = {}
    for key, value in cache.items():
        if not isinstance(key, str) or "::" not in key:
            continue
        directory, tool = key.rsplit("::", 1)
        if directory == row.directory and isinstance(value, dict):
            result[tool] = value
    return result


def severity(row: Row, cache: dict[str, Any], labels: dict[str, str]) -> tuple[str, str]:
    """Return visual severity class and label for one row."""

    if not row.locks:
        return "bad", labels["no_lock"]

    data = outdated_for(row, cache)
    if not data:
        return "muted", labels["not_checked"]

    if any(value.get("timeout") for value in data.values()):
        return "warn", labels["timeout"]

    total = sum(int(value.get("total") or 0) for value in data.values())
    majors = sum(int(value.get("majors") or 0) for value in data.values())

    if majors:
        return "bad", f"{labels['major_updates']}: {majors}"
    if total:
        return "warn", f"{labels['outdated']}: {total}"
    return "ok", labels["current"]


def dependency_text(row: Row, labels: dict[str, str]) -> str:
    """Build a compact dependency count description."""

    parts: list[str] = []
    if "npm" in row.kinds:
        parts.append(f"npm {labels['runtime']} {row.deps.get('npm_runtime', 0)}, {labels['dev']} {row.deps.get('npm_dev', 0)}")
    if "composer" in row.kinds:
        parts.append(
            f"Composer {labels['runtime']} {row.deps.get('composer_runtime', 0)}, {labels['dev']} {row.deps.get('composer_dev', 0)}"
        )
    if "python" in row.kinds:
        parts.append("Python manifest")
    return " | ".join(parts) if parts else "-"


def outdated_html(row: Row, cache: dict[str, Any], labels: dict[str, str]) -> str:
    """Render outdated cache details for one row."""

    data = outdated_for(row, cache)
    if not data:
        return f"<p class='muted'>{html.escape(labels['no_data'])}</p>"

    items: list[str] = []
    for tool, value in sorted(data.items()):
        if value.get("timeout"):
            items.append(f"<li><b>{html.escape(tool)}</b>: {html.escape(labels['timeout'])}</li>")
            continue

        total = int(value.get("total") or 0)
        majors = int(value.get("majors") or 0)
        samples = value.get("samples") or []
        sample_text = "; ".join(str(sample) for sample in samples[:12])

        if total:
            items.append(
                "<li>"
                f"<b>{html.escape(tool)}</b>: {total} {html.escape(labels['direct_outdated'])}, "
                f"{html.escape(labels['possible_major'])}: {majors}"
                f"<br><span class='samples'>{html.escape(labels['samples'])}: {html.escape(sample_text)}</span>"
                "</li>"
            )
        else:
            items.append(f"<li><b>{html.escape(tool)}</b>: {html.escape(labels['current'])}</li>")

    return "<ul>" + "".join(items) + "</ul>"


def render_report(rows: list[Row], cache: dict[str, Any], language: str, source_name: str) -> str:
    """Render the complete HTML document."""

    labels = TRANSLATIONS[language]
    active_rows = [row for row in rows if not is_noise(row.directory)]
    ignored_rows = [row for row in rows if is_noise(row.directory)]

    order = {"bad": 0, "warn": 1, "muted": 2, "ok": 3}
    sorted_rows = sorted(active_rows, key=lambda row: (order[severity(row, cache, labels)[0]], row.directory))

    project_cards: list[str] = []
    for row in sorted_rows:
        css_class, status = severity(row, cache, labels)
        locks = ", ".join(row.locks) if row.locks else "-"
        kinds = ", ".join(row.kinds) if row.kinds else "-"
        project_cards.append(
            f"""
            <section class="project {css_class}">
              <div class="head">
                <h2>{html.escape(row.directory)}</h2>
                <span class="badge {css_class}">{html.escape(status)}</span>
              </div>
              <p><b>{html.escape(labels['type'])}:</b> {html.escape(kinds)} · <b>{html.escape(labels['category'])}:</b> {html.escape(category(row, labels))}</p>
              <p><b>{html.escape(labels['lockfile'])}:</b> {html.escape(locks)} · <b>{html.escape(labels['dependencies'])}:</b> {html.escape(dependency_text(row, labels))}</p>
              <details open>
                <summary>{html.escape(labels['outdated_status'])}</summary>
                {outdated_html(row, cache, labels)}
              </details>
            </section>
            """
        )

    ignored_items = "\n".join(
        f"<li>{html.escape(row.directory)} <span class='muted'>({html.escape(', '.join(row.kinds))})</span></li>"
        for row in ignored_rows
    )

    return f"""<!doctype html>
<html lang="{html.escape(language)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(labels['title'])}</title>
  <style>
    body {{ margin: 0; background: #f6f7f9; color: #17202a; font: 16px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    header {{ background: #17202a; color: white; padding: 32px 40px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin: 0 0 8px; word-break: break-word; letter-spacing: 0; }}
    code {{ background: #e2e8f0; color: #111827; padding: 2px 5px; border-radius: 4px; }}
    .sub {{ color: #cbd5e1; margin: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin: 20px 0; }}
    .metric {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 16px; }}
    .metric b {{ display: block; font-size: 28px; }}
    .note {{ background: white; border-left: 5px solid #3b82f6; padding: 16px 18px; margin: 18px 0; border-radius: 6px; }}
    .project {{ background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; margin: 12px 0; }}
    .project.bad {{ border-left: 6px solid #dc2626; }}
    .project.warn {{ border-left: 6px solid #d97706; }}
    .project.ok {{ border-left: 6px solid #16a34a; }}
    .project.muted {{ border-left: 6px solid #64748b; }}
    .head {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }}
    .badge {{ white-space: nowrap; border-radius: 999px; padding: 5px 10px; font-size: 13px; font-weight: 700; }}
    .badge.bad {{ background: #fee2e2; color: #991b1b; }}
    .badge.warn {{ background: #fef3c7; color: #92400e; }}
    .badge.ok {{ background: #dcfce7; color: #166534; }}
    .badge.muted {{ background: #e2e8f0; color: #334155; }}
    summary {{ cursor: pointer; font-weight: 700; margin-top: 8px; }}
    .samples, .muted {{ color: #64748b; }}
    li {{ margin: 5px 0; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(labels['title'])}</h1>
    <p class="sub">{html.escape(labels['subtitle'])}</p>
    <p class="sub">{html.escape(labels['generated_from'])}: <code>{html.escape(source_name)}</code></p>
  </header>
  <main>
    <section class="grid">
      <div class="metric"><b>{len(rows)}</b>{html.escape(labels['manifest_dirs'])}</div>
      <div class="metric"><b>{len(active_rows)}</b>{html.escape(labels['work_dirs'])}</div>
      <div class="metric"><b>{sum(bool(row.locks) for row in active_rows)}</b>{html.escape(labels['with_lock'])}</div>
      <div class="metric"><b>{sum(not row.locks for row in active_rows)}</b>{html.escape(labels['without_lock'])}</div>
      <div class="metric"><b>{len(ignored_rows)}</b>{html.escape(labels['third_party'])}</div>
    </section>
    <section class="note">
      <h2>{html.escape(labels['how_to_read'])}</h2>
      <p>{html.escape(labels['how_to_read_text'])}</p>
    </section>
    <section class="note">
      <h2>{html.escape(labels['limitations'])}</h2>
      <p>{html.escape(labels['limitations_text'])}</p>
    </section>
    <h2>{html.escape(labels['projects'])}</h2>
    {''.join(project_cards)}
    <h2>{html.escape(labels['ignored'])}</h2>
    <ul>{ignored_items}</ul>
  </main>
</body>
</html>
"""


def main() -> int:
    """Parse CLI arguments and generate the requested report."""

    parser = argparse.ArgumentParser(description="Generate an English or Polish dependency report HTML file.")
    parser.add_argument("--inventory", required=True, type=Path, help="Path to dependency inventory JSON.")
    parser.add_argument("--outdated-cache", type=Path, help="Optional path to outdated cache JSON.")
    parser.add_argument("--output", required=True, type=Path, help="Output HTML file.")
    parser.add_argument("--lang", choices=("en", "pl"), default="en", help="Report language.")
    args = parser.parse_args()

    inventory = read_json(args.inventory)
    rows = normalize_rows(inventory)
    cache = load_outdated_cache(args.outdated_cache)
    report = render_report(rows, cache, args.lang, args.inventory.name)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
