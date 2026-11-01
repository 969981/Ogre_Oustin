import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

SRC = Path(__file__).resolve().parents[1] / "tools" / "build_sv400_raid_damage_ips.py"
spec = importlib.util.spec_from_file_location("raid_damage", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestOneInstructionPatch(unittest.TestCase):
    def test_original_and_new_arm64(self):
        self.assertEqual(mod.ORIGINAL_INSTRUCTION, struct.pack("<I", 0x79413BF9))
        self.assertEqual(mod.PATCH_INSTRUCTION, struct.pack("<I", 0x529FFFF9))

    def test_ryujinx_buildid_filename_exact_uppercase(self):
        self.assertEqual(mod.BUILD_ID, mod.BUILD_ID.upper())
        self.assertTrue(mod.INSTALL_PATH.endswith(f'{mod.BUILD_ID}.ips'))

    def test_ips32_single_record(self):
        blob = mod.make_ips32()
        self.assertEqual(len(blob), 19)
        self.assertEqual(blob[:5], b"IPS32")
        offset, length = struct.unpack_from(">IH", blob, 5)
        self.assertEqual(offset, 0x1536314)
        self.assertEqual(length, 4)
        self.assertEqual(blob[11:15], mod.PATCH_INSTRUCTION)
        self.assertEqual(blob[15:], b"EEOF")

    def test_install_package(self):
        with tempfile.TemporaryDirectory() as temp:
            ips, package = mod.build(Path(temp))
            self.assertEqual(ips.read_bytes(), mod.make_ips32())
            with zipfile.ZipFile(package) as zf:
                self.assertEqual(set(zf.namelist()), {mod.INSTALL_PATH, "README.txt"})
                self.assertEqual(zf.read(mod.INSTALL_PATH), mod.make_ips32())
                self.assertIn(b"UNCONDITIONAL", zf.read("README.txt"))

if __name__ == "__main__":
    unittest.main()
