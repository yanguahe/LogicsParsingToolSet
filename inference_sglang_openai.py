#!/usr/bin/env python3
"""
Call a running SGLang server (OpenAI-compatible) for Logics-Parsing-style inference.

Run this script inside the ROCm / SGLang container where the runtime dependencies
are installed and the target server is reachable, not on the bare host.

This script matches the *effective* behavior of ``inference_v2.py`` for Logics-Parsing-v2.
That HF path passes ``temperature``/``top_p`` into ``model.generate()``, but the public
``generation_config.json`` keeps ``do_sample`` disabled, so the actual decode path is greedy
with ``repetition_penalty=1.05`` and ``max_new_tokens=16384``. We force the same behavior on
the SGLang side by default.

Images: send the original file as data URL (like passing a file path into ``processor`` in
``inference_v2.py``). Resize / ``min_pixels`` / ``max_pixels`` are applied on the SGLang server,
not in this client.

Outputs use an ``_sglang`` suffix on the basename only when this script auto-generates the output
path. If you pass ``--output_path demo_input_output/output_demo1``, the output filenames match
``inference_v2.py`` exactly.

Use after: ./run_sglang_logics_server.sh

Uses a ``urllib`` opener with ``ProxyHandler({})`` so ``HTTP_PROXY`` does not break calls to
``127.0.0.1``.

Examples:
  python3 inference_sglang_openai.py

  python3 inference_sglang_openai.py \\
    --image_path demo_input_output/demo1.png \\
    --output_path demo_input_output/output_demo1
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DEMO_DIR = REPO_ROOT / "demo_input_output"
DEFAULT_MODEL_PATH = REPO_ROOT / "weights" / "Logics-Parsing-v2"

# Match inference_v2.py model.generate.
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TEMPERATURE = 0.1
DEFAULT_TOP_P = 0.5
DEFAULT_REPETITION_PENALTY = 1.05
DEFAULT_OPENAI_HOST = "127.0.0.1"
DEFAULT_OPENAI_PORT = 30000


def _resolve_openai_port(port: Optional[int]) -> int:
    if port is not None:
        return port

    for env_name in ("OPENAI_PORT", "SGLANG_PORT"):
        value = os.environ.get(env_name)
        if not value:
            continue
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(
                f"Environment variable {env_name} must be an integer port, got {value!r}."
            ) from exc

    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
        if parsed.port is not None:
            return parsed.port
        raise ValueError(
            "Environment variable OPENAI_BASE_URL must include an explicit port, "
            f"got {base_url!r}."
        )

    return DEFAULT_OPENAI_PORT


def build_openai_base_url(port: int) -> str:
    return f"http://{DEFAULT_OPENAI_HOST}:{port}/v1"


def _image_file_data_url(image_path: Path) -> str:
    """Original file bytes as data URL — same role as passing a file path into ``processor`` in inference_v2."""
    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    mime = "image/png"
    suf = image_path.suffix.lower()
    if suf in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif suf == ".webp":
        mime = "image/webp"
    return f"data:{mime};base64,{b64}"


def _request_json(
    *,
    base_url: str,
    path: str,
    api_key: str,
    payload: Optional[Dict] = None,
    timeout: float = 600.0,
) -> Dict:
    url = base_url.rstrip("/") + path
    headers = {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if api_key:
        headers["Authorization"] = "Bearer " + api_key

    request = urllib_request.Request(url, data=data, headers=headers)
    opener = urllib_request.build_opener(urllib_request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError("HTTP {} for {}: {}".format(exc.code, url, body))
    except urllib_error.URLError as exc:
        raise RuntimeError("Failed to reach {}: {}".format(url, exc))


def _resolve_served_model_name(
    base_url: str,
    api_key: str,
    requested_model: Optional[str],
) -> str:
    if requested_model:
        return requested_model

    try:
        models = _request_json(
            base_url=base_url,
            path="/models",
            api_key=api_key,
        )
    except Exception as exc:
        print(
            f"[warn] failed to query /v1/models ({exc}); falling back to model='default'",
            file=sys.stderr,
        )
        return "default"

    model_data = models.get("data") or []
    if model_data:
        return model_data[0]["id"]

    print("[warn] /v1/models returned no data; falling back to model='default'", file=sys.stderr)
    return "default"


def _hf_generation_uses_sampling(model_path: Path) -> bool:
    generation_config_path = model_path / "generation_config.json"
    if not generation_config_path.is_file():
        return False

    try:
        config = json.loads(generation_config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(
            f"[warn] failed to read {generation_config_path}: {exc}; assuming greedy decode",
            file=sys.stderr,
        )
        return False

    return bool(config.get("do_sample", False))


def _resolve_effective_decoding(
    *,
    model_path: Path,
    decode_mode: str,
    temperature: float,
    top_p: float,
) -> Tuple[float, Optional[float], Dict]:
    if decode_mode == "sampling":
        return temperature, top_p, {}

    if _hf_generation_uses_sampling(model_path):
        return temperature, top_p, {}

    # Match inference_v2.py effective behavior for Logics-Parsing-v2:
    # generation_config.do_sample is false, so HF ignores temperature/top_p
    # and runs greedy decode with repetition_penalty applied.
    return 0.0, None, {"top_k": 1}


def run_one(
    *,
    base_url: str,
    api_key: str,
    model: str,
    image_path: Path,
    output_path: Path,
    prompt: str,
    max_tokens: int,
    temperature: float,
    top_p: Optional[float],
    repetition_penalty: float,
    request_overrides: Dict,
) -> str:
    url = _image_file_data_url(image_path)

    # SGLang accepts backend-specific sampling keys as top-level OpenAI-compatible request fields.
    extra_body: dict = {
        "repetition_penalty": repetition_penalty,
    }
    extra_body.update(request_overrides)

    request_payload = dict(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if top_p is not None:
        request_payload["top_p"] = top_p
    request_payload.update(extra_body)

    resp = _request_json(
        base_url=base_url,
        path="/chat/completions",
        api_key=api_key,
        payload=request_payload,
    )
    raw_output = (((resp.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_raw_path = Path(str(output_path) + "_raw.mmd")
    output_mmd_path = Path(str(output_path) + ".mmd")
    output_img_path = Path(str(output_path) + "_vis.png")

    output_raw_path.write_text(raw_output, encoding="utf-8")

    from inference_v2 import plot_bbox, qwenvl_cast_html_tag

    plot_bbox(str(image_path), raw_output, str(output_img_path))
    markdown_output = qwenvl_cast_html_tag(raw_output)
    output_mmd_path.write_text(markdown_output, encoding="utf-8")

    return raw_output


def main() -> None:
    p = argparse.ArgumentParser(
        description="OpenAI-compatible client for SGLang Logics-Parsing server (aligned with inference_v2).",
    )
    p.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "SGLang server port. Base URL is derived as "
            f"http://{DEFAULT_OPENAI_HOST}:<port>/v1. If omitted, use "
            "$OPENAI_PORT, then $SGLANG_PORT, then the port from $OPENAI_BASE_URL, else "
            f"{DEFAULT_OPENAI_PORT}."
        ),
    )
    p.add_argument(
        "--model",
        default=os.environ.get("SGLANG_MODEL"),
        help="Model id exposed by /v1/models. If omitted, auto-detect the first served model.",
    )
    p.add_argument(
        "--model_path",
        type=Path,
        default=Path(os.environ.get("MODEL_PATH", str(DEFAULT_MODEL_PATH))),
        help="Weight dir (same model as server; image decode/resize happens on server).",
    )
    p.add_argument(
        "--image_path",
        type=Path,
        default=None,
        help="Single input image. If omitted, runs demo 1..3 under demo_input_output/.",
    )
    p.add_argument(
        "--output_path",
        type=Path,
        default=None,
        help="Output path prefix (files get _raw.mmd / .mmd / _vis.png). Required with --image_path unless using defaults.",
    )
    p.add_argument(
        "--demo_dir",
        type=Path,
        default=DEFAULT_DEMO_DIR,
        help=f"Directory for batch demo images (default: {DEFAULT_DEMO_DIR})",
    )
    p.add_argument("--prompt", type=str, default="QwenVL HTML")
    p.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    p.add_argument("--top_p", type=float, default=DEFAULT_TOP_P)
    p.add_argument(
        "--decode_mode",
        choices=("hf-equivalent", "sampling"),
        default=os.environ.get("SGLANG_DECODE_MODE", "hf-equivalent"),
        help=(
            "hf-equivalent: match inference_v2.py effective decode behavior. "
            "sampling: send temperature/top_p literally to SGLang."
        ),
    )
    p.add_argument(
        "--repetition_penalty",
        type=float,
        default=DEFAULT_REPETITION_PENALTY,
        help="Match inference_v2 model.generate repetition_penalty (default 1.05).",
    )
    args = p.parse_args()

    try:
        port = _resolve_openai_port(args.port)
    except ValueError as exc:
        p.error(str(exc))
    base_url = build_openai_base_url(port)

    api_key = os.environ.get("OPENAI_API_KEY", "EMPTY")
    model = _resolve_served_model_name(base_url, api_key, args.model)
    temperature, top_p, request_overrides = _resolve_effective_decoding(
        model_path=args.model_path,
        decode_mode=args.decode_mode,
        temperature=args.temperature,
        top_p=args.top_p,
    )

    if args.decode_mode == "hf-equivalent" and temperature == 0.0 and top_p is None:
        print(
            "[info] generation_config.do_sample is false; using greedy SGLang decode to match inference_v2.py",
            file=sys.stderr,
        )

    common_kw = dict(
        base_url=base_url,
        api_key=api_key,
        model=model,
        prompt=args.prompt,
        max_tokens=args.max_tokens,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=args.repetition_penalty,
        request_overrides=request_overrides,
    )

    if args.image_path is not None:
        out = args.output_path
        if out is None:
            out = args.image_path.parent / f"output_{args.image_path.stem}_sglang"
        text = run_one(
            image_path=args.image_path,
            output_path=out,
            **common_kw,
        )
        print(text)
        return

    demo_dir = args.demo_dir
    for n in (1, 2, 3):
        image_path = demo_dir / f"demo{n}.png"
        output_path = demo_dir / f"output_demo{n}_sglang"
        if not image_path.is_file():
            print(f"[warn] skip missing image: {image_path}", file=sys.stderr)
            continue
        print(f"[info] demo{n}: {image_path} -> {output_path}.*", file=sys.stderr)
        run_one(image_path=image_path, output_path=output_path, **common_kw)


if __name__ == "__main__":
    main()
