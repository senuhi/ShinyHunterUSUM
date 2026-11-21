"""Bound disk diagnostics without truncating records or deleting image evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from bounded_log import append_json_line


class BoundedLogTests(unittest.TestCase):
    def test_unicode_records_rotate_within_byte_budget_and_keep_latest(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'events.jsonl'
            image=Path(td)/'shiny.png';image.write_bytes(b'preserved candidate')
            for i in range(50):
                append_json_line(path,{'index':i,'text':'色違い候補'},limit_bytes=160,backups=2)
            logs=[path.with_name(path.name+'.2'),path.with_name(path.name+'.1'),path]
            self.assertTrue(all(p.exists() and p.stat().st_size<=160 for p in logs))
            rows=[json.loads(line) for p in logs for line in p.read_text().splitlines()]
            self.assertEqual(rows[-1]['index'],49)
            self.assertEqual([r['index'] for r in rows],list(range(rows[0]['index'],50)))
            self.assertTrue(all(r['text']=='色違い候補' for r in rows))
            self.assertEqual(len(list(Path(td).glob('events.jsonl*'))),3)
            self.assertEqual(image.read_bytes(),b'preserved candidate')

    def test_single_file_mode_and_oversized_event_are_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'events.jsonl'
            for i in range(10):append_json_line(path,{'i':i},limit_bytes=20,backups=0)
            before=path.read_bytes()
            self.assertLessEqual(len(before),20)
            self.assertEqual(json.loads(before.splitlines()[-1])['i'],9)
            with self.assertRaises(OSError):append_json_line(path,{'text':'x'*50},limit_bytes=20)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(len(list(Path(td).iterdir())),1)

    def test_write_errors_propagate_instead_of_disabling_safety_logging(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'missing'/'events.jsonl'
            with self.assertRaises(OSError):append_json_line(path,{'event':'input_attempt'})


if __name__=='__main__':unittest.main()
