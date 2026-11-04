"""All database reads/writes for scans. Each function opens its own short-lived connection."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database.db import connect
from app.schemas.scan import (
    DailyCount,
    IndicatorCount,
    ScanResult,
    ScanSummary,
    StatsResponse,
)

CATEGORIES = ("low", "suspicious", "high")


def insert_scan(result: ScanResult, path: Path | str | None = None) -> None:
    ml_score = result.ml.score if result.ml is not None and result.ml.available else None
    with connect(path) as conn:
        conn.execute(
            """INSERT INTO scans (id, input_type, input_summary, risk_score, risk_category, ml_score,
                                  indicators_json, result_json, is_demo, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                result.scan_id,
                result.input_type,
                result.input_summary,
                result.risk_score,
                result.risk_category,
                ml_score,
                json.dumps([i.model_dump() for i in result.indicators]),
                result.model_dump_json(),
                1 if result.is_demo else 0,
                result.analyzed_at,
            ),
        )


def get_scan(scan_id: str, path: Path | str | None = None) -> ScanResult | None:
    with connect(path) as conn:
        row = conn.execute("SELECT result_json FROM scans WHERE id = ?", (scan_id,)).fetchone()
    return ScanResult.model_validate_json(row["result_json"]) if row else None


def list_scans(
    *,
    limit: int = 20,
    offset: int = 0,
    category: str | None = None,
    input_type: str | None = None,
    path: Path | str | None = None,
) -> tuple[list[ScanSummary], int]:
    where, params = [], []
    if category:
        where.append("risk_category = ?")
        params.append(category)
    if input_type:
        where.append("input_type = ?")
        params.append(input_type)
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    with connect(path) as conn:
        total = conn.execute(f"SELECT COUNT(*) AS n FROM scans {clause}", params).fetchone()["n"]
        rows = conn.execute(
            f"""SELECT id, input_type, input_summary, risk_score, risk_category, ml_score,
                       indicators_json, created_at, is_demo
                FROM scans {clause}
                ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?""",
            [*params, limit, offset],
        ).fetchall()

    items = [
        ScanSummary(
            scan_id=r["id"],
            input_type=r["input_type"],
            input_summary=r["input_summary"],
            risk_score=r["risk_score"],
            risk_category=r["risk_category"],
            ml_score=r["ml_score"],
            indicator_count=len([i for i in json.loads(r["indicators_json"]) if i["points"] > 0]),
            created_at=r["created_at"],
            is_demo=bool(r["is_demo"]),
        )
        for r in rows
    ]
    return items, total


def iter_all_scans(path: Path | str | None = None) -> list[ScanResult]:
    """Every scan, newest first. Used by the CSV export."""
    with connect(path) as conn:
        rows = conn.execute("SELECT result_json FROM scans ORDER BY created_at DESC, rowid DESC").fetchall()
    return [ScanResult.model_validate_json(r["result_json"]) for r in rows]


def count_demo_scans(path: Path | str | None = None) -> int:
    with connect(path) as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM scans WHERE is_demo = 1").fetchone()["n"]


def clear_scans(*, demo_only: bool = False, path: Path | str | None = None) -> int:
    with connect(path) as conn:
        cur = conn.execute("DELETE FROM scans WHERE is_demo = 1" if demo_only else "DELETE FROM scans")
        return cur.rowcount


def get_stats(path: Path | str | None = None) -> StatsResponse:
    with connect(path) as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM scans").fetchone()["n"]
        avg = conn.execute("SELECT AVG(risk_score) AS a FROM scans").fetchone()["a"]
        demo = conn.execute("SELECT COUNT(*) AS n FROM scans WHERE is_demo = 1").fetchone()["n"]
        by_cat_rows = conn.execute("SELECT risk_category AS k, COUNT(*) AS n FROM scans GROUP BY risk_category").fetchall()
        by_type_rows = conn.execute("SELECT input_type AS k, COUNT(*) AS n FROM scans GROUP BY input_type").fetchall()
        since = (datetime.now(timezone.utc) - timedelta(days=13)).strftime("%Y-%m-%d")
        daily_rows = conn.execute(
            """SELECT substr(created_at, 1, 10) AS d, COUNT(*) AS n,
                      SUM(CASE WHEN risk_category = 'high' THEN 1 ELSE 0 END) AS h
               FROM scans WHERE substr(created_at, 1, 10) >= ? GROUP BY d""",
            (since,),
        ).fetchall()
        recent = conn.execute("SELECT indicators_json FROM scans ORDER BY created_at DESC LIMIT 500").fetchall()

    by_category = {c: 0 for c in CATEGORIES}
    by_category.update({r["k"]: r["n"] for r in by_cat_rows})
    by_input_type = {"url": 0, "email": 0}
    by_input_type.update({r["k"]: r["n"] for r in by_type_rows})

    by_day = {r["d"]: (r["n"], r["h"] or 0) for r in daily_rows}
    today = datetime.now(timezone.utc).date()
    last_14 = []
    for offset in range(13, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        n, h = by_day.get(day, (0, 0))
        last_14.append(DailyCount(date=day, total=n, high=h))

    counter: Counter[tuple[str, str]] = Counter()
    for row in recent:
        for ind in json.loads(row["indicators_json"]):
            if ind["points"] > 0:
                counter[(ind["id"], ind["title"])] += 1
    top = [IndicatorCount(id=k[0], title=k[1], count=v) for k, v in counter.most_common(8)]

    return StatsResponse(
        total_scans=total,
        by_category=by_category,
        by_input_type=by_input_type,
        demo_scans=demo,
        average_score=round(avg or 0.0, 1),
        last_14_days=last_14,
        top_indicators=top,
    )
