"""Build and verify a clean manual-install ZIP (does not contact Home Assistant)."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "eyocean"


def main() -> None:
    version = json.loads((COMPONENT / "manifest.json").read_text())["version"]
    files = sorted(
        p for p in COMPONENT.rglob("*") if p.is_file() and p.suffix in {".py", ".json", ".txt"}
    )
    files = [p for p in files if "__pycache__" not in p.parts]
    assert files and (COMPONENT / "__init__.py") in files
    archive = ROOT / "dist" / f"eyocean-radio-frequency-{version}.zip"
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for file in files:
            zipped.write(file, file.relative_to(ROOT))
        zipped.write(ROOT / "README.md", "README.md")
        zipped.write(ROOT / "LICENSE", "LICENSE")
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert set(zipped.namelist()) == {str(f.relative_to(ROOT)) for f in files} | {
            "README.md",
            "LICENSE",
        }
        assert all("secrets" not in name and ".venv" not in name for name in zipped.namelist())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(
        f"{archive}\nSHA256 {digest}\n"
        f"Verified {len(files)} integration files plus README and MIT LICENSE"
    )


if __name__ == "__main__":
    main()
