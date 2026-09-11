import errno
import io
from unittest import TestCase
from unittest.mock import MagicMock, patch

from odoo.tests import tagged

from ..services.import_utils import parsers


class _BrokenDiagnosticStream:
    """Match a production output stream that rejects xlrd diagnostics."""

    def write(self, _value):
        raise OSError(errno.EIO, "Input/output error")


@tagged("standard", "post_install", "-at_install")
class TestImportUtilsParsers(TestCase):
    test_module = "marathon_ventures"

    def test_xls_reader_isolates_xlrd_diagnostics(self):
        sheet = MagicMock()
        sheet.nrows = 2
        sheet.row_values.side_effect = [
            ["Network Deal Number", "Airdate"],
            ["TCN-1", "2026-09-07"],
        ]
        workbook = MagicMock()
        workbook.nsheets = 1
        workbook.sheet_by_index.return_value = sheet

        broken_default = _BrokenDiagnosticStream()

        def open_workbook(*, file_contents, logfile=broken_default):
            self.assertEqual(file_contents, b"legacy-xls")
            logfile.write("*** No CODEPAGE record, no encoding_override\n")
            self.assertIsInstance(logfile, io.StringIO)
            return workbook

        with patch.object(parsers.xlrd, "open_workbook", side_effect=open_workbook):
            rows = parsers.read_tabular_rows(
                b"legacy-xls",
                "tcn-prelog.xls",
                {"headerRow": 1, "sheetIndex": 0},
            )

        self.assertEqual(
            rows,
            [{"Network Deal Number": "TCN-1", "Airdate": "2026-09-07"}],
        )
