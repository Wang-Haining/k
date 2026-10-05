"""Download and checksum the two public archived registry sources."""

import hashlib
import shutil
import urllib.request
import zipfile

from config import DATA_DIR
from construct.reporter import dump

SOURCES = (
    ("10091147", "AACT-2022-11-09.zip", "AACT-2022-11-09.zip", "1d4e6d141f40d300186fdd3d0a5980b1"),
    (
        "13984069",
        "responsible_parties.txt",
        "AACT_20240927_responsible_parties.txt",
        "7a05bfb5f6e64ff8dad4ff0f8696ca35",
    ),
)


def main():
    folder = DATA_DIR / "contemporaneous"
    (folder / "sources").mkdir(parents=True, exist_ok=True)
    for record, remote, local, expected in SOURCES:
        url = f"https://zenodo.org/records/{record}/files/{remote}?download=1"
        path = folder / "sources" / local
        if not path.exists():
            with urllib.request.urlopen(url, timeout=90) as response, path.open("wb") as target:
                shutil.copyfileobj(response, target)
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "md5").hexdigest()
        assert digest == expected, f"Snapshot checksum mismatch: expected {expected}, got {digest}"
        if remote.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                members = [
                    {"member": item.filename, "bytes": item.file_size, "CRC": item.CRC} for item in archive.infolist()
                ]
            dump(
                folder / "AACT_20221109_archive_inventory.json",
                {
                    "source": f"https://zenodo.org/records/{record}",
                    "md5": digest,
                    "claimed_collection_date": "2022-11-09",
                    "public_deposit_date": "2023-11-09",
                    "published_checksum_verified": True,
                    "members": members,
                },
            )
        else:
            dump(
                folder / "aact_responsible_parties_manifest.json",
                {
                    "source_record": f"https://zenodo.org/records/{record}",
                    "download_url": url,
                    "claimed_snapshot_date": "2024-09-27",
                    "deposit_date": "2024-10-23",
                    "file_md5": digest,
                    "published_md5_verified": True,
                },
            )
        print("snapshot checksum verified; bytes:", path.stat().st_size)


if __name__ == "__main__":
    main()
