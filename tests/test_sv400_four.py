import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "package_sv400_four.py"
spec = importlib.util.spec_from_file_location("sv400_four", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestFourPlatformPackages(unittest.TestCase):
    def test_ips32_is_one_instruction(self):
        ips = mod.candidate_ips32()
        self.assertEqual(ips[:5], b"IPS32")
        self.assertEqual(struct.unpack_from(">IH", ips, 5), (0x1536314, 4))
        self.assertEqual(ips[11:15], bytes.fromhex("f9ff9f52"))
        self.assertEqual(ips[-4:], b"EEOF")
        self.assertEqual(ips, mod.VIOLET_IPS)

    def test_both_games_and_both_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "atmosphere" / "exefs_patches" / mod.PATCH_NAME / (mod.GAMES["Violet"]["bid"] + ".ips")
            original.parent.mkdir(parents=True)
            original.write_bytes(mod.VIOLET_IPS)
            bundles = mod.build(root)
            self.assertEqual(len(bundles), 4)
            for name, info in mod.GAMES.items():
                suffix = "_CANDIDATE" if name == "Scarlet" else ""
                for target, prefix in (
                    ("Atmosphere", f"atmosphere/exefs_patches/{mod.PATCH_NAME}/"),
                    ("Ryujinx", f"mods/contents/{info['tid']}/{mod.PATCH_NAME}/exefs/"),
                ):
                    bundle = root / f"Pokemon_{name}_4.0.0_{target}_65535{suffix}.zip"
                    self.assertIn(bundle, bundles)
                    with zipfile.ZipFile(bundle) as archive:
                        expected = prefix + info["bid"] + ".ips"
                        self.assertEqual(archive.read(expected), mod.VIOLET_IPS)
                        readme = archive.read("README.txt").decode()
                        self.assertIn("NOT RAID-ONLY", readme)
                        if name == "Scarlet":
                            self.assertIn("UNVERIFIED CANDIDATE", readme)

    def test_rejects_unexpected_violet(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                mod.build(Path(tmp))

if __name__ == "__main__":
    unittest.main()
