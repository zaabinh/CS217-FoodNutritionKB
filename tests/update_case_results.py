"""Chạy mọi ca trong tests/test_cases.md và ghi kết quả thật vào ``actual_result``.

Chỉ thay giá trị ``actual_result`` (khóa cuối của mỗi khối JSON) và dòng
"Trạng thái chung"; không đụng tới input/expected. Chạy lại bất kỳ lúc nào:
  python tests/update_case_results.py          # ghi vào test_cases.md
  python tests/update_case_results.py --check  # chỉ in kết quả, không ghi
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys

from case_runner import BLOCK, CASES_MD, run_case

WIDTH = 100
STATUS_LINE = re.compile(r"^\*\*Trạng thái chung:.*$", re.M)
COMMAND = "python tests/update_case_results.py"


def fmt(o, ind=0) -> str:
    one = json.dumps(o, ensure_ascii=False)
    if not isinstance(o, (dict, list)) or len(one) + ind <= WIDTH:
        return one
    pad = " " * (ind + 2)
    if isinstance(o, dict):
        body = [f"{pad}{json.dumps(k, ensure_ascii=False)}: {fmt(v, ind + 2)}" for k, v in o.items()]
        return "{\n" + ",\n".join(body) + "\n" + " " * ind + "}"
    return "[\n" + ",\n".join(pad + fmt(v, ind + 2) for v in o) + "\n" + " " * ind + "]"


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="không ghi tệp")
    args = parser.parse_args(argv)

    raw_text = CASES_MD.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw_text else "\n"
    text = raw_text.replace("\r\n", "\n")
    today = datetime.date.today().isoformat()
    passed = total = 0
    out, last = [], 0
    for m in BLOCK.finditer(text):
        case = json.loads(m.group(1))
        actual, problems = run_case(case)
        total += 1
        passed += not problems
        print(f"{case['id']}: {'PASS' if not problems else 'FAIL'}" + (f" — {problems}" if problems else ""))
        result = {"status": "PASS" if not problems else "FAIL", "run_on": today, "command": COMMAND,
                  "observed": actual}
        if problems:
            result["mismatches"] = problems
        block = m.group(1)
        pos = block.rindex('"actual_result":')
        block = block[:pos] + '"actual_result": ' + fmt(result, 2) + "\n}"
        out.append(text[last:m.start(1)] + block)
        last = m.end(1)
    out.append(text[last:])
    new_text = "".join(out)
    status = (f"**Trạng thái chung: đã thực thi ngày {today} — {passed}/{total} PASS.** "
              f"`actual_result` do `{COMMAND}` ghi tự động từ kết quả chương trình, không chép tay; "
              f"`python -m unittest discover -s tests` chạy lại cùng các ca này.")
    new_text = STATUS_LINE.sub(status, new_text, count=1)
    print(f"Tổng: {passed}/{total} PASS")
    if not args.check:
        CASES_MD.write_bytes(new_text.replace("\n", nl).encode("utf-8"))
        print(f"Đã ghi {CASES_MD}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
