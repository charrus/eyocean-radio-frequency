"""Use this checkout, not the HA test plugin's dummy custom_components package."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def custom_integration_path(enable_custom_integrations, monkeypatch):
    import custom_components

    monkeypatch.setattr(
        custom_components, "__path__", [str(Path(__file__).parents[1] / "custom_components")]
    )
