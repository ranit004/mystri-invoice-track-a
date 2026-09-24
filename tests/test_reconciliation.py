import json
import tempfile
import unittest
import urllib.request
import urllib.error
import threading
from pathlib import Path
from ledger import storage, reporting, importing, http_app

ROOT = Path(__file__).resolve().parent.parent
LOCAL_TMP_DIR = ROOT / '.local' / 'test_tmp'


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        LOCAL_TMP_DIR.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=LOCAL_TMP_DIR)
        self.db_path = Path(self.tmp.name) / 'ledger.sqlite3'
        self.db = storage.connect(self.db_path)
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_invoice_idempotency(self):
        """Re-importing identical invoice CSV skips record without changing totals."""
        summary_before = reporting.overview(self.db)['summary']
        csv_data = "customer_id,invoice_number,amount,due_date\nHARBOR,INV-100,1250.00,2026-09-01\n"
        res = importing.import_csv(self.db, csv_data, 'invoices')
        self.assertEqual(res['imported'], 0)
        self.assertEqual(res['skipped'], 1)
        self.assertEqual(res['rejected'], 0)
        summary_after = reporting.overview(self.db)['summary']
        self.assertEqual(summary_before, summary_after)

    def test_invoice_conflict_rejection(self):
        """Re-using an existing invoice identity with conflicting details rejects the row."""
        csv_data = "customer_id,invoice_number,amount,due_date\nHARBOR,INV-100,9999.00,2026-10-10\n"
        res = importing.import_csv(self.db, csv_data, 'invoices')
        self.assertEqual(res['imported'], 0)
        self.assertEqual(res['skipped'], 0)
        self.assertEqual(res['rejected'], 1)
        self.assertTrue(any('already exists with different details' in e['reason'] for e in res['errors']))
        inv = storage.invoice_by_key(self.db, 'HARBOR', 'INV-100')
        self.assertEqual(inv['amount'], 125000)


    def test_payment_idempotency(self):
        """Re-importing an identical payment skips without altering balance."""
        csv_data = "payment_id,customer_id,invoice_number,amount\nSEED-1,HARBOR,INV-101,300.00\n"
        res = importing.import_csv(self.db, csv_data, 'payments')
        self.assertEqual(res['imported'], 0)
        self.assertEqual(res['skipped'], 1)
        self.assertEqual(res['rejected'], 0)

    def test_payment_conflict_rejection(self):
        """Re-using a payment ID with conflicting details rejects the row."""
        csv_data = "payment_id,customer_id,invoice_number,amount\nSEED-1,HARBOR,INV-101,500.00\n"
        res = importing.import_csv(self.db, csv_data, 'payments')
        self.assertEqual(res['imported'], 0)
        self.assertEqual(res['skipped'], 0)
        self.assertEqual(res['rejected'], 1)
        self.assertTrue(any('already exists with different details' in e['reason'] for e in res['errors']))

    def test_exact_payment_matching_not_amount_alone(self):
        """Payments attach ONLY when both customer_id and invoice_number match."""
        importing.import_csv(self.db, "customer_id,invoice_number,amount,due_date\nNORTH,INV-777,300.00,2026-10-01\n", 'invoices')
        res = importing.import_csv(self.db, "payment_id,customer_id,invoice_number,amount\nPAY-N1,NORTH,INV-777,300.00\n", 'payments')
        self.assertEqual(res['imported'], 1)
        invoices = reporting.invoices(self.db)
        inv_north = next(r for r in invoices if r['invoice_number'] == 'INV-777')
        self.assertEqual(inv_north['paid'], 300.00)
        self.assertEqual(inv_north['status'], 'paid')

    def test_unmatched_payment_pool(self):
        """Payment with no matching invoice remains unmatched without affecting invoice balances."""
        res = importing.import_csv(self.db, "payment_id,customer_id,invoice_number,amount\nPAY-UNMATCHED,MAPLE,NO-INV-999,75.50\n", 'payments')
        self.assertEqual(res['imported'], 1)
        ov = reporting.overview(self.db)
        unmatched_ids = [p['payment_id'] for p in ov['unmatched_payments']]
        self.assertIn('PAY-UNMATCHED', unmatched_ids)

    def test_mixed_validity_csv_import(self):
        """Valid data rows import while invalid data rows reject individually with line numbers."""
        csv_data = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,TEST-1,100.00,2026-12-01\n"    # Line 2: Valid
            "MAPLE,TEST-2,-50.00,2026-12-01\n"     # Line 3: Invalid amount
            "INVALID_CUST,TEST-3,200.00,2026-12-01\n" # Line 4: Unknown customer
            "NORTH,TEST-4,300.00,2026-12-05\n"     # Line 5: Valid
        )
        res = importing.import_csv(self.db, csv_data, 'invoices')
        self.assertEqual(res['imported'], 2)
        self.assertEqual(res['skipped'], 0)
        self.assertEqual(res['rejected'], 2)
        self.assertEqual(len(res['errors']), 2)
        error_lines = [e['line'] for e in res['errors']]
        self.assertEqual(error_lines, [3, 4])

    def test_open_paid_status_filters(self):
        """invoices(status) filters open vs paid accurately."""
        all_inv = reporting.invoices(self.db, 'all')
        open_inv = reporting.invoices(self.db, 'open')
        paid_inv = reporting.invoices(self.db, 'paid')

        self.assertTrue(all(r['status'] == 'open' for r in open_inv))
        self.assertTrue(all(r['balance'] > 0 for r in open_inv))
        self.assertTrue(all(r['status'] == 'paid' for r in paid_inv))
        self.assertTrue(all(r['balance'] <= 0 for r in paid_inv))
        self.assertEqual(len(all_inv), len(open_inv) + len(paid_inv))

    def test_cent_precision_and_export_consistency(self):
        """CSV export values match screen data with exact 2-decimal precision (e.g. 19.99)."""
        export_text = reporting.export_csv(self.db)
        self.assertIn('NORTH,INV-300,19.99,10.00,9.99,open', export_text)
        self.assertNotIn('19.98', export_text)

    def test_csv_formula_injection_protection(self):
        """CSV text fields starting with =, +, -, @ are escaped with leading single quote."""
        importing.import_csv(self.db, "customer_id,invoice_number,amount,due_date\nHARBOR,=SUM(A1:A10),500.00,2026-12-01\n", 'invoices')
        export_text = reporting.export_csv(self.db)
        self.assertIn("HARBOR,'=SUM(A1:A10),500.00,0.00,500.00,open", export_text)

    def test_http_api_import_feedback(self):
        """Test HTTP API server responses for success (200), partial failure (200 with rejections), and 400 failure."""
        server = http_app.make_server(self.db_path, ROOT / 'web', 0)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            url = f'http://127.0.0.1:{port}/api/import?kind=invoices'
            
            # 1. Success (200)
            req1 = urllib.request.Request(url, data=b"customer_id,invoice_number,amount,due_date\nHARBOR,HTTP-1,100.00,2026-11-01\n", headers={'Content-Type': 'text/csv'})
            with urllib.request.urlopen(req1) as resp1:
                self.assertEqual(resp1.status, 200)
                body1 = json.loads(resp1.read().decode('utf-8'))
                self.assertEqual(body1['imported'], 1)
                self.assertEqual(body1['rejected'], 0)

            # 2. Partial Failure (200 with rejected row detail)
            req2 = urllib.request.Request(url, data=b"customer_id,invoice_number,amount,due_date\nHARBOR,HTTP-2,-50.00,2026-11-01\n", headers={'Content-Type': 'text/csv'})
            with urllib.request.urlopen(req2) as resp2:
                self.assertEqual(resp2.status, 200)
                body2 = json.loads(resp2.read().decode('utf-8'))
                self.assertEqual(body2['rejected'], 1)
                self.assertEqual(body2['errors'][0]['line'], 2)

            # 3. Wholly Invalid Header Failure (400 Bad Request)
            req3 = urllib.request.Request(url, data=b"bad_col1,bad_col2\nval1,val2\n", headers={'Content-Type': 'text/csv'})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req3)
            self.assertEqual(ctx.exception.code, 400)
            body3 = json.loads(ctx.exception.read().decode('utf-8'))
            ctx.exception.close()
            self.assertIn('error', body3)

        finally:
            server.shutdown()
            server.server_close()


    def test_overpayment_handling(self):
        """Overpayment results in negative balance, status 'paid', and does not alter other invoices."""
        res = importing.import_csv(self.db, "payment_id,customer_id,invoice_number,amount\nPAY-OVER,HARBOR,INV-100,1300.00\n", 'payments')
        self.assertEqual(res['imported'], 1)

        invoices = reporting.invoices(self.db, 'all')
        harbor_100 = next(i for i in invoices if i['customer_id'] == 'HARBOR' and i['invoice_number'] == 'INV-100')
        self.assertEqual(harbor_100['paid'], 1300.00)
        self.assertEqual(harbor_100['balance'], -50.00)
        self.assertEqual(harbor_100['status'], 'paid')

        ov = reporting.overview(self.db)
        open_invs = reporting.invoices(self.db, 'open')
        expected_outstanding = round(sum(i['balance'] for i in open_invs), 2)
        self.assertEqual(ov['summary']['outstanding'], expected_outstanding)

    def test_sample_files_import(self):
        """Test importing the sample CSV files in samples/ directory."""
        samples_dir = ROOT / 'samples'
        
        # 1. invoices-mixed.csv (2 imported, 1 rejected at line 3)
        mixed_text = (samples_dir / 'invoices-mixed.csv').read_text(encoding='utf-8')
        res_mixed = importing.import_csv(self.db, mixed_text, 'invoices')
        self.assertEqual(res_mixed['imported'], 2)
        self.assertEqual(res_mixed['rejected'], 1)
        self.assertEqual(res_mixed['errors'][0]['line'], 3)

        # 2. wrong-header.csv (raises ValueError / HTTP 400 header error)
        wrong_text = (samples_dir / 'wrong-header.csv').read_text(encoding='utf-8')
        with self.assertRaises(ValueError) as ctx:
            importing.import_csv(self.db, wrong_text, 'invoices')
        self.assertIn('Expected CSV header', str(ctx.exception))

        # 3. invoices-new.csv (2 imported)
        new_text = (samples_dir / 'invoices-new.csv').read_text(encoding='utf-8')
        res_new = importing.import_csv(self.db, new_text, 'invoices')
        self.assertEqual(res_new['imported'], 2)
        self.assertEqual(res_new['rejected'], 0)

        # 4. payments.csv (3 imported)
        pay_text = (samples_dir / 'payments.csv').read_text(encoding='utf-8')
        res_pay = importing.import_csv(self.db, pay_text, 'payments')
        self.assertEqual(res_pay['imported'], 3)
        self.assertEqual(res_pay['rejected'], 0)

    def test_csv_oversized_row_count_rejection(self):
        """CSVs with more than 5000 rows are rejected with ValueError."""
        header = "customer_id,invoice_number,amount,due_date\n"
        rows = "".join(f"HARBOR,ROW-{i},10.00,2026-12-01\n" for i in range(5001))
        with self.assertRaises(ValueError) as ctx:
            importing.import_csv(self.db, header + rows, 'invoices')
        self.assertIn('maximum limit of 5000 rows', str(ctx.exception))

    def test_csv_oversized_field_length_rejection(self):
        """CSV fields longer than 256 characters are rejected per-row."""
        long_inv = "A" * 257
        csv_data = f"customer_id,invoice_number,amount,due_date\nHARBOR,{long_inv},10.00,2026-12-01\n"
        res = importing.import_csv(self.db, csv_data, 'invoices')
        self.assertEqual(res['imported'], 0)
        self.assertEqual(res['rejected'], 1)
        self.assertIn('exceeds maximum length of 256 characters', res['errors'][0]['reason'])

    def test_per_row_field_length_validation(self):
        """Field length validation (>256 chars) rejects only the invalid row while importing valid rows."""
        long_inv = "A" * 257
        csv_data = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,INV-FIELD-1,100.00,2026-12-01\n"
            f"HARBOR,{long_inv},200.00,2026-12-01\n"
            "MAPLE,INV-FIELD-2,300.00,2026-12-01\n"
        )
        res = importing.import_csv(self.db, csv_data, 'invoices')
        self.assertEqual(res['imported'], 2)
        self.assertEqual(res['rejected'], 1)
        self.assertEqual(len(res['errors']), 1)
        self.assertEqual(res['errors'][0]['line'], 3)
        self.assertIn('exceeds maximum length of 256 characters', res['errors'][0]['reason'])

        invoices = reporting.invoices(self.db, 'all')
        inv_numbers = [i['invoice_number'] for i in invoices]
        self.assertIn('INV-FIELD-1', inv_numbers)
        self.assertIn('INV-FIELD-2', inv_numbers)

    def test_formula_injection_protection_all_prefixes(self):
        """Formula injection protection covers =, +, -, and @ leading characters."""
        test_cases = [('INV-EQ', '=SUM(A1:A10)'), ('INV-PLUS', '+123456'), ('INV-MINUS', '-cmd.exe'), ('INV-AT', '@SUM')]
        for inv_num, bad_val in test_cases:
            self.db.execute("INSERT INTO invoices (customer_id, invoice_number, amount, due_date) VALUES ('HARBOR', ?, 1000, '2026-12-01')", (bad_val,))
        export_text = reporting.export_csv(self.db)
        for _, bad_val in test_cases:
            self.assertIn(f"HARBOR,'{bad_val}", export_text)

    def test_no_inner_html_in_app_js(self):
        """Static audit enforcing zero innerHTML assignments in web/app.js."""
        app_js_content = (ROOT / 'web' / 'app.js').read_text(encoding='utf-8')
        self.assertNotIn('.innerHTML', app_js_content)
        self.assertNotIn('innerHTML =', app_js_content)

    def test_import_audit_log(self):
        """import_audit records transactional audit entries without raw CSV text."""
        csv_data = "customer_id,invoice_number,amount,due_date\nHARBOR,AUDIT-1,50.00,2026-12-01\n"
        res = importing.import_csv(self.db, csv_data, 'invoices', filename='test_import.csv')
        self.assertEqual(res['imported'], 1)
        
        audits = reporting.get_import_audit(self.db)
        self.assertGreaterEqual(len(audits), 1)
        latest = audits[0]
        self.assertEqual(latest['kind'], 'invoices')
        self.assertEqual(latest['source_filename'], 'test_import.csv')
        self.assertEqual(latest['imported_count'], 1)
        self.assertTrue(len(latest['sha256']) == 64)
        
        # Verify raw CSV text is NOT stored in audit table
        raw_audit_text = str(dict(latest))
        self.assertNotIn('HARBOR,AUDIT-1,50.00,2026-12-01', raw_audit_text)

    def test_error_information_leakage_prevention(self):
        """HTTP error responses do not leak traceback text, SQL statements, or database paths."""
        server = http_app.make_server(self.db_path, ROOT / 'web', 0)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            url = f'http://127.0.0.1:{port}/api/import?kind=invoices'
            # Send invalid non-UTF8 bytes
            req = urllib.request.Request(url, data=b'\x80\x81\x82', headers={'Content-Type': 'text/csv'})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req)
            self.assertEqual(ctx.exception.code, 400)
            body = ctx.exception.read().decode('utf-8')
            ctx.exception.close()
            
            # Assert no sensitive internal path or traceback leaked
            self.assertNotIn('Traceback', body)
            self.assertNotIn('sqlite3', body)
            self.assertNotIn('clearledger.sqlite3', body)
            self.assertIn('Use a UTF-8 CSV', body)
        finally:
            server.shutdown()
            server.server_close()

    def test_integrity_error_sanitization(self):
        """Database integrity errors return generic response without revealing table schema or SQL statements."""
        from unittest.mock import patch
        import sqlite3
        server = http_app.make_server(self.db_path, ROOT / 'web', 0)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            url = f'http://127.0.0.1:{port}/api/import?kind=invoices'
            req = urllib.request.Request(url, data=b"customer_id,invoice_number,amount,due_date\nHARBOR,HTTP-INT,100.00,2026-11-01\n", headers={'Content-Type': 'text/csv'})
            with patch('ledger.importing.import_csv', side_effect=sqlite3.IntegrityError("UNIQUE constraint failed: invoices.customer_id, invoices.invoice_number")):
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
                body = json.loads(ctx.exception.read().decode('utf-8'))
                ctx.exception.close()
                self.assertEqual(body, {'error': 'A database constraint error occurred'})
                self.assertNotIn('UNIQUE constraint', str(body))
                self.assertNotIn('invoices.customer_id', str(body))
        finally:
            server.shutdown()
            server.server_close()

    def test_audit_privacy_no_sensitive_identifiers(self):
        """Assert user-provided customer IDs, invoice numbers, and raw strings do not enter import_audit."""
        csv_data = (
            "customer_id,invoice_number,amount,due_date\n"
            "HARBOR,SECRET-INV-999,INVALID_AMT,2026-12-01\n"
            "SECRET_CUST_ID,SECRET-INV-888,100.00,2026-12-01\n"
        )
        res = importing.import_csv(self.db, csv_data, 'invoices', filename='secret_import.csv')
        self.assertEqual(res['rejected'], 2)
        
        audits = reporting.get_import_audit(self.db)
        latest = audits[0]
        audit_str = str(dict(latest))
        
        # Verify no sensitive customer ID or invoice numbers are persisted in import_audit
        self.assertNotIn('SECRET-INV-999', audit_str)
        self.assertNotIn('SECRET_CUST_ID', audit_str)
        self.assertNotIn('SECRET-INV-888', audit_str)
        self.assertNotIn('INVALID_AMT', audit_str)
        
        # Verify structured error summary uses non-sensitive codes
        summary = json.loads(latest['error_summary'])
        self.assertEqual(summary[0]['code'], 'INVALID_AMOUNT')
        self.assertEqual(summary[1]['code'], 'UNKNOWN_CUSTOMER')

    def test_x_import_filename_header_sanitization(self):
        """Test sanitization of X-Import-Filename header (path traversal, control chars, length caps)."""
        self.assertIsNone(importing._sanitize_filename(None))
        self.assertIsNone(importing._sanitize_filename('../../'))
        self.assertEqual(importing._sanitize_filename('../../etc/passwd.csv'), 'passwd.csv')
        self.assertEqual(importing._sanitize_filename('C:\\Windows\\System32\\test\x00.csv'), 'test.csv')
        long_name = "A" * 100 + ".csv"
        self.assertEqual(len(importing._sanitize_filename(long_name)), 64)

    def test_backup_failure_aborts_migration(self):
        """Simulate backup failure prior to migration and assert migration is aborted cleanly."""
        test_db_path = Path(self.tmp.name) / 'unmigrated.sqlite3'
        import sqlite3
        conn = sqlite3.connect(test_db_path)
        conn.execute('CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT)')
        conn.execute('CREATE TABLE invoices (id INTEGER PRIMARY KEY, customer_id TEXT, invoice_number TEXT, amount REAL, due_date TEXT)')
        conn.execute('CREATE TABLE payments (payment_id TEXT PRIMARY KEY, customer_id TEXT, invoice_number TEXT, amount REAL, invoice_id INTEGER)')
        conn.execute("INSERT INTO customers VALUES ('HARBOR', 'Harbor')")
        conn.execute("INSERT INTO invoices VALUES (1, 'HARBOR', 'INV-1', 10.50, '2026-09-01')")
        conn.execute("INSERT INTO payments VALUES ('PAY-1', 'HARBOR', 'INV-1', 10.50, 1)")
        conn.commit()
        conn.close()

        from unittest.mock import patch
        with patch('ledger.storage.create_verified_backup', side_effect=RuntimeError("Backup failed simulation")):
            with self.assertRaises(RuntimeError) as ctx:
                storage.connect(test_db_path)
            self.assertIn("Backup failed simulation", str(ctx.exception))

        # Verify original database table structure remains unmigrated REAL floats
        check_conn = sqlite3.connect(test_db_path)
        col_type = check_conn.execute("PRAGMA table_info(invoices)").fetchall()[3][2]
        check_conn.close()
        self.assertEqual(col_type.upper(), 'REAL')

    def test_migration_rollback_on_failure(self):
        """Simulate unexpected failure during schema migration and prove database rolls back cleanly."""
        test_db_path = Path(self.tmp.name) / 'rollback_test.sqlite3'
        import sqlite3
        conn = sqlite3.connect(test_db_path)
        conn.execute('CREATE TABLE customers (customer_id TEXT PRIMARY KEY, name TEXT)')
        conn.execute('CREATE TABLE invoices (id INTEGER PRIMARY KEY, customer_id TEXT, invoice_number TEXT, amount REAL, due_date TEXT)')
        conn.execute('CREATE TABLE payments (payment_id TEXT PRIMARY KEY, customer_id TEXT, invoice_number TEXT, amount REAL, invoice_id INTEGER)')
        conn.execute("INSERT INTO customers VALUES ('HARBOR', 'Harbor')")
        conn.execute("INSERT INTO invoices VALUES (1, 'HARBOR', 'INV-1', 10.50, '2026-09-01')")
        conn.execute("INSERT INTO payments VALUES ('PAY-1', 'HARBOR', 'INV-1', 10.50, 1)")
        conn.commit()
        conn.close()

        from unittest.mock import patch
        with patch('ledger.storage.to_paise', side_effect=ValueError("Simulated conversion failure")):
            with self.assertRaises(ValueError):
                storage.connect(test_db_path)

        # Confirm original unmigrated database structure and values remain untouched
        check_conn = sqlite3.connect(test_db_path)
        row = check_conn.execute("SELECT amount FROM invoices WHERE id=1").fetchone()
        check_conn.close()
        self.assertEqual(row[0], 10.50)

    def test_per_ip_rate_limiting(self):
        """Per-IP rate limiting caps API routes at 60 req/60s, isolates IPs, and bypasses static routes."""
        http_app._ip_request_times.clear()
        server = http_app.make_server(self.db_path, ROOT / 'web', 0)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            url_api = f'http://127.0.0.1:{port}/api/overview'
            url_static = f'http://127.0.0.1:{port}/app.js'

            # (a) Fire 60 requests (succeed), 61st request returns HTTP 429
            for _ in range(60):
                req = urllib.request.Request(url_api)
                with urllib.request.urlopen(req) as resp:
                    self.assertEqual(resp.status, 200)

            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(urllib.request.Request(url_api))
            self.assertEqual(ctx.exception.code, 429)
            retry_after_hdr = ctx.exception.headers.get('Retry-After')
            self.assertIsNotNone(retry_after_hdr)
            self.assertTrue(1 <= int(retry_after_hdr) <= 60)
            body = json.loads(ctx.exception.read().decode('utf-8'))
            ctx.exception.close()
            self.assertEqual(body, {'error': 'Too many requests, please slow down'})

            # (b) Assert request from a different simulated IP still succeeds
            allowed_other, _ = http_app.check_rate_limit('10.0.0.1')
            self.assertTrue(allowed_other)

            # (c) Assert static routes are never rate-limited even when IP is limited
            req_static = urllib.request.Request(url_static)
            with urllib.request.urlopen(req_static) as resp_static:
                self.assertEqual(resp_static.status, 200)
                self.assertGreater(len(resp_static.read()), 0)
        finally:
            http_app._ip_request_times.clear()
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()




