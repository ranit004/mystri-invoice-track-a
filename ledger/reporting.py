import csv
import io


def _invoice_rows_with_paise(db, status='all'):
    """Build invoice rows including the internal `_bal_paise` field.

    Internal helper only: `_bal_paise` is exact-precision plumbing for
    status/sum math and must never reach an HTTP response directly.
    Public callers should go through `invoices()`, which strips it.
    """
    if status not in ('all', 'open', 'paid'):
        raise ValueError('status must be all, open or paid')
    data = db.execute('''
        SELECT i.id, i.customer_id, c.name AS customer_name, i.invoice_number,
               i.amount, i.due_date, COALESCE(SUM(p.amount), 0) AS paid
        FROM invoices i JOIN customers c ON c.customer_id=i.customer_id
        LEFT JOIN payments p ON p.invoice_id=i.id
        GROUP BY i.id ORDER BY i.id
    ''').fetchall()
    result = []
    for row in data:
        item = dict(row)
        amt_paise = int(item['amount'])
        paid_paise = int(item['paid'])
        bal_paise = amt_paise - paid_paise

        item['amount'] = round(amt_paise / 100.0, 2)
        item['paid'] = round(paid_paise / 100.0, 2)
        item['balance'] = round(bal_paise / 100.0, 2)
        item['_bal_paise'] = bal_paise
        item['status'] = 'paid' if bal_paise <= 0 else 'open'
        result.append(item)
    if status != 'all':
        result = [r for r in result if r['status'] == status]
    return result


def invoices(db, status='all'):
    """Public invoice listing. Never exposes internal `_bal_paise`."""
    rows = _invoice_rows_with_paise(db, status)
    for r in rows:
        r.pop('_bal_paise', None)
    return rows


def overview(db):
    rows = _invoice_rows_with_paise(db)
    unmatched = [{
        'payment_id': r['payment_id'],
        'customer_id': r['customer_id'],
        'invoice_number': r['invoice_number'],
        'amount': round(int(r['amount']) / 100.0, 2)
    } for r in db.execute('''SELECT payment_id, customer_id,
        invoice_number, amount FROM payments WHERE invoice_id IS NULL ORDER BY payment_id''')]

    outstanding_paise = sum(r['_bal_paise'] for r in rows if r['_bal_paise'] > 0)
    for r in rows:
        r.pop('_bal_paise', None)

    return {'invoices': rows, 'unmatched_payments': unmatched, 'summary': {
        'invoice_count': len(rows),
        'open_count': sum(r['status'] == 'open' for r in rows),
        'outstanding': round(outstanding_paise / 100.0, 2),
    }}


def _sanitize_csv_text(val):
    s = str(val)
    if s and s[0] in ('=', '+', '-', '@'):
        return "'" + s
    return s


def export_csv(db):
    output = io.StringIO(newline='')
    fields = ['customer_id', 'invoice_number', 'amount', 'paid', 'balance', 'status']
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in invoices(db):
        item = {}
        for k in fields:
            if k in ('amount', 'paid', 'balance'):
                item[k] = f"{row[k]:.2f}"
            else:
                item[k] = _sanitize_csv_text(row[k])
        writer.writerow(item)
    return output.getvalue()


def get_import_audit(db):
    rows = db.execute('''
        SELECT id, timestamp, kind, source_filename, sha256,
               imported_count, skipped_count, rejected_count, error_summary
        FROM import_audit ORDER BY id DESC
    ''').fetchall()
    return [dict(r) for r in rows]