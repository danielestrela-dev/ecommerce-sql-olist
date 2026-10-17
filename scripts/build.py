"""Reproduz toda a análise usando apenas a biblioteca padrão do Python."""
import csv
import hashlib
import io
import json
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
SOURCE = 'https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce'
TABLES = {'orders': 'olist_orders_dataset.csv', 'reviews': 'olist_order_reviews_dataset.csv',
          'customers': 'olist_customers_dataset.csv', 'items': 'olist_order_items_dataset.csv',
          'payments': 'olist_order_payments_dataset.csv'}


def run():
    RAW.mkdir(parents=True, exist_ok=True)
    archive = RAW / 'olist.zip'
    if not archive.exists():
        print('Baixando base pública Olist...')
        urllib.request.urlretrieve(SOURCE, archive)
    if not zipfile.is_zipfile(archive):
        raise ValueError('O download não é um ZIP. Baixe a base na página oficial do Kaggle e salve em data/raw/olist.zip.')
    con = sqlite3.connect(ROOT / 'data' / 'olist.sqlite')
    con.row_factory = sqlite3.Row
    counts, hashes = {}, {}
    with zipfile.ZipFile(archive) as z:
        for table, filename in TABLES.items():
            data = z.read(filename)
            hashes[filename] = hashlib.sha256(data).hexdigest()
            reader = csv.reader(io.StringIO(data.decode('utf-8-sig')))
            header = next(reader)
            con.execute(f'DROP TABLE IF EXISTS {table}')
            cols = ','.join(f'"{col}" TEXT' for col in header)
            con.execute(f'CREATE TABLE {table} ({cols})')
            con.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in header)})',
                            ([v if v != '' else None for v in row] for row in reader))
            counts[table] = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            con.execute(f'CREATE INDEX idx_{table}_order ON {table} ({"customer_id" if table == "customers" else "order_id"})')
    con.executescript((ROOT / 'sql/01_model.sql').read_text(encoding='utf-8'))
    # Materializa para acelerar consultas; a definição canônica continua em SQL.
    con.execute('DROP TABLE IF EXISTS analysis_orders')
    con.execute('CREATE TABLE analysis_orders AS SELECT * FROM fact_orders')
    def query(sql):
        return [dict(r) for r in con.execute(sql.replace('fact_orders', 'analysis_orders'))]
    n = query('SELECT COUNT(*) n, COUNT(DISTINCT order_id) unique_n FROM fact_orders')[0]
    assert n['n'] == n['unique_n'], 'Junção duplicou pedidos'
    assert query('SELECT COUNT(*) n FROM fact_orders WHERE score NOT BETWEEN 1 AND 5')[0]['n'] == 0
    for table, key in [('orders','order_id'), ('customers','customer_id')]:
        assert con.execute(f'SELECT COUNT(*) - COUNT(DISTINCT {key}) FROM {table}').fetchone()[0] == 0
    reviewed = query('SELECT COUNT(score) n FROM fact_orders')[0]['n']
    groups = query('''SELECT month, state, is_late, COUNT(*) orders, COUNT(score) reviewed,
       COALESCE(SUM(score),0) score_sum, SUM(CASE WHEN score<=2 THEN 1 ELSE 0 END) low_scores,
       SUM(delivery_days) delivery_sum, SUM(merchandise_value) merchandise_value
       FROM fact_orders GROUP BY month, state, is_late ORDER BY month,state,is_late''')
    assert sum(g['orders'] for g in groups) == n['n']
    assert sum(g['reviewed'] for g in groups) == reviewed
    comparisons = query('''SELECT is_late, COUNT(*) orders, COUNT(score) reviewed,
       AVG(score) avg_score, 100.0*SUM(CASE WHEN score<=2 THEN 1 ELSE 0 END)/COUNT(score) low_pct
       FROM fact_orders GROUP BY is_late''')
    sensitivity = query('''SELECT is_late, COUNT(*) reviewed, AVG(score) avg_score,
       100.0*SUM(score<=2)/COUNT(*) low_pct FROM fact_orders
       WHERE score IS NOT NULL AND post_delivery_review=1 GROUP BY is_late''')
    buckets = query('''SELECT CASE WHEN is_late=0 THEN 'No prazo' WHEN delay_days<=3 THEN '1–3 dias'
       WHEN delay_days<=7 THEN '4–7 dias' ELSE '8+ dias' END bucket,
       COUNT(*) orders, COUNT(score) reviewed, AVG(score) avg_score
       FROM fact_orders GROUP BY bucket ORDER BY MIN(delay_days)''')
    quality = {'raw_counts': counts, 'valid_delivered_orders': n['n'], 'reviewed_orders': reviewed,
      'delivered_raw': con.execute("SELECT COUNT(*) FROM orders WHERE order_status='delivered'").fetchone()[0],
      'extra_review_rows': con.execute('SELECT COUNT(*)-COUNT(DISTINCT order_id) FROM reviews').fetchone()[0],
      'purchase_range': query('SELECT MIN(purchased_on) start, MAX(purchased_on) end FROM fact_orders')[0]}
    result = {'source': 'https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce',
      'quality': quality, 'groups': groups, 'comparison': comparisons, 'sensitivity': sensitivity, 'buckets': buckets}
    docs = ROOT / 'docs'
    docs.mkdir(exist_ok=True)
    (docs / 'data.json').write_text(json.dumps(result, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    (ROOT / 'data' / 'manifest.json').write_text(json.dumps({'files_sha256':hashes,'quality':quality}, ensure_ascii=False, indent=2),encoding='utf-8')
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    statements, buffer = [], ''
    for line in (ROOT / 'sql/02_analysis.sql').read_text(encoding='utf-8').splitlines(True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer)
            buffer = ''
    for idx, statement in enumerate(statements, 1):
        if not statement.strip():
            continue
        rows = query(statement)
        if rows:
            with (out / f'{idx:02d}_analysis.csv').open('w',encoding='utf-8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    con.commit()
    con.close()
    print(json.dumps({'quality':quality,'comparison':comparisons,'sensitivity':sensitivity,'buckets':buckets},ensure_ascii=False,indent=2))
    print('Verificações passaram: unicidade, notas válidas e reconciliação dos agregados.')


if __name__ == '__main__':
    run()
