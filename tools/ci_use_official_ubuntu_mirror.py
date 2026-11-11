"""Select Canonical's signed Ubuntu archive when hosted runner Azure mirror stalls.

Only the archive hostname is rewritten. Suites, components, signatures and
security repositories are preserved. apt continues enforcing signed metadata.
"""
from pathlib import Path

AZURE = "http://azure.archive.ubuntu.com/ubuntu"
OFFICIAL = "http://archive.ubuntu.com/ubuntu"


def rewrite_sources(text: str) -> str:
    return text.replace(AZURE, OFFICIAL)


def main() -> None:
    paths = [Path("/etc/apt/sources.list"), *Path("/etc/apt/sources.list.d").glob("*.sources"),
             *Path("/etc/apt/sources.list.d").glob("*.list")]
    for path in paths:
        if not path.is_file():
            continue
        before = path.read_text(encoding="utf-8")
        after = rewrite_sources(before)
        if after != before:
            path.write_text(after, encoding="utf-8")
            print(f"Switched {path} from Azure mirror to official Ubuntu archive")


if __name__ == "__main__":
    main()
