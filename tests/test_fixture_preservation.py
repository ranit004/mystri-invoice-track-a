import json
import shutil
import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing

ROOT = Path(__file__).resolve().parent.parent
LOCAL_TMP_DIR = ROOT / '.local' / 'test_tmp'


class FixturePreservationTests(unittest.TestCase):
    def setUp(self):
        LOCAL_TMP_DIR.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=LOCAL_TMP_DIR)
        self.db_path = Path(self.tmp.name) / 'fixture.sqlite3'
        fixture_src = ROOT / 'fixtures' / 'existing-register.sqlite3'
        shutil.copy2(fixture_src, self.db_path)
        self.db = storage.connect(self.db_path)
        with open(ROOT / 'fixtures' / 'expected-records.json', 'r', encoding='utf-8') as f:
            self.expected = json.load(f)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()


    def test_fixture_starting_totals(self):
        """Verify the restored fixture matches exact expected starting totals."""
        ov = reporting.overview(self.db)
        summary = ov['summary']
        expected_summary = self.expected['summary']
        self.assertEqual(summary['invoice_count'], expected_summary['invoice_count'])
        self.assertEqual(summary['open_count'], expected_summary['open_count'])
        self.assertEqual(f"{summary['outstanding']:.2f}", expected_summary['outstanding'])
        self.assertEqual(len(ov['unmatched_payments']), 1)
        self.assertEqual(ov['unmatched_payments'][0]['payment_id'], 'KEEP-U1')

    def test_fixture_preserved_identities(self):
        """Verify all original records, invoice IDs, and allocations exist in fixture."""
        invoices = reporting.invoices(self.db, 'all')
        invoice_numbers = {i['invoice_number'] for i in invoices}
        for exp_inv in self.expected['invoices']:
            self.assertIn(exp_inv['invoice_number'], invoice_numbers)

        # Check KEEP-700 for HARBOR
        harbor_700 = next(i for i in invoices if i['customer_id'] == 'HARBOR' and i['invoice_number'] == 'KEEP-700')
        self.assertEqual(harbor_700['amount'], 456.78)
        self.assertEqual(harbor_700['paid'], 56.78)
        self.assertEqual(harbor_700['balance'], 400.00)

        # Check KEEP-702 for NORTH
        north_702 = next(i for i in invoices if i['customer_id'] == 'NORTH' and i['invoice_number'] == 'KEEP-702')
        self.assertEqual(north_702['amount'], 150.00)
        self.assertEqual(north_702['paid'], 150.00)
        self.assertEqual(north_702['balance'], 0.00)
        self.assertEqual(north_702['status'], 'paid')

    def test_fixture_allows_new_imports_and_survives_restart(self):
        """Valid new invoice and payment imports succeed on fixture DB and survive app restart."""
        # 1. Import valid new invoice
        res_inv = importing.import_csv(self.db, "customer_id,invoice_number,amount,due_date\nHARBOR,NEW-999,500.00,2026-12-31\n", 'invoices')
        self.assertEqual(res_inv['imported'], 1)

        # 2. Import valid new payment
        res_pay = importing.import_csv(self.db, "payment_id,customer_id,invoice_number,amount\nPAY-NEW1,HARBOR,NEW-999,200.00\n", 'payments')
        self.assertEqual(res_pay['imported'], 1)

        # 3. Simulate App Restart by closing DB and reconnecting to same file
        self.db.close()
        reconnected_db = storage.connect(self.db_path)
        try:
            ov = reporting.overview(reconnected_db)
            self.assertEqual(ov['summary']['invoice_count'], 10)
            self.assertEqual(ov['summary']['open_count'], 8)
            # Original 3698.19 + new 300.00 balance = 3998.19
            self.assertEqual(f"{ov['summary']['outstanding']:.2f}", "3998.19")
        finally:
            reconnected_db.close()


    def test_fixture_migration_exact_snapshot_preservation(self):
        """Exercise actual schema migration on fixture copy and verify all fields are unchanged."""
        mig_db_path = Path(self.tmp.name) / 'unmigrated_fixture.sqlite3'
        shutil.copy2(ROOT / 'fixtures' / 'existing-register.sqlite3', mig_db_path)
        
        # Connect raw and force user_version = 0 to trigger migration
        import sqlite3
        raw_db = sqlite3.connect(mig_db_path)
        raw_db.execute('PRAGMA user_version = 0')
        raw_db.commit()
        raw_db.close()

        # Connect via storage.connect to trigger _migrate_if_needed
        migrated_db = storage.connect(mig_db_path)
        try:
            ov = reporting.overview(migrated_db)
            self.assertEqual(ov['summary']['invoice_count'], 9)
            self.assertEqual(ov['summary']['open_count'], 7)
            self.assertEqual(f"{ov['summary']['outstanding']:.2f}", "3698.19")
            self.assertEqual(len(ov['unmatched_payments']), 1)
            self.assertEqual(ov['unmatched_payments'][0]['payment_id'], 'KEEP-U1')
            self.assertIsNone(ov['unmatched_payments'][0].get('invoice_id'))
        finally:
            migrated_db.close()


if __name__ == '__main__':
    unittest.main()
