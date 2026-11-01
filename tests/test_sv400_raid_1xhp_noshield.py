"""SV400 1x HP + no shield builder tests; never bundles retail assets."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_sv400_raid_1xhp_noshield import package, inspect_patch, MAIN_PATH
from build_raid_profile_experiment import loadi, jmp, OFFSET_SJ

class RaidProfileTests(unittest.TestCase):
    def test_loadi(self):
        for n in [0, 100, 65535]:
            self.assertEqual((loadi(9, n) >> 15) - 65535, n)

    def test_branch(self):
        for src, dest in [(153, 538), (538, 154), (157, 541)]:
            self.assertEqual((jmp(src, dest) >> 7) - OFFSET_SJ + src + 1, dest)

    def test_version_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "bad.blua"
            file.write_bytes(b"not lua")
            with self.assertRaises(ValueError):
                package(file, Path(temp), "scarlet")
            with self.assertRaisesRegex(ValueError, "Violet"):
                package(file, Path(temp), "violet")

    @unittest.skipUnless(os.getenv("SV400_MAIN_BLUA"), "set SV400_MAIN_BLUA to user-owned original")
    def test_full_build(self):
        src = Path(os.environ["SV400_MAIN_BLUA"])
        with tempfile.TemporaryDirectory() as temp:
            report = package(src, Path(temp), "scarlet")
            with zipfile.ZipFile(Path(temp) / report["zip"]) as z:
                self.assertEqual(set(z.namelist()), {"info.toml", MAIN_PATH})
                self.assertEqual(inspect_patch(z.read(MAIN_PATH))["literals"]["hpCoef"], 1)

if __name__ == "__main__":
    unittest.main()
