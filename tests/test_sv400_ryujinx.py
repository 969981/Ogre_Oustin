import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "package_sv400_ryujinx.py"
spec = importlib.util.spec_from_file_location("ryujinx_package", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestRyujinxPackage(unittest.TestCase):
    def test_ryujinx_filename_exact_uppercase(self):
        self.assertEqual(mod.BUILD_ID, mod.BUILD_ID.upper())
        self.assertTrue(mod.RYUJINX_PATH.endswith(f'{mod.BUILD_ID}.ips'))

    def test_repackage_valid_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "atmosphere" / "exefs_patches" / mod.PATCH_NAME / f"{mod.BUILD_ID}.ips"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(mod.EXPECTED_IPS)
            out = mod.build(root)
            with zipfile.ZipFile(out) as z:
                self.assertEqual(z.read(mod.RYUJINX_PATH), mod.EXPECTED_IPS)
                self.assertEqual(len(z.read(mod.RYUJINX_PATH)), 19)
                self.assertIn("README_Ryujinx.txt", z.namelist())

    def test_rejects_unknown_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "atmosphere" / "exefs_patches" / mod.PATCH_NAME / f"{mod.BUILD_ID}.ips"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b"garbage")
            with self.assertRaises(ValueError):
                mod.build(root)

if __name__ == "__main__":
    unittest.main()
