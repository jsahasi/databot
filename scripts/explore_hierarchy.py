"""Explore client_hierarchy structure for client 10710."""
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
            return val.replace('\\n', '\n')
    return ''

raw = open(ENV_FILE, encoding='utf-8').read()
tmp = tempfile.mkdtemp()
for name, key in [('ca.pem','DB_PG_SSL_ROOT_CERT_CONTENT'),
                   ('client.crt','DB_PG_SSL_CERT_CONTENT'),
                   ('client.key','DB_PG_SSL_KEY_CONTENT')]:
    with open(f'{tmp}/{name}', 'w', newline='\n') as f:
        f.write(extract(key, raw))

conn = psycopg2.connect(
    host='10.3.7.233', port=5459, dbname='on24master', user='ON24_RO', password='welcome1234!',
    sslmode='verify-ca', sslrootcert=f'{tmp}/ca.pem',
    sslcert=f'{tmp}/client.crt', sslkey=f'{tmp}/client.key',
)
cur = conn.cursor()

print("=== client_hierarchy columns ===")
cur.execute("""SELECT column_name, data_type FROM information_schema.columns
    WHERE table_schema='on24master' AND table_name='client_hierarchy' ORDER BY ordinal_position""")
for row in cur.fetchall():
    print(' ', row)

print("\n=== Sample 10 rows ===")
cur.execute("SELECT * FROM on24master.client_hierarchy LIMIT 10")
for row in cur.fetchall():
    print(' ', row)

print("\n=== 10710 as parent (has sub-clients?) ===")
cur.execute("SELECT * FROM on24master.client_hierarchy WHERE client_id = 10710")
rows = cur.fetchall()
print(f"  {len(rows)} rows")
for r in rows:
    print(' ', r)

print("\n=== 10710 as child (belongs to a parent?) ===")
cur.execute("SELECT * FROM on24master.client_hierarchy WHERE sub_client_id = 10710")
rows = cur.fetchall()
print(f"  {len(rows)} rows")
for r in rows:
    print(' ', r)

print("\n=== Full hierarchy tree under 10710 (recursive, up to 5 levels) ===")
cur.execute("""
    WITH RECURSIVE hierarchy AS (
        SELECT client_id, sub_client_id, 1 AS depth
        FROM on24master.client_hierarchy
        WHERE client_id = 10710
        UNION ALL
        SELECT ch.client_id, ch.sub_client_id, h.depth + 1
        FROM on24master.client_hierarchy ch
        JOIN hierarchy h ON ch.client_id = h.sub_client_id
        WHERE h.depth < 5
    )
    SELECT * FROM hierarchy ORDER BY depth, sub_client_id
""")
rows = cur.fetchall()
print(f"  {len(rows)} total sub-client relationships")
for r in rows:
    print(' ', r)

print("\n=== Ancestors of 10710 (is it a sub-client of something?) ===")
cur.execute("""
    WITH RECURSIVE ancestors AS (
        SELECT client_id, sub_client_id, 1 AS depth
        FROM on24master.client_hierarchy
        WHERE sub_client_id = 10710
        UNION ALL
        SELECT ch.client_id, ch.sub_client_id, a.depth + 1
        FROM on24master.client_hierarchy ch
        JOIN ancestors a ON ch.sub_client_id = a.client_id
        WHERE a.depth < 5
    )
    SELECT * FROM ancestors ORDER BY depth
""")
rows = cur.fetchall()
print(f"  {len(rows)} ancestors")
for r in rows:
    print(' ', r)

print("\n=== Direct events for client 10710 ===")
cur.execute("SELECT COUNT(*) FROM on24master.event WHERE client_id = 10710")
print('  Count:', cur.fetchone()[0])

print("\n=== All client_ids in the full hierarchy under 10710 ===")
cur.execute("""
    WITH RECURSIVE hierarchy AS (
        SELECT sub_client_id AS cid FROM on24master.client_hierarchy WHERE client_id = 10710
        UNION
        SELECT ch.sub_client_id FROM on24master.client_hierarchy ch
        JOIN hierarchy h ON ch.client_id = h.cid
    )
    SELECT cid FROM hierarchy ORDER BY cid
""")
rows = cur.fetchall()
all_cids = [r[0] for r in rows]
print(f"  Sub-client IDs: {all_cids}")

if all_cids:
    print("\n=== Events across entire hierarchy (10710 + all sub-clients) ===")
    all_ids = [10710] + all_cids
    placeholders = ','.join(str(x) for x in all_ids)
    cur.execute(f"SELECT client_id, COUNT(*) FROM on24master.event WHERE client_id IN ({placeholders}) GROUP BY client_id ORDER BY client_id")
    for row in cur.fetchall():
        print(f'  client_id={row[0]}: {row[1]} events')

conn.close()
print("\nDone.")
