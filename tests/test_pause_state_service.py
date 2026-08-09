from __future__ import annotations

import unittest

from app.services.pause_state_service import PauseStateService


class PauseStateServiceTests(unittest.TestCase):
    def test_effective_pause_manual_or_auto(self) -> None:
        service = PauseStateService()
        self.assertFalse(service.is_effectively_paused())

        service.set_manual_paused(True)
        self.assertTrue(service.is_effectively_paused())

        service.set_manual_paused(False)
        self.assertFalse(service.is_effectively_paused())

        service.apply_auto_pause("code.exe", should_pause=True)
        self.assertTrue(service.is_effectively_paused())

    def test_auto_pause_state_transition(self) -> None:
        service = PauseStateService()

        changed = service.apply_auto_pause("code.exe", should_pause=True)
        self.assertTrue(changed)
        self.assertTrue(service.auto_paused)
        self.assertEqual("code.exe", service.auto_pause_process_name)

        changed = service.apply_auto_pause("code.exe", should_pause=True)
        self.assertFalse(changed)

        changed = service.apply_auto_pause("notepad.exe", should_pause=False)
        self.assertTrue(changed)
        self.assertFalse(service.auto_paused)
        self.assertIsNone(service.auto_pause_process_name)


if __name__ == "__main__":
    unittest.main()
