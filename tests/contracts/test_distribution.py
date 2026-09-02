from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


class DistributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = yaml.safe_load((ROOT / "distribution.yaml").read_text(encoding="utf-8"))
        self.owned = self.manifest["distribution_owned"]

    def test_manifest_installs_only_runtime_owned_surfaces(self) -> None:
        self.assertEqual(self.manifest["name"], "company-os")
        required = {
            "setup.py",
            "setup.cmd",
            "compose.yaml",
            "apps/installer/__init__.py",
            "apps/installer/runtime.py",
            "apps/installer/cli",
            "apps/installer/workspace.py",
            "apps/installer/profile.py",
            "apps/installer/provider_catalog.py",
            "apps/installer/composio_session.py",
            "apps/installer/connection_evals.py",
            "apps/installer/providers",
            "apps/installer/prompts",
            "workspace.hermes.template.md",
            "automations",
            "templates",
            "skills/pm-daily/templates",
            "skills/pm-weekly/templates",
            "plugins/platforms/notion/plugin.yaml",
        }
        self.assertTrue(required.issubset(set(self.owned)))
        self.assertNotIn("workspace.hermes.md", self.owned)
        self.assertNotIn("apps/company_os/schemas", self.owned)
        self.assertFalse(any(path.endswith((".js", ".mjs")) for path in self.owned))
        self.assertIn("skills/pm-daily/SKILL.md", self.owned)
        self.assertIn("skills/pm-weekly/SKILL.md", self.owned)
        self.assertIn("apps/eval_viewer/build.py", self.owned)
        self.assertIn("apps/eval_viewer/model.py", self.owned)
        for excluded in ("docs", "tickets", "tests", "seed", "evals/filesystem"):
            self.assertFalse(any(path == excluded or path.startswith(f"{excluded}/") for path in self.owned))
        self.assertFalse(any("company-os-onboard" in path for path in self.owned))
        self.assertNotIn("NGROK_AUTHTOKEN", {
            item["name"] for item in self.manifest.get("env_requires", [])
        })

    def test_every_owned_path_exists_and_payload_is_small(self) -> None:
        files: set[Path] = set()
        for relative in self.owned:
            path = ROOT / relative
            self.assertTrue(path.exists(), relative)
            if path.is_file():
                files.add(path)
            else:
                files.update(item for item in path.rglob("*") if item.is_file() and ".pyc" not in item.suffix)
        payload_bytes = sum(path.stat().st_size for path in files)
        self.assertLess(payload_bytes, 1_000_000, payload_bytes)
        self.assertFalse(any(path.suffix in {".js", ".mjs"} for path in files))
        self.assertFalse(any(path.name in {"package.json", "package-lock.json"} for path in files))
        text_payload = "\n".join(
            path.read_text(encoding="utf-8")
            for path in files
            if path.suffix in {".md", ".py", ".json", ".yaml", ".yml"}
        )
        self.assertNotIn("javascript", text_payload.lower())


if __name__ == "__main__":
    unittest.main()
