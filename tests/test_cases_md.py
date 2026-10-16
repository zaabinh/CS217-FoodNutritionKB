"""Các ca kiểm thử đặc tả trong tests/test_cases.md, chạy tự động.

Chạy:  python -m unittest discover -s tests   (hoặc: python -m pytest tests)
"""
import unittest

from case_runner import RUNNERS, parse_cases, run_case

CASES = parse_cases()


class SpecTestCases(unittest.TestCase):
    def test_every_case_has_a_runner(self):
        ids = [c["id"] for c in CASES]
        self.assertEqual(len(ids), len(set(ids)), "mã TC bị trùng trong test_cases.md")
        self.assertEqual(sorted(ids), sorted(RUNNERS), "mỗi TC trong test_cases.md cần đúng một hàm chạy")


def _make_test(case):
    def test(self):
        actual, problems = run_case(case)
        self.assertEqual(problems, [], f"{case['id']} sai khác: {problems}; thực tế: {actual}")
    test.__doc__ = f"{case['id']} — luật {', '.join(case.get('rules', [])) or 'truy vấn'}"
    return test


for _case in CASES:
    setattr(SpecTestCases, f"test_{_case['id']}", _make_test(_case))


if __name__ == "__main__":
    unittest.main()
