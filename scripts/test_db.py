"""Quick script to test ON24 QA DB connection and list tables by size."""
import tempfile
import psycopg2

ENV_FILE = r'C:\Users\jayesh.sahasi\gitlab\databot\.env.local'

def extract(key: str, raw: str) -> str:
    for line in raw.splitlines():
        if line.startswith(key + '='):
            val = line[len(key)+1:].strip()
            # Strip surrounding quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            # Unescape literal \n
            val = val.replace('\\n', '\n')
            return val
    return ''

raw = open(ENV_FILE, encoding='utf-8').read()

ca_pem   = extract('DB_PG_SSL_ROOT_CERT_CONTENT', raw)
cert_pem = extract('DB_PG_SSL_CERT_CONTENT', raw)
key_pem  = extract('DB_PG_SSL_KEY_CONTENT', raw)

print('CA length:', len(ca_pem), '| starts:', ca_pem[:27])

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

cur = conn.cursor()
cur.execute("""
    SELECT schemaname, tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
        pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog','information_schema')
      AND has_schema_privilege(current_user, schemaname, 'USAGE')
      AND has_table_privilege(current_user, schemaname||'.'||tablename, 'SELECT')
    ORDER BY size_bytes DESC
    LIMIT 80
""")

rows = cur.fetchall()
print(f"\n{'Schema':<20} {'Table':<50} {'Size':>10}")
print('-' * 82)
for schema, table, size, _ in rows:
    print(f"{schema:<20} {table:<50} {size:>10}")

conn.close()
