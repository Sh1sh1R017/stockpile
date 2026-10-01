"""Strict import smoke test: every application Python module must import cleanly.

This intentionally requires no API keys, GPU, network access, or .env file. Any import
failure is surfaced with the module name so CI catches import-time regressions such as
configuration parsing crashes.
"""

from __future__ import annotations

import importlib
import pkgutil

import ai_broll_autopilot


def test_all_application_modules_import_cleanly() -> None:
    failures = []
    package_path = list(ai_broll_autopilot.__path__)

    for module_info in pkgutil.walk_packages(package_path, ai_broll_autopilot.__name__ + "."):
        module_name = module_info.name
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001 - smoke test must report every import failure
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")

    assert not failures, "Application import smoke test failed:\n" + "\n".join(failures)
