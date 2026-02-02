from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .checker import QCResult


@dataclass
class CostReportEntry:
    asset_id: str
    provider: str
    model: str
    cost_usd: float
    cached: bool
    timestamp: str


@dataclass
class CostReport:
    total_cost_usd: float
    total_runs: int
    cached_runs: int
    reuse_rate: float
    entries: list[CostReportEntry] = field(default_factory=list)
    by_provider: dict[str, float] = field(default_factory=dict)


def generate_qc_report(result: QCResult, output_dir: Path, episode_id: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_data = _qc_result_to_dict(result, episode_id)

    json_path = output_dir / "qc_report.json"
    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    md_path = output_dir / "qc_report.md"
    md_content = _qc_result_to_markdown(result, episode_id)
    md_path.write_text(md_content, encoding="utf-8")

    return json_path, md_path


def _qc_result_to_dict(result: QCResult, episode_id: str) -> dict[str, Any]:
    return {
        "episode_id": episode_id,
        "timestamp": datetime.now().isoformat(),
        "passed": result.passed,
        "summary": {
            "total_warnings": len(result.warnings),
            "total_errors": len(result.errors),
        },
        "warnings": result.warnings,
        "errors": result.errors,
        "rule_results": [
            {
                "rule_name": rr.rule_name,
                "passed": rr.passed,
                "warnings": rr.warnings,
                "errors": rr.errors,
            }
            for rr in result.rule_results
        ],
    }


def _qc_result_to_markdown(result: QCResult, episode_id: str) -> str:
    lines = [
        f"# QC Report: {episode_id}",
        "",
        f"**Status:** {'✅ PASSED' if result.passed else '❌ FAILED'}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        f"- **Errors:** {len(result.errors)}",
        f"- **Warnings:** {len(result.warnings)}",
        "",
    ]

    if result.errors:
        lines.extend([
            "## Errors",
            "",
        ])
        for error in result.errors:
            lines.append(f"- ❌ {error}")
        lines.append("")

    if result.warnings:
        lines.extend([
            "## Warnings",
            "",
        ])
        for warning in result.warnings:
            lines.append(f"- ⚠️ {warning}")
        lines.append("")

    lines.extend([
        "## Rule Details",
        "",
    ])
    for rr in result.rule_results:
        status = "✅" if rr.passed else "❌"
        lines.append(f"### {status} {rr.rule_name}")
        lines.append("")
        if rr.errors:
            for e in rr.errors:
                lines.append(f"- ❌ {e}")
        if rr.warnings:
            for w in rr.warnings:
                lines.append(f"- ⚠️ {w}")
        if not rr.errors and not rr.warnings:
            lines.append("- No issues found")
        lines.append("")

    return "\n".join(lines)


def generate_cost_report(logs_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = _parse_gen_runs(logs_dir)
    report = _build_cost_report(entries)

    report_data = {
        "total_cost_usd": report.total_cost_usd,
        "total_runs": report.total_runs,
        "cached_runs": report.cached_runs,
        "reuse_rate": report.reuse_rate,
        "by_provider": report.by_provider,
        "entries": [
            {
                "asset_id": e.asset_id,
                "provider": e.provider,
                "model": e.model,
                "cost_usd": e.cost_usd,
                "cached": e.cached,
                "timestamp": e.timestamp,
            }
            for e in report.entries
        ],
    }

    json_path = output_dir / "cost_report.json"
    json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    md_path = output_dir / "cost_report.md"
    md_content = _cost_report_to_markdown(report)
    md_path.write_text(md_content, encoding="utf-8")

    return json_path, md_path


def _parse_gen_runs(logs_dir: Path) -> list[CostReportEntry]:
    entries = []
    gen_runs_path = logs_dir / "gen_runs.jsonl"

    if not gen_runs_path.exists():
        return entries

    for line in gen_runs_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            entries.append(CostReportEntry(
                asset_id=data.get("asset_id", "unknown"),
                provider=data.get("provider", "unknown"),
                model=data.get("model", "unknown"),
                cost_usd=data.get("cost_usd", 0.0),
                cached=data.get("cached", False),
                timestamp=data.get("timestamp", ""),
            ))
        except json.JSONDecodeError:
            continue

    return entries


def _build_cost_report(entries: list[CostReportEntry]) -> CostReport:
    total_cost = sum(e.cost_usd for e in entries if not e.cached)
    total_runs = len(entries)
    cached_runs = sum(1 for e in entries if e.cached)
    reuse_rate = cached_runs / total_runs if total_runs > 0 else 0.0

    by_provider: dict[str, float] = {}
    for e in entries:
        if not e.cached:
            by_provider[e.provider] = by_provider.get(e.provider, 0.0) + e.cost_usd

    return CostReport(
        total_cost_usd=total_cost,
        total_runs=total_runs,
        cached_runs=cached_runs,
        reuse_rate=reuse_rate,
        entries=entries,
        by_provider=by_provider,
    )


def _cost_report_to_markdown(report: CostReport) -> str:
    lines = [
        "# Cost & Reuse Report",
        "",
        "## Summary",
        "",
        f"- **Total Cost:** ${report.total_cost_usd:.4f}",
        f"- **Total Runs:** {report.total_runs}",
        f"- **Cached Runs:** {report.cached_runs}",
        f"- **Reuse Rate:** {report.reuse_rate*100:.1f}%",
        "",
    ]

    if report.by_provider:
        lines.extend([
            "## Cost by Provider",
            "",
            "| Provider | Cost (USD) |",
            "|----------|------------|",
        ])
        for provider, cost in sorted(report.by_provider.items()):
            lines.append(f"| {provider} | ${cost:.4f} |")
        lines.append("")

    if report.entries:
        lines.extend([
            "## Recent Runs",
            "",
            "| Asset | Provider | Model | Cost | Cached |",
            "|-------|----------|-------|------|--------|",
        ])
        for e in report.entries[-20:]:
            cached_str = "✅" if e.cached else "❌"
            lines.append(f"| {e.asset_id} | {e.provider} | {e.model} | ${e.cost_usd:.4f} | {cached_str} |")
        lines.append("")

    return "\n".join(lines)
