# -*- coding: utf-8 -*-
"""通用回收站删除工具：SHFileOperationW + FOF_ALLOWUNDO"""
import os
import sys
import ctypes


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ('hwnd', ctypes.c_void_p),
        ('wFunc', ctypes.c_uint),
        ('pFrom', ctypes.c_wchar_p),
        ('pTo', ctypes.c_wchar_p),
        ('fFlags', ctypes.c_ushort),
        ('fAnyOperationsAborted', ctypes.c_int),
        ('hNameMappings', ctypes.c_void_p),
        ('lpszProgressTitle', ctypes.c_wchar_p),
    ]


FO_DELETE = 3
FOF_ALLOWUNDO = 0x40
FOF_NOCONFIRMATION = 0x10
FOF_SILENT = 0x4
FOF_NOERRORUI = 0x400


def recycle(paths):
    existing = [p for p in paths if os.path.exists(p)]
    missing = [p for p in paths if not os.path.exists(p)]
    if not existing:
        print('nothing to delete')
        return 0
    # 分小批，每批最多 10 个（安全规则）
    rc_all = 0
    for i in range(0, len(existing), 10):
        chunk = existing[i:i + 10]
        pfrom = '\x00'.join(chunk) + '\x00\x00'
        op = SHFILEOPSTRUCTW()
        op.hwnd = None
        op.wFunc = FO_DELETE
        op.pFrom = pfrom
        op.pTo = None
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        rc_all |= rc
        left = [p for p in chunk if os.path.exists(p)]
        print(f'batch {i//10+1}: rc={rc} submitted={len(chunk)} failed={left}')
        if rc != 0 or left:
            print('ABORT: failure detected, stopping')
            break
    if missing:
        print('missing (skipped):', missing)
    return rc_all


if __name__ == '__main__':
    # 用法：python recycle_tool.py <listfile>
    listfile = sys.argv[1]
    with open(listfile, encoding='utf-8') as f:
        paths = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    sys.exit(1 if recycle(paths) else 0)
