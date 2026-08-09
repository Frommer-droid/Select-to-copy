from __future__ import annotations

import ctypes
import unittest
from unittest.mock import patch

from app.services import windows_scancode_input_service as input_service


class WindowsScancodeInputServiceTests(unittest.TestCase):
    def test_send_scancode_writes_extra_info_to_winapi_event(self) -> None:
        captured_extra_info: list[int] = []

        def fake_send_input(_count, event_pointer, _size) -> int:
            event = ctypes.cast(
                event_pointer,
                ctypes.POINTER(input_service.INPUT),
            ).contents
            captured_extra_info.append(int(event.ki.dwExtraInfo))
            return 1

        with patch.object(input_service, "SendInput", side_effect=fake_send_input):
            self.assertTrue(
                input_service._send_scancode(
                    input_service.SCAN_C,
                    extra_info=input_service.AUTOHOTKEY_IGNORE_MARKER,
                )
            )

        self.assertEqual([input_service.AUTOHOTKEY_IGNORE_MARKER], captured_extra_info)

    def test_ctrl_c_marks_every_event_for_autohotkey_ignore(self) -> None:
        sent_events: list[tuple[int, bool, int]] = []

        def capture_event(scan_code: int, key_up: bool = False, extra_info: int = 0) -> bool:
            sent_events.append((scan_code, key_up, extra_info))
            return True

        scan_codes = {
            input_service.VK_LCONTROL: input_service.SCAN_LCONTROL,
            input_service.VK_C: input_service.SCAN_C,
        }

        with (
            patch.object(
                input_service,
                "_map_virtual_key_to_scan_code",
                side_effect=scan_codes.__getitem__,
            ),
            patch.object(input_service, "_send_scancode", side_effect=capture_event),
            patch.object(input_service.time, "sleep"),
        ):
            self.assertTrue(input_service.send_left_ctrl_c())

        self.assertEqual(
            [
                (input_service.SCAN_LCONTROL, False, input_service.AUTOHOTKEY_IGNORE_MARKER),
                (input_service.SCAN_C, False, input_service.AUTOHOTKEY_IGNORE_MARKER),
                (input_service.SCAN_C, True, input_service.AUTOHOTKEY_IGNORE_MARKER),
                (input_service.SCAN_LCONTROL, True, input_service.AUTOHOTKEY_IGNORE_MARKER),
            ],
            sent_events,
        )


if __name__ == "__main__":
    unittest.main()
