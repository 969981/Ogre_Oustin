#!/usr/bin/env python3
"""Run Lua mock integration tests via system liblua (no Lua interpreter required).

Requires liblua5.4 or liblua5.3; e.g. apt install liblua5.4-0.
"""
from __future__ import annotations
import ctypes
import ctypes.util
from pathlib import Path
import sys


def main() -> int:
    lib = ctypes.util.find_library("lua5.4") or ctypes.util.find_library("lua5.3")
    if not lib:
        print("ERROR: liblua5.4 or liblua5.3 required for Lua mock integration tests")
        return 2
    lua = ctypes.CDLL(lib)
    V = ctypes.c_void_p
    lua.luaL_newstate.restype = V
    lua.luaL_openlibs.argtypes = [V]
    lua.luaL_loadstring.argtypes = [V, ctypes.c_char_p]
    lua.luaL_loadstring.restype = ctypes.c_int
    lua.lua_pcallk.argtypes = [V, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              ctypes.c_longlong, V]
    lua.lua_pcallk.restype = ctypes.c_int
    lua.lua_tolstring.argtypes = [V, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
    lua.lua_tolstring.restype = ctypes.c_char_p
    lua.lua_close.argtypes = [V]
    L = lua.luaL_newstate()
    if not L:
        raise RuntimeError("failed to open Lua state")
    try:
        lua.luaL_openlibs(L)
        root = Path(__file__).resolve().parents[1]
        patch = str(root / "patches/lua/ogre_oustin_emptyhand.lua")
        fixture = str(root / "tests/test_emptyhand.lua")
        command = f"arg_patch_path={patch!r}; assert(loadfile({fixture!r}))()"
        status = lua.luaL_loadstring(L, command.encode())
        if status == 0:
            status = lua.lua_pcallk(L, 0, 0, 0, 0, None)
        if status:
            length = ctypes.c_size_t()
            e = lua.lua_tolstring(L, -1, ctypes.byref(length))
            print("Lua test FAILED:", e.decode("utf-8", "replace") if e else status)
            return 1
        return 0
    finally:
        lua.lua_close(L)


if __name__ == "__main__":
    sys.exit(main())
