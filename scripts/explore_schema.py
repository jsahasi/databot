"""Explore ON24 PostgreSQL schema: columns, row counts, and sample rows."""
import tempfile
import psycopg2

ENV_FILE = r'C:\Users\jayesh.sahasi\gitlab\databot\.env.local'

def extract(key: str, raw: str) -> str:
    for line in raw.splitlines():
        if line.startswith(key + '='):
            val = line[len(key)+1:].strip()
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            val = val.replace('\\n', '\n')
            return val
    return ''

raw = open(ENV_FILE, encoding='utf-8').read()

ca_pem   = extract('DB_PG_SSL_ROOT_CERT_CONTENT', raw)
cert_pem = extract('DB_PG_SSL_CERT_CONTENT', raw)
key_pem  = extract('DB_PG_SSL_KEY_CONTENT', raw)

tmp = tempfile.mkdtemp()
ca_path   = tmp + '/ca.pem'
cert_path = tmp + '/client.crt'
key_path  = tmp + '/client.key'

with open(ca_path,   'w', newline='\n') as f: f.write(ca_pem)
with open(cert_path, 'w', newline='\n') as f: f.write(cert_pem)
with open(key_path,  'w', newline='\n') as f: f.write(key_pem)

conn = psycopg2.connect(
    host='10.3.7.233', port=5459, dbname='on24master',
    user='ON24_RO', password='welcome1234!',
    sslmode='verify-ca',
    sslrootcert=ca_path,
    sslcert=cert_path,
    sslkey=key_path,
)
conn.autocommit = True
cur = conn.cursor()

TABLES = [
    'event', 'event_info', 'event_user', 'event_user_info',
    'event_session', 'event_user_x_answer', 'question', 'question_x_answer',
    'dw_attendee', 'dw_lead', 'dw_lead_user', 'resource_hit_track',
    'content_hit_track_summary', 'display_element', 'client_user',
    'client_hierarchy', 'survey_attempts',
]

# First, get table sizes to decide whether to use TABLESAMPLE
print("=== Getting table sizes ===")
size_map = {}
try:
    cur.execute("""
        SELECT tablename,
               pg_total_relation_size('on24master.' || quote_ident(tablename)) AS size_bytes
        FROM pg_tables
        WHERE schemaname = 'on24master'
          AND tablename = ANY(%s)
    """, (TABLES,))
    for row in cur.fetchall():
        size_map[row[0]] = row[1]
        print(f"  {row[0]}: {row[1]:,} bytes ({row[1]/1e9:.2f} GB)")
except Exception as e:
    print(f"  Could not get sizes: {e}")

print()

# ── Query A: Column info ──────────────────────────────────────────────────────
print("=" * 70)
print("QUERY A — COLUMN DEFINITIONS")
print("=" * 70)

for table in TABLES:
    print(f"\n=== TABLE: {table} ===")
    try:
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'on24master'
              AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        rows = cur.fetchall()
        if not rows:
            print("  (no columns found — table may not exist)")
        else:
            print(f"  {'column_name':<40} {'data_type':<30} {'max_len'}")
            print(f"  {'-'*40} {'-'*30} {'-'*7}")
            for col_name, data_type, max_len in rows:
                ml = str(max_len) if max_len is not None else ''
                print(f"  {col_name:<40} {data_type:<30} {ml}")
    except Exception as e:
        print(f"  ERROR: {e}")

print()

# ── Query B: Row counts ───────────────────────────────────────────────────────
print("=" * 70)
print("QUERY B — ROW COUNTS")
print("=" * 70)
print()

TEN_GB = 10 * 1_000_000_000

for table in TABLES:
    size_bytes = size_map.get(table, 0)
    try:
        if size_bytes > TEN_GB:
            cur.execute(f"SELECT COUNT(*) * 1000 AS approx_count FROM on24master.{table} TABLESAMPLE SYSTEM(0.1)")
            count = cur.fetchone()[0]
            print(f"{table}: ~{count:,} rows  (TABLESAMPLE estimate, table >{size_bytes/1e9:.1f}GB)")
        else:
            cur.execute(f"SELECT COUNT(*) FROM on24master.{table}")
            count = cur.fetchone()[0]
            print(f"{table}: ~{count:,} rows")
    except Exception as e:
        print(f"{table}: ERROR — {e}")

print()

# ── Query C: Sample rows from event ──────────────────────────────────────────
print("=" * 70)
print("QUERY C — SAMPLE 3 ROWS FROM event")
print("=" * 70)
print()

try:
    cur.execute("SELECT * FROM on24master.event LIMIT 3")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"--- Row {i} ---")
        for col, val in zip(cols, row):
            print(f"  {col}: {val!r}")
        print()
except Exception as e:
    print(f"ERROR: {e}")

# ── Query D: Sample rows from event_user (first 20 cols) ─────────────────────
print("=" * 70)
print("QUERY D — SAMPLE 3 ROWS FROM event_user (first 20 columns)")
print("=" * 70)
print()

try:
    # First get column names to pick the first 20
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'on24master'
          AND table_name = 'event_user'
        ORDER BY ordinal_position
        LIMIT 20
    """)
    col_names = [r[0] for r in cur.fetchall()]
    col_list = ', '.join(f'"{c}"' for c in col_names)
    cur.execute(f"SELECT {col_list} FROM on24master.event_user LIMIT 3")
    cols = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"--- Row {i} ---")
        for col, val in zip(cols, row):
            print(f"  {col}: {val!r}")
        print()
except Exception as e:
    print(f"ERROR: {e}")

conn.close()
print("Done.")
