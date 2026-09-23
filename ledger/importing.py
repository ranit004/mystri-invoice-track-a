import csv
import hashlib
import io
import json
import datetime
import re
from pathlib import Path
from .validation import HEADERS, normalize, classify_error
from .storage import insert_invoice, insert_payment
from .matching import find_invoice

MAX_ROWS = 5000
MAX_FIELD_LEN = 256


def _sanitize_filename(val):
    if not val or not isinstance(val, str):
        return None
    name = Path(val).name
    name = re.sub(r'[\x00-\x1f\x7f]', '', name).strip()
    if not name or name in ('.', '..'):
        return None
    return name[:64]


def import_csv(db, text, kind, filename=None):
    if kind not in HEADERS:
        raise ValueError('Unknown import kind')
    safe_filename = _sanitize_filename(filename)
    sha256_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if reader.fieldnames != HEADERS[kind]:
        raise ValueError('Expected CSV header: ' + ','.join(HEADERS[kind]))
    
    customers = {r[0] for r in db.execute('SELECT customer_id FROM customers')}
    result = {'imported': 0, 'skipped': 0, 'rejected': 0, 'errors': []}
    
    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise ValueError(f'CSV input exceeds maximum limit of {MAX_ROWS} rows')

    with db:
        for line, raw_row in enumerate(rows, start=2):
            try:
                for k, v in raw_row.items():
                    if v and len(str(v)) > MAX_FIELD_LEN:
                        raise ValueError(f'CSV cell at line {line} field "{k}" exceeds maximum length of {MAX_FIELD_LEN} characters')
                row = normalize(raw_row, kind, customers)
                if kind == 'invoices':
                    outcome = insert_invoice(db, row)
                else:
                    outcome = insert_payment(db, row, find_invoice(db, row))
                result[outcome] += 1
            except ValueError as exc:
                result['rejected'] += 1
                result['errors'].append({'line': line, 'reason': str(exc)})

        # Transactional privacy-safe audit log
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        audit_errors = []
        for err in result['errors']:
            cl = classify_error(err['reason'])
            item = {'line': err['line'], 'code': cl['code']}
            if cl['field']:
                item['field'] = cl['field']
            audit_errors.append(item)

        err_summary = json.dumps(audit_errors[:10])[:500] if audit_errors else None
        db.execute('''
            INSERT INTO import_audit 
            (timestamp, kind, source_filename, sha256, imported_count, skipped_count, rejected_count, error_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ts, kind, safe_filename, sha256_hash, result['imported'], result['skipped'], result['rejected'], err_summary))

    return result

