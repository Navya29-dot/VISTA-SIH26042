from __future__ import annotations

import argparse
from pathlib import Path

from backend.indictrans2 import translate


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate English text to Santali offline with IndicTrans2.")
    parser.add_argument("input", type=Path, help="UTF-8 text file to translate")
    parser.add_argument("-o", "--output", type=Path, help="Output UTF-8 text file (stdout if omitted)")
    parser.add_argument("--source", default="en-IN", choices=("en-IN", "en"))
    parser.add_argument("--target", default="sat", choices=("sat", "sat-IN"))
    args = parser.parse_args()

    result = translate(
        args.input.read_text(encoding="utf-8"),
        source_language_code=args.source,
        target_language_code=args.target,
    )["translated_text"]
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)


if __name__ == "__main__":
    main()
