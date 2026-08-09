from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from app.services.settings_service import SettingsService


class SettingsServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        self._project_root = Path(self._temp_dir.name)
        logger_name = f"test_settings_service_{id(self)}"
        self._logger = logging.getLogger(logger_name)
        self._logger.handlers.clear()
        self._logger.propagate = False

    def _create_service(self) -> SettingsService:
        return SettingsService(project_root=self._project_root, logger=self._logger)

    def test_settings_create_default_when_missing(self) -> None:
        service = self._create_service()
        settings = service.load_settings()

        self.assertTrue(service.settings_path.exists())
        self.assertIn("exclusions", settings)
        self.assertEqual([], settings["exclusions"]["process_names"])
        self.assertTrue(settings["exclusions"]["enabled"])

    def test_settings_persist_and_reload_exclusions(self) -> None:
        service = self._create_service()
        exclusions = service.get_exclusion_settings()
        exclusions.process_names = ["code.exe", "notepad.exe"]
        exclusions.enabled = True
        service.update_exclusion_settings(exclusions)

        reloaded = self._create_service().get_exclusion_settings()
        self.assertEqual(["code.exe", "notepad.exe"], reloaded.process_names)
        self.assertTrue(reloaded.enabled)

    def test_import_exclusions_from_json(self) -> None:
        service = self._create_service()
        import_path = self._project_root / "import_exclusions.json"
        import_payload = {
            "enabled": True,
            "process_names": ["code.exe", "Code.EXE", "notepad.exe"],
        }
        import_path.write_text(json.dumps(import_payload), encoding="utf-8")

        exclusions = service.import_exclusions(import_path)

        self.assertEqual(["code.exe", "notepad.exe"], exclusions.process_names)
        self.assertTrue(exclusions.enabled)

    def test_export_exclusions_to_json(self) -> None:
        service = self._create_service()
        exclusions = service.get_exclusion_settings()
        exclusions.enabled = True
        exclusions.process_names = ["code.exe", "notepad.exe"]
        service.update_exclusion_settings(exclusions)

        export_path = self._project_root / "exported_exclusions.json"
        service.export_exclusions(export_path)

        exported_payload = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(["code.exe", "notepad.exe"], exported_payload["process_names"])
        self.assertTrue(exported_payload["enabled"])

    def test_import_invalid_json_keeps_previous_state(self) -> None:
        service = self._create_service()
        exclusions = service.get_exclusion_settings()
        exclusions.process_names = ["code.exe"]
        service.update_exclusion_settings(exclusions)

        import_path = self._project_root / "broken.json"
        import_path.write_text("{not valid json", encoding="utf-8")

        with self.assertRaises(json.JSONDecodeError):
            service.import_exclusions(import_path)

        reloaded = service.get_exclusion_settings()
        self.assertEqual(["code.exe"], reloaded.process_names)


if __name__ == "__main__":
    unittest.main()
