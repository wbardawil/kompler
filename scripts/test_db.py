"""Test database connection."""
import psycopg

try:
    conn = psycopg.connect(
        "host=127.0.0.1 port=5432 dbname=kompler user=kompler password=devpass123"
    )
    cur = conn.execute('SELECT 1 as test')
    print(f"CONNECTED! Result: {cur.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"Failed with DSN string: {e}")

# Try with conninfo
try:
    conn = psycopg.connect(conninfo="host=127.0.0.1 port=5432 dbname=kompler user=kompler password=devpass123")
    cur = conn.execute('SELECT 1')
    print(f"CONNECTED via conninfo! Result: {cur.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"Failed with conninfo: {e}")
