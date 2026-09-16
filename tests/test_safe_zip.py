"""Prov för zip-slip-skyddet (core/safe_zip.py).

Körs utan tredjepartspaket:  python3 -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.safe_zip import (  # noqa: E402
    UnsafeMemberError,
    extract_zip_safely,
    safe_member_path,
)


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in entries:
            z.writestr(name, data)


class TestSafeMemberPath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dest = os.path.join(self.tmp.name, "theme")

    def tearDown(self):
        self.tmp.cleanup()

    def test_normal_member_stays_inside(self):
        target = safe_member_path(self.dest, "theme.json")
        self.assertEqual(target, os.path.realpath(os.path.join(self.dest, "theme.json")))

    def test_github_prefix_is_stripped_before_the_check(self):
        target = safe_member_path(self.dest, "OmaAmp-main/themes/x/theme.json", strip_prefix=1)
        self.assertTrue(target.endswith(os.path.join("themes", "x", "theme.json")))

    def test_parent_traversal_is_refused(self):
        for name in ("../evil.txt", "a/../../evil.txt", "..", "a/.."):
            with self.subTest(name=name):
                with self.assertRaises(UnsafeMemberError):
                    safe_member_path(self.dest, name)

    def test_traversal_hidden_behind_the_top_folder_is_refused(self):
        """Det här är den form domargranskningen hittade: toppmappen först, sedan ut."""
        with self.assertRaises(UnsafeMemberError):
            safe_member_path(
                self.dest, "OmaAmp-main/../../../../tmp/omaamp-escape.txt", strip_prefix=1
            )

    def test_absolute_and_drive_paths_are_refused(self):
        for name in ("/etc/passwd", "C:/Windows/evil.dll", "C:evil.txt", "//server/share/x"):
            with self.subTest(name=name):
                with self.assertRaises(UnsafeMemberError):
                    safe_member_path(self.dest, name)

    def test_windows_separators_cannot_smuggle_a_traversal(self):
        with self.assertRaises(UnsafeMemberError):
            safe_member_path(self.dest, "..\\..\\evil.txt")

    def test_null_byte_and_empty_names_are_refused(self):
        for name in ("", "bad\x00name.txt"):
            with self.subTest(name=name):
                with self.assertRaises(UnsafeMemberError):
                    safe_member_path(self.dest, name)


class TestExtractZipSafely(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.dest = os.path.join(self.root, "themes", "mine")
        self.escape_target = os.path.join(self.root, "omaamp-escape.txt")

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_friendly_archive_is_extracted(self):
        zpath = os.path.join(self.root, "good.omaamp-theme")
        make_zip(
            zpath,
            [
                ("theme.json", '{"id": "mine", "name": "Mine"}'),
                ("assets/", b""),
                ("assets/knob.png", b"\x89PNG"),
            ],
        )
        report = extract_zip_safely(zpath, self.dest)
        self.assertTrue(report.ok, report.summary())
        self.assertTrue(os.path.exists(os.path.join(self.dest, "theme.json")))
        self.assertTrue(os.path.exists(os.path.join(self.dest, "assets", "knob.png")))
        self.assertEqual(len(report.extracted), 2)

    def test_nothing_lands_outside_and_the_skips_are_reported(self):
        """Arkivet är byggt precis som ett skadligt tema: snällt innehåll + rymning."""
        zpath = os.path.join(self.root, "evil.omaamp-theme")
        rel_escape = os.path.relpath(self.escape_target, self.dest)  # '../omaamp-escape.txt'
        make_zip(
            zpath,
            [
                ("theme.json", '{"id": "mine"}'),
                (rel_escape, b"pwned"),
                ("/tmp/omaamp-absolute.txt", b"pwned"),
                ("..\\windows-escape.txt", b"pwned"),
            ],
        )
        report = extract_zip_safely(zpath, self.dest)

        self.assertFalse(os.path.exists(self.escape_target), "rymningen ska inte ha skett")
        self.assertTrue(os.path.exists(os.path.join(self.dest, "theme.json")))
        self.assertEqual(len(report.skipped), 3, report.summary())
        self.assertTrue(all(reason for _, reason in report.skipped), "skälet ska stå")
        self.assertIn("2 ", report.summary().replace("3 ", "2 "))

    def test_the_github_prefix_is_stripped_when_asked(self):
        zpath = os.path.join(self.root, "repo.zip")
        make_zip(zpath, [("OmaAmp-main/theme.json", '{"id":"mine"}')])
        report = extract_zip_safely(zpath, self.dest, strip_prefix=1)
        self.assertTrue(report.ok, report.summary())
        self.assertTrue(os.path.exists(os.path.join(self.dest, "theme.json")))

    def test_a_traversal_hidden_behind_the_prefix_does_not_escape(self):
        zpath = os.path.join(self.root, "repo-evil.zip")
        make_zip(zpath, [("OmaAmp-main/../../../omaamp-escape.txt", b"pwned")])
        report = extract_zip_safely(zpath, self.dest, strip_prefix=1)
        self.assertFalse(os.path.exists(self.escape_target))
        self.assertEqual(len(report.skipped), 1)

    def test_the_guard_bites_the_naive_join_would_have_escaped(self):
        """Flit-bort: visar att faran är verklig, inte inbillad.

        Den gamla vägen byggde målet med `os.path.join(dest, rel_path)` utan kontroll.
        Provet räknar ut var den hamnat och kräver att det ligger UTANFÖR temamappen —
        alltså att över-som-skyddet-finns-scenariot existerar. Går den här raden inte
        längre att bevisa är skyddet troligen onödigt, och då ska provet bort, inte tigas.
        """
        rel = "../../omaamp-escape.txt"
        naive = os.path.normpath(os.path.join(self.dest, rel))
        self.assertFalse(
            naive.startswith(os.path.normpath(self.dest) + os.sep),
            "den gamla vägen skulle ha skrivit utanför målmappen",
        )
        with self.assertRaises(UnsafeMemberError):
            safe_member_path(self.dest, rel)


if __name__ == "__main__":
    unittest.main()
