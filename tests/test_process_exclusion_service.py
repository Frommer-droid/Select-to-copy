from __future__ import annotations

import unittest

from app.services.process_exclusion_service import ProcessExclusionService


class ProcessExclusionServiceTests(unittest.TestCase):
    def test_exclusion_match_exact_case_insensitive(self) -> None:
        service = ProcessExclusionService(process_names=["Code.exe"])
        self.assertTrue(service.is_process_excluded("code.exe"))
        self.assertTrue(service.is_process_excluded("CODE.EXE"))

    def test_exclusion_no_substring_match(self) -> None:
        service = ProcessExclusionService(process_names=["code.exe"])
        self.assertFalse(service.is_process_excluded("code-insiders.exe"))

    def test_exclusion_empty_list(self) -> None:
        service = ProcessExclusionService(process_names=[])
        self.assertFalse(service.is_process_excluded("code.exe"))


if __name__ == "__main__":
    unittest.main()
