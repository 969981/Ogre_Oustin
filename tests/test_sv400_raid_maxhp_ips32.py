"""Smoke tests for the Violet 4.0.0 IPS32 generator."""
from pathlib import Path
import hashlib
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_sv400_raid_maxhp_ips32 import build, branch, STORE_RVA, CAVE_RVA

KNOWN_PATCH_SHA = "b7d03d97542f95f27383ff1ceb8e9b8eb39c33ed7535be520be07e1cbc581e84"


class IPS32Tests(unittest.TestCase):
    def test_arm64_branch_roundtrip(self):
        for src, target in ((STORE_RVA, CAVE_RVA), (CAVE_RVA + 24, STORE_RVA + 4)):
            w = struct.unpack("<I", branch(src, target))[0]
            self.assertEqual(w >> 26, 0x05)
            immediate = w & 0x3FFFFFF
            if immediate & 0x2000000:
                immediate -= 0x4000000
            self.assertEqual(src + immediate * 4, target)

    def test_bad_elf_is_refused(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            build(b"invalid")

    def test_known_elf_reproduces_committed_ips(self):
        # Set SV400_ELF to a local copy of the user's own original ELF.
        import os
        path = os.environ.get("SV400_ELF")
        if not path:
            self.skipTest("Set SV400_ELF to test source patch reproduction")
        patch = build(Path(path).read_bytes())
        self.assertEqual(hashlib.sha256(patch).hexdigest(), KNOWN_PATCH_SHA)


if __name__ == "__main__":
    unittest.main()
