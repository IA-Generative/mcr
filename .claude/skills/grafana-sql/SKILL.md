---
name: grafana-sql
description: Generate PostgreSQL queries for Grafana dashboards from natural language. Use when the user asks for SQL queries, Grafana panels, or data analysis on MCR meeting data.
argument-hint: "[describe the data you want to visualize]"
---

You generate **read-only PostgreSQL SELECT queries** optimized for Grafana dashboards. You MUST load the live database schema before generating any SQL.

## Step 1: Load schema

Execute these in order. Stop at the first success.

1. Run `python3 ${CLAUDE_SKILL_DIR}/scripts/extract_schema.py` — if exit code 0, use its stdout as the schema. The script auto-detects the models directory from the current working directory.
2. If step 1 failed: read `mcr-core/mcr_meeting/app/models/__init__.py`, then read each model file it imports. Parse the SQLAlchemy column definitions yourself.
3. If step 2 failed: glob for `mcr-core/**/models/*_model.py`, read any files that define classes inheriting from `Base`.
4. If nothing found: tell the user you cannot locate the schema. **Do NOT generate SQL from memory or assumptions.**

## Step 2: Generate the query

Write a PostgreSQL SELECT query that answers the user's question using ONLY tables and columns from the schema loaded in step 1.

### Grafana rules

- Apply the time filter macro on the most relevant date column:
  ```sql
  WHERE $__timeFilter(creation_date)
  ```
- **UNION ALL pitfall**: `$__timeFilter` must appear in EVERY branch of a UNION ALL — not just the first one. This is the most common Grafana SQL bug. Always check.
- Reference Grafana variables as `${variable_name}` (string values need quoting: `'${status}'`)
- Generate ONLY `SELECT` statements — never `INSERT`, `UPDATE`, `DELETE`, `DROP`, or `ALTER`

### Domain rules

- **MCR_VISIO aggregation**: When grouping by platform type, propose to the user to aggregate COMU, WEBINAIRE, WEBCONF, VISIO, and WEBEX as `'MCR_VISIO'`:
  ```sql
  CASE
      WHEN name_platform IN ('COMU','WEBINAIRE','WEBCONF','VISIO','WEBEX') THEN 'MCR_VISIO'
      ELSE name_platform::text
  END
  ```

- **Status categories** (use these when the user asks about "failed", "successful", or "in progress" meetings):
  - Success: `REPORT_DONE`, `TRANSCRIPTION_DONE`
  - Failed: `CAPTURE_FAILED`, `CAPTURE_BOT_CONNECTION_FAILED`, `TRANSCRIPTION_FAILED`
  - In progress: `*_PENDING`, `*_IN_PROGRESS`, `CAPTURE_BOT_IS_CONNECTING`, `CAPTURE_DONE`
  - Not started: `NONE`

- **DELETED status — requires `meeting_transition_record` archeology**: `DELETED` is a terminal status that hides the previous state. A deleted meeting may have been a success or a failure before deletion.

  **When to include DELETED archeology:**
  - When the query filters on **terminal statuses** (cf Success or Failed Status categories) — because the outcome is an immutable fact. A deleted meeting that was `CAPTURE_FAILED` before deletion is still a failure.
  - When the user explicitly asks for a breakdown of deleted meetings.
  
  **When to exclude DELETED (with `AND status != 'DELETED'` and a note):**
  - Simple counts, averages, or metrics where the pre-deletion outcome doesn't change the answer.
  - When filtering on **transient statuses** (cf In progress Status categories) — these represent current state, not outcomes. A deleted meeting that was once TRANSCRIPTION_IN_PROGRESS isn't "currently being transcribed."
  - When grouping by status without filtering (e.g. "count by status") — DELETED shows up as its own bucket, archeology would over-complicate the query.

  Use `LEFT JOIN LATERAL ... ON true` to recover the pre-deletion status:
  ```sql
  -- All DELETED meetings bucketed by their last non-DELETED status
  SELECT
      COALESCE(CAST(pre_delete.last_status AS text), 'UNKNOWN') || '+DEL' AS status,
      COUNT(m.id) AS count
  FROM meeting m
  LEFT JOIN LATERAL (
      SELECT mtr.status AS last_status
      FROM meeting_transition_record mtr
      WHERE mtr.meeting_id = m.id
        AND mtr.status != 'DELETED'
      ORDER BY mtr.timestamp DESC, mtr.id DESC
      LIMIT 1
  ) pre_delete ON true
  WHERE $__timeFilter(m.creation_date)
    AND m.status = 'DELETED'
  GROUP BY pre_delete.last_status
  ```

  Key details:
  - Use `ON true`, NOT `ON (m.status = 'DELETED')` — the latter causes undercounting because non-matching rows still appear via LEFT JOIN but with NULL lateral columns
  - Use `COALESCE(..., 'UNKNOWN')` — some deleted meetings have no transition records at all
  - When combining with non-DELETED meetings in a UNION ALL, add `AND status != 'DELETED'` to the non-DELETED branch to prevent double-counting
  - The `|| '+DEL'` suffix creates synthetic status labels (e.g. `REPORT_DONE+DEL`) that preserve both the original state and the deletion

- **Prefer indexed columns** in WHERE clauses: `creation_date`, `name`, `url`, `speaker`, `email` (check the Indexed column in the schema output)

### Examples

**Simple aggregation:**
```sql
SELECT status, COUNT(*) AS meeting_count
FROM meeting
WHERE $__timeFilter(creation_date)
GROUP BY status
ORDER BY meeting_count DESC;
```

**Complete status breakdown including deleted meetings:**
```sql
-- Non-DELETED meetings by status
SELECT
    CAST(status AS text) AS status,
    COUNT(id)            AS count
FROM meeting
WHERE $__timeFilter(creation_date)
  AND status != 'DELETED'
GROUP BY status

UNION ALL

-- DELETED meetings bucketed by pre-deletion status
SELECT
    COALESCE(CAST(pre_delete.last_status AS text), 'UNKNOWN') || '+DEL' AS status,
    COUNT(m.id) AS count
FROM meeting m
LEFT JOIN LATERAL (
    SELECT mtr.status AS last_status
    FROM meeting_transition_record mtr
    WHERE mtr.meeting_id = m.id
      AND mtr.status != 'DELETED'
    ORDER BY mtr.timestamp DESC, mtr.id DESC
    LIMIT 1
) pre_delete ON true
WHERE $__timeFilter(m.creation_date)
  AND m.status = 'DELETED'
GROUP BY pre_delete.last_status;
```

## Step 3: Output

1. The SQL query in a fenced `sql` code block
2. A one-line explanation of what the query returns
3. If you made any assumptions (e.g. which date column to filter on, whether DELETED meetings are included), list them
4. **If the query is complex** (uses UNION ALL, LEFT JOIN LATERAL, CTEs, or computes ratios/percentages), propose to the user that you can provide validation queries to verify the counts. Do not output them automatically — just mention the offer.

## Step 4: Validation queries (on request)

When the user accepts the validation offer (or explicitly asks for checks), generate self-contained queries that return a boolean or two comparable rows. The goal: the user pastes one query into Grafana, sees `true` or sees two identical numbers, and knows the main query is correct.

### Patterns

**Total count match** — verify the main query accounts for every meeting:
```sql
-- Should return true: main query total matches ground truth
SELECT (
    SELECT SUM(count) FROM (
        -- paste main query here
    ) sub
) = (
    SELECT COUNT(*) FROM meeting WHERE $__timeFilter(creation_date)
) AS counts_match;
```

**Branch balance** — verify UNION ALL branches don't overlap or miss rows:
```sql
-- Should return two identical numbers
SELECT 'non_deleted' AS branch, COUNT(*) AS n FROM meeting WHERE $__timeFilter(creation_date) AND status != 'DELETED'
UNION ALL
SELECT 'deleted', COUNT(*) FROM meeting WHERE $__timeFilter(creation_date) AND status = 'DELETED'
UNION ALL
SELECT 'total', COUNT(*) FROM meeting WHERE $__timeFilter(creation_date);
-- non_deleted + deleted should equal total
```

**Overlap check** — verify no meeting is counted in both UNION branches:
```sql
-- Should return 0 (no overlap)
SELECT COUNT(*) AS overlap
FROM meeting
WHERE $__timeFilter(creation_date)
  AND status = 'DELETED'
  AND status != 'DELETED';
-- This is trivially 0 for status-based splits, but for more complex
-- partitioning (e.g. by join conditions), replace with actual ID intersection
```

### When to offer validation
- UNION ALL (branches may overlap or miss rows)
- LEFT JOIN LATERAL (ON clause bugs cause silent under/overcounting)
- CTEs feeding into aggregations
- Percentage/ratio computations (numerator and denominator may diverge)

Do NOT offer validation for simple single-table GROUP BY queries.
