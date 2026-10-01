#!/usr/bin/env python3
"""Extract one TRPAK from Game Freak data.trpfs using a matching data.trpfd.

The parser is intentionally small and only implements the FlatBuffer fields used
by Trinity/gftool for FileDescriptor, PackInfo and FileSystem.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

FNV_BASIS = 0xCBF29CE484222645
FNV_PRIME = 0x00000100000001B3
DEFAULT_MAIN_PACK = "arc/scriptluabinreleasemainmain.blua.trpak"


class FlatBuffer:
    def __init__(self, data: bytes):
        self.data = data

    def u8(self, off: int) -> int:
        return self.data[off]

    def i8(self, off: int) -> int:
        return struct.unpack_from("<b", self.data, off)[0]

    def u16(self, off: int) -> int:
        return struct.unpack_from("<H", self.data, off)[0]

    def u32(self, off: int) -> int:
        return struct.unpack_from("<I", self.data, off)[0]

    def i32(self, off: int) -> int:
        return struct.unpack_from("<i", self.data, off)[0]

    def u64(self, off: int) -> int:
        return struct.unpack_from("<Q", self.data, off)[0]

    @property
    def root(self) -> int:
        return self.u32(0)

    def field_pos(self, table_pos: int, field_index: int) -> int | None:
        # FlatBuffers stores a signed backwards offset to the vtable. Shared
        # vtables may also result in a negative value, so keep it signed.
        vtable_pos = table_pos - self.i32(table_pos)
        vtable_len = self.u16(vtable_pos)
        entry = 4 + field_index * 2
        if entry + 2 > vtable_len:
            return None
        field_off = self.u16(vtable_pos + entry)
        return None if field_off == 0 else table_pos + field_off

    def vector(self, table_pos: int, field_index: int) -> tuple[int, int]:
        field = self.field_pos(table_pos, field_index)
        if field is None:
            return 0, 0
        vector_pos = field + self.u32(field)
        return vector_pos + 4, self.u32(vector_pos)

    def vector_u64(self, table_pos: int, field_index: int) -> list[int]:
        start, count = self.vector(table_pos, field_index)
        return [self.u64(start + i * 8) for i in range(count)]

    def vector_strings(self, table_pos: int, field_index: int) -> list[str]:
        start, count = self.vector(table_pos, field_index)
        result: list[str] = []
        for i in range(count):
            entry = start + i * 4
            string_pos = entry + self.u32(entry)
            length = self.u32(string_pos)
            raw = self.data[string_pos + 4 : string_pos + 4 + length]
            result.append(raw.decode("utf-8"))
        return result

    def vector_tables(self, table_pos: int, field_index: int) -> list[int]:
        start, count = self.vector(table_pos, field_index)
        return [start + i * 4 + self.u32(start + i * 4) for i in range(count)]

    def scalar_u64(self, table_pos: int, field_index: int, default: int = 0) -> int:
        field = self.field_pos(table_pos, field_index)
        return default if field is None else self.u64(field)


class Descriptor:
    def __init__(self, data: bytes):
        fb = FlatBuffer(data)
        root = fb.root
        self.pack_names = fb.vector_strings(root, 1)
        pack_tables = fb.vector_tables(root, 3)
        self.pack_info = [
            (fb.scalar_u64(table, 0), fb.scalar_u64(table, 1))
            for table in pack_tables
        ]

    def get_pack(self, name: str) -> tuple[int, int, int]:
        try:
            index = self.pack_names.index(name)
        except ValueError as exc:
            raise KeyError(f"pack not found in TRPFD: {name}") from exc
        size, count = self.pack_info[index]
        return index, size, count


def fnv1a64(text: str) -> int:
    value = FNV_BASIS
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return value


def parse_trpfs_filesystem(data: bytes) -> tuple[int, list[int], list[int]]:
    if len(data) < 16:
        raise ValueError("TRPFS is smaller than the 16-byte ONEFILE header")

    magic, fs_offset = struct.unpack_from("<Qq", data, 0)
    if fs_offset < 16 or fs_offset >= len(data):
        raise ValueError(f"invalid FileSystem offset in TRPFS header: {fs_offset:#x}")

    fb = FlatBuffer(data[fs_offset:])
    hashes = fb.vector_u64(fb.root, 0)
    offsets = fb.vector_u64(fb.root, 1)
    if len(hashes) != len(offsets):
        raise ValueError("TRPFS FileSystem hash/offset vector lengths differ")
    return magic, hashes, offsets


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trpfd", type=Path, help="matching arc/data.trpfd")
    parser.add_argument("trpfs", type=Path, help="matching arc/data.trpfs")
    parser.add_argument(
        "output",
        type=Path,
        help="output .trpak path",
    )
    parser.add_argument(
        "--pack",
        default=DEFAULT_MAIN_PACK,
        help=f"TRPFD pack name (default: {DEFAULT_MAIN_PACK})",
    )
    args = parser.parse_args()

    desc_data = args.trpfd.read_bytes()
    trpfs_data = args.trpfs.read_bytes()

    descriptor = Descriptor(desc_data)
    pack_index, pack_size, file_count = descriptor.get_pack(args.pack)

    magic, file_hashes, file_offsets = parse_trpfs_filesystem(trpfs_data)
    pack_hash = fnv1a64(args.pack)

    try:
        file_index = file_hashes.index(pack_hash)
    except ValueError as exc:
        raise SystemExit(
            f"error: FNV64 {pack_hash:016X} for {args.pack!r} is absent from TRPFS FileSystem"
        ) from exc

    pack_offset = file_offsets[file_index]
    pack_end = pack_offset + pack_size
    if pack_end > len(trpfs_data):
        raise SystemExit(
            f"error: pack range {pack_offset:#x}..{pack_end:#x} exceeds TRPFS size {len(trpfs_data):#x}"
        )

    payload = trpfs_data[pack_offset:pack_end]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)

    print(f"TRPFS magic : 0x{magic:016X}")
    print(f"pack index  : {pack_index}")
    print(f"file index  : {file_index}")
    print(f"pack name   : {args.pack}")
    print(f"pack hash   : 0x{pack_hash:016X}")
    print(f"pack offset : 0x{pack_offset:X}")
    print(f"pack size   : {pack_size} bytes")
    print(f"file count  : {file_count}")
    print(f"output      : {args.output}")
    print(f"sha256      : {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
