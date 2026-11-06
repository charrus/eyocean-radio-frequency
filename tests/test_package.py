"""Ensure manual installation preserves the diagnostic action description."""

import zipfile

from scripts import package


def test_package_contains_raw_service_description(tmp_path, monkeypatch):
    root = tmp_path
    component = root / "custom_components" / "eyocean"
    component.mkdir(parents=True)
    (component / "manifest.json").write_text('{"version": "test"}')
    (component / "__init__.py").write_text('"""Test integration."""')
    (component / "services.yaml").write_text("send_raw:\n  name: Send raw\n")
    (root / "README.md").write_text("Test")
    (root / "LICENSE").write_text("Test")
    monkeypatch.setattr(package, "ROOT", root)
    monkeypatch.setattr(package, "COMPONENT", component)
    package.main()
    with zipfile.ZipFile(root / "dist" / "eyocean-radio-frequency-test.zip") as archive:
        assert "custom_components/eyocean/services.yaml" in archive.namelist()
