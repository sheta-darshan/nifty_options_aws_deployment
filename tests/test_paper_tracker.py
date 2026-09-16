import unittest
import os
import pandas as pd
import tempfile
from stock_selection.paper_tracker import (
    parse_date_to_iso,
    migrate_log_file,
    validate_date_formats,
    ISO_DATE_REGEX
)


class TestPaperTrackerDates(unittest.TestCase):

    def test_parse_date_to_iso_formats(self):
        # ISO format
        self.assertEqual(parse_date_to_iso("2026-08-27"), "2026-08-27")
        # DD/MM/YYYY format
        self.assertEqual(parse_date_to_iso("24/08/2026"), "2026-08-24")
        self.assertEqual(parse_date_to_iso("26/08/2026"), "2026-08-26")
        # None and blanks
        self.assertIsNone(parse_date_to_iso(None))
        self.assertIsNone(parse_date_to_iso(""))
        self.assertIsNone(parse_date_to_iso("nan"))

    def test_validate_date_formats_assertion(self):
        # Valid ISO dataframe
        df_valid = pd.DataFrame([
            {"Selection_Date": "2026-08-24", "Execution_Date": "2026-08-25"},
            {"Selection_Date": "2026-08-27", "Execution_Date": "2026-08-28"}
        ])
        # Should not raise
        validate_date_formats(df_valid)

        # Invalid non-ISO dataframe (DD/MM/YYYY)
        df_invalid = pd.DataFrame([
            {"Selection_Date": "24/08/2026", "Execution_Date": "25/08/2026"}
        ])
        with self.assertRaises(AssertionError):
            validate_date_formats(df_invalid)

    def test_migration_of_legacy_log(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            temp_path = f.name
            f.write("Selection_Date,Execution_Date,Symbol,Status\n")
            f.write("24/08/2026,25/08/2026,MARATHON,PENDING_EXECUTION\n")
            f.write("2026-08-27,2026-08-28,IMAGICAA,EXECUTED\n")

        try:
            migrate_log_file(temp_path)
            df_migrated = pd.read_csv(temp_path)
            self.assertEqual(df_migrated.loc[0, "Selection_Date"], "2026-08-24")
            self.assertEqual(df_migrated.loc[0, "Execution_Date"], "2026-08-25")
            self.assertEqual(df_migrated.loc[1, "Selection_Date"], "2026-08-27")
            self.assertEqual(df_migrated.loc[1, "Execution_Date"], "2026-08-28")
            # Should pass validation cleanly
            validate_date_formats(df_migrated)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
