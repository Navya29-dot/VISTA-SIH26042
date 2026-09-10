"""Export a confirmed local IndicTrans2 checkpoint and create an INT8 copy.

The model identifier is deliberately required: AI4Bharat checkpoint names and
parameter counts change, so never bake an unverified repo into the app.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True, help="Confirmed HF repo or local checkpoint")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    from optimum.exporters.onnx import main_export
    from onnxruntime.quantization import QuantType, quantize_dynamic

    args.output.mkdir(parents=True, exist_ok=True)
    fp32_dir = args.output / "fp32"
    main_export(
        model_name_or_path=args.model_id,
        output=fp32_dir,
        task="text2text-generation",
        framework="pt",
        trust_remote_code=True,
    )

    for source in fp32_dir.glob("*.onnx"):
        target = args.output / f"{source.stem}.int8.onnx"
        quantize_dynamic(str(source), str(target), weight_type=QuantType.QInt8)
    print(f"INT8 ONNX files written to {args.output}")


if __name__ == "__main__":
    main()
