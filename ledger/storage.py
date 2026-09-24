import datetime
import os
import sqlite3
import subprocess  # nosec B404
import shutil
import logging
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


def to_paise(val):
    if val is None:
        return 0
    if isinstance(val, int) and val > 10000000:
        return val
    d = Decimal(str(val))
    return int((d * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _set_restrictive_permissions(path):
    try:
        p = Path(path)
        if p.exists() and p.is_file() and os.name != 'nt':
            p.chmod(0o600)
        if p.parent.exists() and os.name != 'nt':
            p.parent.chmod(0o700)
    except (OSError, NotImplementedError):
        pass

    if os.name == 'nt':
        try:
            user = os.environ.get('USERNAME')
            p = Path(path)
            icacls_bin = shutil.which('icacls') or r'C:\Windows\System32\icacls.exe'
            if user and p.exists() and p.is_file() and icacls_bin:
                proc = subprocess.run(  # nosec B603 B607
                    [icacls_bin, str(p), '/grant:r', f'{user}:F'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if proc.returncode != 0:
                    logger.warning(f"icacls failed to set ACL on local database file with code {proc.returncode}")
        except Exception as exc:
            logger.warning(f"Could not apply local file permissions: {exc}")


def create_verified_backup(db, db_path):
    db_p = Path(db_path)
    if not (db_p.exists() and db_p.is_file()):
        return None
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bak_path = db_p.parent / f"{db_p.name}.bak_{ts}"
    try:
        b_conn = sqlite3.connect(bak_path)
        try:
            db.backup(b_conn)
        finally:
            b_conn.close()

        check_uri = f"file:{bak_path.resolve().as_posix()}?mode=ro"
        check_conn = sqlite3.connect(check_uri, uri=True)
        try:
            res = check_conn.execute('PRAGMA integrity_check').fetchone()
        finally:
            check_conn.close()

        if not res or res[0] != 'ok':
            raise RuntimeError(f"Backup integrity check failed for {bak_path}")
        return bak_path
    except Exception as exc:
        raise RuntimeError(f"Database backup creation/verification failed prior to migration: {exc}") from exc


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY, name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                invoice_number TEXT NOT NULL, amount INTEGER NOT NULL, due_date TEXT NOT NULL,
                UNIQUE(customer_id, invoice_number)
            );
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                invoice_number TEXT NOT NULL, amount INTEGER NOT NULL,
                invoice_id INTEGER REFERENCES invoices(id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_customer_number 
            ON invoices(customer_id, invoice_number);
            CREATE TABLE IF NOT EXISTS import_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                kind TEXT NOT NULL,
                source_filename TEXT,
                sha256 TEXT NOT NULL,
                imported_count INTEGER NOT NULL,
                skipped_count INTEGER NOT NULL,
                rejected_count INTEGER NOT NULL,
                error_summary TEXT
            );
        ''')
        _migrate_if_needed(db, path)
        _set_restrictive_permissions(path)
        return db
    except Exception:
        db.close()
        raise


def _migrate_if_needed(db, db_path):
    version = db.execute('PRAGMA user_version').fetchone()[0]
    inv_info = db.execute("PRAGMA table_info(invoices)").fetchall()
    amount_col_type = next((col['type'].upper() for col in inv_info if col['name'] == 'amount'), '')
    
    inv_rows = db.execute('SELECT id, customer_id, invoice_number, amount, due_date FROM invoices').fetchall()
    pay_rows = db.execute('SELECT payment_id, customer_id, invoice_number, amount, invoice_id FROM payments').fetchall()
    cust_rows = db.execute('SELECT customer_id, name FROM customers').fetchall()
    
    needs_migration = (version < 1) or (amount_col_type != 'INTEGER') or any(isinstance(r['amount'], float) for r in inv_rows) or any(isinstance(r['amount'], float) for r in pay_rows)

    if needs_migration:
        snap_customers = set((r['customer_id'], r['name']) for r in cust_rows)
        snap_invoices = set((r['id'], r['customer_id'], r['invoice_number'], to_paise(r['amount']), str(r['due_date'])) for r in inv_rows)
        snap_payments = set((r['payment_id'], r['customer_id'], r['invoice_number'], to_paise(r['amount']), r['invoice_id']) for r in pay_rows)
        snap_unmatched_pay_ids = set(r['payment_id'] for r in pay_rows if r['invoice_id'] is None)

        create_verified_backup(db, db_path)

        inv_data = [(r['id'], r['customer_id'], r['invoice_number'], to_paise(r['amount']), r['due_date']) for r in inv_rows]
        pay_data = [(r['payment_id'], r['customer_id'], r['invoice_number'], to_paise(r['amount']), r['invoice_id']) for r in pay_rows]

        db.execute('BEGIN IMMEDIATE')
        try:
            db.execute('''
                CREATE TABLE IF NOT EXISTS _new_invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    invoice_number TEXT NOT NULL, amount INTEGER NOT NULL, due_date TEXT NOT NULL,
                    UNIQUE(customer_id, invoice_number)
                )
            ''')
            db.execute('''
                CREATE TABLE IF NOT EXISTS _new_payments (
                    payment_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
                    invoice_number TEXT NOT NULL, amount INTEGER NOT NULL,
                    invoice_id INTEGER REFERENCES _new_invoices(id)
                )
            ''')

            db.executemany('INSERT OR REPLACE INTO _new_invoices (id, customer_id, invoice_number, amount, due_date) VALUES (?, ?, ?, ?, ?)', inv_data)
            db.executemany('INSERT OR REPLACE INTO _new_payments (payment_id, customer_id, invoice_number, amount, invoice_id) VALUES (?, ?, ?, ?, ?)', pay_data)

            db.execute('DROP TABLE payments')
            db.execute('DROP TABLE invoices')
            db.execute('ALTER TABLE _new_invoices RENAME TO invoices')
            db.execute('ALTER TABLE _new_payments RENAME TO payments')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_customer_number ON invoices(customer_id, invoice_number)')
            db.execute('PRAGMA user_version = 1')

            post_cust = set((r['customer_id'], r['name']) for r in db.execute('SELECT customer_id, name FROM customers').fetchall())
            post_inv = set((r['id'], r['customer_id'], r['invoice_number'], int(r['amount']), str(r['due_date'])) for r in db.execute('SELECT id, customer_id, invoice_number, amount, due_date FROM invoices').fetchall())
            post_pay = set((r['payment_id'], r['customer_id'], r['invoice_number'], int(r['amount']), r['invoice_id']) for r in db.execute('SELECT payment_id, customer_id, invoice_number, amount, invoice_id FROM payments').fetchall())
            post_unmatched_pay_ids = set(r['payment_id'] for r in db.execute('SELECT payment_id FROM payments WHERE invoice_id IS NULL').fetchall())

            if snap_customers != post_cust or snap_invoices != post_inv or snap_payments != post_pay or snap_unmatched_pay_ids != post_unmatched_pay_ids:
                raise RuntimeError("Migration verification failed: customer, invoice, or payment records differ post-migration.")

            db.commit()
        except Exception:
            db.rollback()
            raise
    else:
        db.execute('PRAGMA user_version = 1')


def seed(db):
    if db.execute('SELECT COUNT(*) FROM customers').fetchone()[0]:
        return
    with db:
        db.executemany('INSERT INTO customers VALUES (?, ?)', [
            ('HARBOR', 'Harbor Design'), ('MAPLE', 'Maple Studio'),
            ('NORTH', 'North Workshop'),
        ])
        db.executemany('''INSERT INTO invoices
            (customer_id, invoice_number, amount, due_date) VALUES (?, ?, ?, ?)''', [
            ('HARBOR', 'INV-100', to_paise('1250.00'), '2026-09-01'),
            ('MAPLE', 'INV-200', to_paise('1250.00'), '2026-09-02'),
            ('NORTH', 'INV-300', to_paise('19.99'), '2026-09-03'),
            ('HARBOR', 'INV-101', to_paise('300.00'), '2026-09-04'),
            ('MAPLE', 'INV-201', to_paise('600.00'), '2026-09-05'),
            ('NORTH', 'INV-301', to_paise('100.00'), '2026-09-06'),
        ])
        for pid, customer, number, amount in [
            ('SEED-1', 'HARBOR', 'INV-101', to_paise('300.00')),
            ('SEED-2', 'NORTH', 'INV-300', to_paise('10.00')),
        ]:
            iid = db.execute('SELECT id FROM invoices WHERE customer_id=? AND invoice_number=?',
                             (customer, number)).fetchone()[0]
            db.execute('INSERT INTO payments VALUES (?, ?, ?, ?, ?)',
                       (pid, customer, number, amount, iid))


def invoice_by_key(db, customer_id, invoice_number):
    return db.execute('SELECT * FROM invoices WHERE customer_id=? AND invoice_number=? ORDER BY id',
                      (customer_id, invoice_number)).fetchone()


def insert_invoice(db, row):
    old = invoice_by_key(db, row['customer_id'], row['invoice_number'])
    if old:
        if (int(old['amount']) == int(row['amount']) and
                str(old['due_date']) == str(row['due_date'])):
            return 'skipped'
        raise ValueError(f"Invoice '{row['customer_id']}/{row['invoice_number']}' already exists with different details")
    db.execute('''INSERT INTO invoices (customer_id, invoice_number, amount, due_date)
                  VALUES (:customer_id, :invoice_number, :amount, :due_date)''', row)
    return 'imported'


def insert_payment(db, row, invoice_id):
    old = db.execute('SELECT * FROM payments WHERE payment_id=?', (row['payment_id'],)).fetchone()
    if old:
        if (old['customer_id'] == row['customer_id'] and
                old['invoice_number'] == row['invoice_number'] and
                int(old['amount']) == int(row['amount'])):
            return 'skipped'
        raise ValueError(f"Payment ID '{row['payment_id']}' already exists with different details")
    db.execute('''INSERT INTO payments (payment_id, customer_id, invoice_number, amount, invoice_id)
                  VALUES (:payment_id, :customer_id, :invoice_number, :amount, :invoice_id)''',
               {**row, 'invoice_id': invoice_id})
    return 'imported'


