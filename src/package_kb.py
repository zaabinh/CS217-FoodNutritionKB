"""Đóng gói CSTT để nộp: dist/CS217_TH2_Nhom1_KnowledgeBase.zip.

Trước khi nén, chạy lại kiểm tra CSTT, toàn bộ test và demo; kết quả được lưu
trong thư mục bang_chung/ của tệp ZIP làm bằng chứng chạy thử. Dừng nếu có lỗi.

Chạy:  python src/package_kb.py [--out THU_MUC]
"""
from __future__ import annotations

import argparse
import datetime
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIP_NAME = "CS217_TH2_Nhom1_KnowledgeBase.zip"
INCLUDE = ["README.md", "kb/*.json", "docs/*.md", "src/*.py", "tests/*.py", "tests/*.md"]
STEPS = [
    ("validate_kb.txt", [sys.executable, "src/validate_kb.py"]),
    ("tests.txt", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("demo.txt", [sys.executable, "src/demo_queries.py", "demo"]),
]


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Đóng gói CSTT kèm bằng chứng chạy thử.")
    parser.add_argument("--out", default=str(ROOT / "dist"), help="thư mục đặt tệp ZIP (mặc định: dist/)")
    args = parser.parse_args(argv)

    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    evidence = {}
    for name, cmd in STEPS:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
        output = f"$ {' '.join(Path(c).name if i == 0 else c for i, c in enumerate(cmd))}\n{proc.stdout}{proc.stderr}"
        evidence[name] = output
        print(f"{name}: mã thoát {proc.returncode}")
        if proc.returncode != 0:
            print(output)
            print("Dừng đóng gói vì bước trên thất bại.")
            return 1

    files = sorted({p for pattern in INCLUDE for p in ROOT.glob(pattern) if p.is_file()})
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ZIP_NAME
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())
        for name, text in evidence.items():
            zf.writestr(f"bang_chung/{name}", f"# Chạy lúc {stamp}\n{text}")
    print(f"Đã tạo {target} ({len(files)} tệp + {len(evidence)} tệp bằng chứng)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
