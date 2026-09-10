"""Run one local translation and print process RSS for Phase 1 validation."""

from __future__ import annotations

import argparse
import os

from backend.indictrans2 import translate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="?", default="Namaste, today we learn numbers.")
    args = parser.parse_args()
    result = translate(args.text, "en-IN", "sat")
    print(result["translated_text"])
    if os.name != "nt":
        import resource

        # Linux reports KiB; macOS reports bytes. Android validation still uses adb.
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        print(f"Maximum resident set: {usage / 1024:.1f} MB")
    else:
        print("Maximum resident set: use Windows Task Manager or Android dumpsys meminfo.")


if __name__ == "__main__":
    main()
