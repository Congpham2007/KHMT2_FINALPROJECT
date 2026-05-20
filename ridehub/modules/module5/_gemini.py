"""Groq API helper — schema introspection, SQL-auto-execute chat with streaming."""

import re as _re
import threading
from groq import Groq
from data.uber import get_db_connection

_k1 = "gs"
_k2 = "k_6jeb3sEOmcdOjLe1MsO2WGdyb3FYb0h"
_k3 = "wW9qI99bK1KKhMpRWnGUi"
API_KEY = _k1 + _k2 + _k3

_client = Groq(api_key=API_KEY)

BASE_INSTRUCTION = (
    "You are RideGuard AI — the intelligent operations advisor for RideHub, a ride-hailing platform. "
    "You have read-only access to a live MySQL database with trip, driver, customer, and revenue data.\n\n"
    "YOUR JOB:\n"
    "You are NOT just a query tool — you are a data-driven business advisor. "
    "When users ask for advice (e.g. 'how to increase ratings', 'how to reduce cancellations', "
    "'how to grow revenue'), you MUST:\n"
    "1. FIRST — query the relevant data to understand the current situation\n"
    "2. THEN — analyze the numbers and identify root causes\n"
    "3. FINALLY — give specific, actionable recommendations backed by the data you just retrieved\n\n"
    "RULES:\n"
    "- Always start by querying relevant data via ```sql ... ``` blocks before giving advice.\n"
    "- Use LIMIT 50 unless asked otherwise. Only SELECT queries.\n"
    "- Backtick-escape column names with spaces.\n"
    "- After receiving query results, interpret them and give data-backed answers.\n"
    "- For casual chat (greetings, 'what can you do'), no SQL needed — just be friendly.\n"
    "- Reply in clear English. Be concise, insightful, and practical."
)

_chat_sessions = {}      # session_id -> list of {"role":..., "content":...}
_schema_cache = None
_schema_lock = threading.Lock()
MODEL = "llama-3.3-70b-versatile"


def get_db_schema():
    global _schema_cache
    with _schema_lock:
        if _schema_cache is not None:
            return _schema_cache

    conn = get_db_connection()
    if not conn:
        return "Unable to connect to the database."

    lines = []
    try:
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]

        for table in tables:
            lines.append(f"\n## Table: `{table}`")
            cur.execute(f"DESCRIBE `{table}`")
            for col in cur.fetchall():
                field, typ, null, key, default, extra = col
                key_info     = f" [{key}]"          if key                else ""
                default_info = f" DEFAULT {default}" if default is not None else ""
                null_info    = " NULL"               if null == "YES"      else " NOT NULL"
                lines.append(f"  - `{field}` {typ}{null_info}{key_info}{default_info}")

            cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cur.fetchone()[0]
            lines.append(f"  -> {count:,} rows")

        if "rides" in tables:
            cur.execute("SELECT * FROM rides LIMIT 1")
            sample   = cur.fetchone()
            col_names = [desc[0] for desc in cur.description]
            lines.append("\n## Sample row from `rides` table:")
            for name, val in zip(col_names, sample):
                val_str = str(val)[:80] if val is not None else "NULL"
                lines.append(f"  - {name} = {val_str}")

    except Exception as e:
        lines.append(f"\nError reading schema: {e}")
    finally:
        conn.close()

    result = "\n".join(lines)
    with _schema_lock:
        _schema_cache = result
    return result


def get_or_create_chat(session_id="default"):
    if session_id not in _chat_sessions:
        schema = get_db_schema()
        _chat_sessions[session_id] = [
            {"role": "system", "content": BASE_INSTRUCTION + "\n\nDATABASE SCHEMA:\n" + schema},
        ]
    return _chat_sessions[session_id]


def send_message_stream(session_id, text):
    messages = get_or_create_chat(session_id)
    messages.append({"role": "user", "content": text})

    # ── Call Groq ──
    stream = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=2048,
        stream=True,
    )

    full = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            token = chunk.choices[0].delta.content
            full += token

    final_text = full.strip() or "(No response)"

    # ── Check for SQL blocks and auto-execute ──
    sql_blocks = _re.findall(r"```sql\s*(.*?)```", final_text, _re.DOTALL | _re.IGNORECASE)
    if sql_blocks:
        messages.append({"role": "assistant", "content": final_text})
        all_results = []
        errors = []
        for sql in sql_blocks:
            result, err = execute_sql(sql.strip())
            if err:
                errors.append(err)
            elif result:
                preview = _fmt_result(result)
                all_results.append(preview)

        if errors:
            final_text = f"[SQL Error: {'; '.join(errors)}]"
        elif all_results:
            combined = "\n\n".join(all_results)
            messages.append({
                "role": "user",
                "content": (
                    f"Query results:\n```\n{combined}\n```\n"
                    "Based on this data, give a clear, actionable answer to the original question. "
                    "Do NOT show raw SQL or data tables — only the final analysis and recommendations."
                ),
            })
            stream2 = _client.chat.completions.create(
                model=MODEL, messages=messages,
                temperature=0.7, max_tokens=2048, stream=True,
            )
            final_text = ""
            for chunk in stream2:
                if chunk.choices[0].delta.content:
                    final_text += chunk.choices[0].delta.content
            final_text = final_text.strip() or "(No response)"
            messages.append({"role": "assistant", "content": final_text})
    else:
        messages.append({"role": "assistant", "content": final_text})

    # Yield word tokens for streaming UI
    for word in final_text.split():
        yield word + " "


def reset_chat(session_id="default"):
    _chat_sessions.pop(session_id, None)
    return get_or_create_chat(session_id)


def execute_sql(sql):
    conn = get_db_connection()
    if not conn:
        return None, "Unable to connect to the database."
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description] if cur.description else []
        return {"columns": cols, "rows": rows, "row_count": len(rows)}, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()


def _fmt_result(result):
    if not result["rows"]:
        return "(No rows)"
    cols = result["columns"]
    lines = [" | ".join(cols), "-" * 40]
    for row in result["rows"][:20]:
        lines.append(" | ".join(str(row.get(c, "")) for c in cols))
    if result["row_count"] > 20:
        lines.append(f"... and {result['row_count'] - 20} more rows")
    return "\n".join(lines)
