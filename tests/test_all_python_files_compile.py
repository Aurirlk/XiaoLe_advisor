from __future__ import annotations

from pathlib import Path
import py_compile


ROOT = Path(__file__).resolve().parents[1]


def iter_python_files():
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts or "__pycache__" in path.parts:
            continue
        yield path


def test_every_python_file_is_compilable():
    failures: list[str] = []
    for file_path in iter_python_files():
        try:
            py_compile.compile(str(file_path), doraise=True)
        except Exception as exc:  # pragma: no cover
            failures.append(f"{file_path}: {exc}")
    assert not failures, "发现不可编译文件:\n" + "\n".join(failures)
