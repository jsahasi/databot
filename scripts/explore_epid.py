"""Explore event_info.epid structure and client_property tables."""
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

print("=== Tables with 'property', 'profile', 'param', 'field' in name ===")
cur.execute("""
    SELECT tablename FROM pg_tables WHERE schemaname='on24master'
    AND (tablename LIKE '%property%' OR tablename LIKE '%profile%'
         OR tablename LIKE '%param%' OR tablename LIKE '%field%'
         OR tablename LIKE '%attribute%')
    ORDER BY tablename
""")
for r in cur.fetchall():
    print(' ', r[0])

print("\n=== event_profile columns ===")
cur.execute("""SELECT column_name, data_type FROM information_schema.columns
    WHERE table_schema='on24master' AND table_name='event_profile'
    ORDER BY ordinal_position""")
rows = cur.fetchall()
for r in rows: print(' ', r)

print("\n=== Distinct epid values in event_info for client 10710 (top 50 by freq) ===")
cur.execute("""
    SELECT ei.epid, COUNT(*) as freq
    FROM on24master.event_info ei
    JOIN on24master.event e ON ei.event_id = e.event_id
    WHERE e.client_id = 10710
    GROUP BY ei.epid
    ORDER BY freq DESC
    LIMIT 50
""")
for r in cur.fetchall():
    print(f'  epid={r[0]:5d}  count={r[1]}')

print("\n=== event_info for one recent client 10710 event (all epid+value) ===")
cur.execute("""
    SELECT ei.epid, LEFT(CAST(ei.value AS text), 120) as value
    FROM on24master.event_info ei
    WHERE ei.event_id = (
        SELECT event_id FROM on24master.event
        WHERE client_id = 10710 AND last_modified IS NOT NULL
        ORDER BY last_modified DESC LIMIT 1
    )
    ORDER BY ei.epid
""")
for r in cur.fetchall():
    print(f'  epid={r[0]:5d}  {r[1]}')

print("\n=== event_profile sample ===")
cur.execute("""SELECT * FROM on24master.event_profile LIMIT 5""")
cols = [d[0] for d in cur.description]
print(' ', cols)
for r in cur.fetchall():
    print(' ', dict(zip(cols, r)))

print("\n=== display_profile columns ===")
cur.execute("""SELECT column_name, data_type FROM information_schema.columns
    WHERE table_schema='on24master' AND table_name='display_profile'
    ORDER BY ordinal_position""")
for r in cur.fetchall(): print(' ', r)

print("\n=== client_property_info columns ===")
cur.execute("""SELECT column_name, data_type FROM information_schema.columns
    WHERE table_schema='on24master' AND table_name='client_property_info'
    ORDER BY ordinal_position""")
rows = cur.fetchall()
for r in rows: print(' ', r)

if rows:
    print("\n=== client_property_info sample for client 10710 ===")
    cur.execute("""SELECT * FROM on24master.client_property_info
        WHERE client_id = 10710 LIMIT 20""")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        print(' ', dict(zip(cols, r)))

conn.close()
print("\nDone.")
