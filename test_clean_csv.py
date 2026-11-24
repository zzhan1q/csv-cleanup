import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from clean_csv import clean

ROOT = Path(__file__).parent


class CleanerTests(unittest.TestCase):
    def test_example_audit(self):
        with (ROOT / "data/dirty.csv").open(newline="", encoding="utf-8") as stream:
            rows, audit = clean(csv.DictReader(stream))
        self.assertEqual([row["order_id"] for row in rows],
                         ["A-104", "A-105", "A-108", "A-110", "A-112", "A-115"])
        self.assertEqual(rows[0]["date"], "2026-04-02")
        self.assertEqual(rows[2]["amount_usd"], "19.50")
        self.assertEqual(rows[3]["product"], "Tray, small")
        self.assertEqual([(i, kind) for i, _, kind, _ in audit if kind != "normalized"],
                         [(2, "duplicate"), (4, "rejected"), (5, "rejected"),
                          (7, "conflict"), (8, "rejected"), (10, "rejected"),
                          (12, "rejected"), (13, "rejected")])

    def test_cli_reproduces_committed_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run([sys.executable, ROOT / "clean_csv.py", ROOT / "data/dirty.csv",
                            "--output-dir", folder], check=True, capture_output=True)
            for name in ("audit.csv", "cleaned.csv"):
                self.assertEqual((Path(folder) / name).read_text(), (ROOT / "example" / name).read_text())

    def test_truncated_record(self):
        _, audit = clean([dict(order_id="A-001", date="2026-04-01", product=None, amount_usd=None)])
        self.assertEqual(audit[0][2:], ("rejected", "wrong number of fields"))

    def test_rejects_source_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "cleaned.csv"
            source.write_text("keep me")
            result = subprocess.run([sys.executable, ROOT / "clean_csv.py", source,
                                     "--output-dir", folder], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(source.read_text(), "keep me")
