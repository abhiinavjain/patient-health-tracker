"""Download the public training datasets into data/raw/.

Usage:  python -m healthml.download [dataset ...]
"""

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

from .config import DATA_RAW, DATASETS


def dataset_dir(name: str) -> Path:
    return DATA_RAW / name


def csv_path(name: str) -> Path:
    return dataset_dir(name) / DATASETS[name]["csv"]


def _extract_csv(archive: Path, target_csv: str, dest: Path) -> None:
    """Find `target_csv` anywhere inside the zip (including nested zips) and write it to dest."""
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            if Path(member).name == target_csv:
                with zf.open(member) as src, open(dest / target_csv, "wb") as out:
                    shutil.copyfileobj(src, out)
                return
        for member in zf.namelist():
            if member.endswith(".zip"):
                nested = dest / Path(member).name
                with zf.open(member) as src, open(nested, "wb") as out:
                    shutil.copyfileobj(src, out)
                try:
                    _extract_csv(nested, target_csv, dest)
                    return
                except FileNotFoundError:
                    continue
                finally:
                    nested.unlink(missing_ok=True)
    raise FileNotFoundError(f"{target_csv} not found in {archive}")


def download(name: str, force: bool = False) -> Path:
    spec = DATASETS[name]
    out_dir = dataset_dir(name)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = csv_path(name)
    if final.exists() and not force:
        print(f"[skip] {name}: {final} already exists")
        return final

    raw = out_dir / spec["filename"]
    print(f"[get ] {name}: {spec['url']}")
    req = urllib.request.Request(spec["url"], headers={"User-Agent": "healthml-dataset-fetch"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(raw, "wb") as out:
        shutil.copyfileobj(resp, out)

    if raw.suffix == ".zip":
        _extract_csv(raw, spec["csv"], out_dir)
        raw.unlink()
    print(f"[ok  ] {name}: {final} ({final.stat().st_size / 1e6:.1f} MB)")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="*", default=list(DATASETS), choices=list(DATASETS))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    for name in args.datasets:
        download(name, force=args.force)


if __name__ == "__main__":
    main()
