"""Normalize registry names and exclude professional titles."""

import re
import unicodedata

TITLES = {
    "dr",
    "prof",
    "md",
    "phd",
    "mph",
    "ms",
    "msc",
    "mscr",
    "mshp",
    "mhs",
    "mas",
    "rn",
    "np",
    "mbbs",
    "do",
    "pharmd",
    "facs",
    "facp",
    "faap",
    "frcpc",
    "jr",
    "sr",
    "ii",
    "iii",
    "mba",
    "ma",
    "bs",
    "ba",
    "mpp",
    "dsc",
    "dnp",
    "psyd",
}


def norm(s):
    return " ".join(
        re.findall("[a-z0-9]+", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())
    )
