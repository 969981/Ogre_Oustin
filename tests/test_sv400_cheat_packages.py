import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "package_sv400_cheats.py"
spec = importlib.util.spec_from_file_location("sv400_cheat_packages", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestCheatPackaging(unittest.TestCase):
    def test_guarded_violet_instruction(self):
        self.assertEqual(mod.RVA, 0x1536214)
        self.assertEqual(mod.ORIGINAL_WORD, 0x79413BF9)
        self.assertEqual(mod.PATCHED_WORD, 0x529FFFF9)
        self.assertEqual(
            mod.cheat_text(),
            "[SV 4.0.0 Damage Record 65535 EXPERIMENTAL]\n"
            "14050000 01536214 79413BF9\n"
            "04000000 01536214 529FFFF9\n"
            "20000000\n"
        )

    def test_all_four_paths_and_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d)
            zips = mod.package(output)
            self.assertEqual(len(zips), 4)
            for game, identity in mod.GAMES.items():
                bid16 = identity["bid"][:16]
                self.assertEqual(len(bid16), 16)
                expected_txt = mod.cheat_text().encode("utf-8")
                self.assertEqual((output / "cheats" / game / (bid16 + ".txt")).read_bytes(), expected_txt)
                suffix = "_CANDIDATE" if game == "Scarlet" else ""
                for target in ("Atmosphere", "Ryujinx"):
                    archive = output / f"Pokemon_{game}_4.0.0_{target}_65535_CHEAT{suffix}.zip"
                    self.assertIn(archive, zips)
                    with zipfile.ZipFile(archive) as zf:
                        dest = (
                            f"atmosphere/contents/{identity['tid']}/cheats/{bid16}.txt"
                            if target == "Atmosphere"
                            else f"mods/contents/{identity['tid']}/{mod.PATCH_NAME}/cheats/{bid16}.txt"
                        )
                        self.assertEqual(zf.read(dest), expected_txt)
                        notes = zf.read("README.txt").decode("utf-8")
                        self.assertIn("DO NOT enable the previous IPS", notes)
                        self.assertIn("Disabling a code does not undo", notes)
                        if game == "Scarlet":
                            self.assertIn("UNVERIFIED CANDIDATE", notes)
                            self.assertIn("DOES NOT prove Scarlet validity", notes)


if __name__ == "__main__":
    unittest.main()
