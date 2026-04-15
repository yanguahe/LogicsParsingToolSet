#!/usr/bin/env python3
"""
Batch process PDF pages with Logics-Parsing v2 via SGLang API.
Uses OpenAI-compatible API instead of local model loading.
Supports concurrent inference for multiple pages.

Run after starting the SGLang server, for example:
  bash run_sglang_logics_server.sh

Examples using PDFs under demo_pdfs/:
  python3 run_logics_parsing_api.py \
    --pdf_path "demo_pdfs/03-MemoryHierarchy.pdf" \
    --output_dir "demo_pdfs/03-MemoryHierarchy"

  python3 run_logics_parsing_api.py \
    --pdf_path "demo_pdfs/2020-04-14 - Memory, IO, and CU Architecture on gfx9 GPUs.pdf" \
    --output_dir "demo_pdfs/gfx9-memory-io-cu"

  python3 run_logics_parsing_api.py \
    --pdf_path "demo_pdfs/03-MemoryHierarchy.pdf" \
    --output_dir "demo_pdfs/03-MemoryHierarchy-pages-1-5" \
    --start_page 1 \
    --end_page 5 \
    --concurrency 8

  python3 run_logics_parsing_api.py \
    --pdf_path "demo_pdfs/03-MemoryHierarchy.pdf" \
    --output_dir "demo_pdfs/03-MemoryHierarchy" \
    --combine_only
"""

import os
import sys
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import re

from inference_sglang_openai import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_PATH,
    DEFAULT_REPETITION_PENALTY,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    _image_file_data_url,
    _request_json,
    _resolve_effective_decoding,
    _resolve_served_model_name,
)


def pdf_to_images(pdf_path, output_dir, dpi=150):
    """Convert PDF pages to PNG images."""
    try:
        import fitz  # PyMuPDF  # pyright: ignore[reportMissingImports]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyMuPDF is required for PDF rasterization. Install it with "
            "`python3 -m pip install PyMuPDF` in the runtime environment."
        ) from exc

    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_path = os.path.join(output_dir, f"page_{page_num+1:03d}.png")
        pix.save(img_path)
        image_paths.append(img_path)
        print(f"Converted page {page_num+1}/{len(doc)} -> {img_path}")
    doc.close()
    return image_paths


def extract_and_save_figures(html_output, image_path, output_dir, page_num):
    """Extract figure bounding boxes from HTML output and crop from original image."""
    import cv2  # pyright: ignore[reportMissingImports]

    img = cv2.imread(image_path)
    if img is None:
        return html_output
    img_height, img_width = img.shape[:2]

    pattern = re.compile(
        r'<img\b[^>]*\bdata-bbox\s*=\s*"(\d+),(\d+),(\d+),(\d+)"[^>]*/?>',
        flags=re.IGNORECASE,
    )

    fig_count = 0

    def replace_img(match):
        nonlocal fig_count
        fig_count += 1
        x1, y1, x2, y2 = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
        )
        px1 = int(x1 / 1000 * img_width)
        py1 = int(y1 / 1000 * img_height)
        px2 = int(x2 / 1000 * img_width)
        py2 = int(y2 / 1000 * img_height)

        cropped = img[py1:py2, px1:px2]
        fig_name = f"page_{page_num:03d}_fig_{fig_count:02d}.png"
        fig_path = os.path.join(output_dir, fig_name)
        cv2.imwrite(fig_path, cropped)
        return f"![Figure {fig_count}](figures/{fig_name})"

    result = pattern.sub(replace_img, html_output)
    return result


def heading_to_slug(text):
    """Convert heading text to a URL-friendly slug."""
    slug = re.sub(r"<[^>]*>", "", text)
    slug = re.sub(r"\$[^$]*\$", "", slug)
    slug = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", slug)
    slug = slug.lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


def generate_toc(markdown_text):
    """Extract headings from markdown and generate a Table of Contents."""
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = heading_pattern.findall(markdown_text)

    if not headings:
        return ""

    toc_lines = ["# Table of Contents\n"]
    for hashes, title in headings:
        level = len(hashes)
        title_clean = title.strip()
        slug = heading_to_slug(title_clean)
        indent = "  " * (level - 1)
        toc_lines.append(f"{indent}- [{title_clean}](#{slug})")

    toc_lines.append("")
    return "\n".join(toc_lines)


def split_and_index(combined_md_path, output_dir, pages_per_file, pdf_basename):
    """Split a combined markdown file by page markers and generate an index."""
    import glob as _glob

    with open(combined_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by page markers
    page_pattern = re.compile(r"(<!-- Page (\d+) -->)")
    parts = page_pattern.split(content)

    # Extract TOC (everything before first page marker)
    toc_text = parts[0]

    # Build page dict
    pages = {}
    i = 1
    while i < len(parts):
        marker = parts[i]
        page_num = int(parts[i + 1])
        page_content = parts[i + 2] if i + 2 < len(parts) else ""
        pages[page_num] = marker + page_content
        i += 3

    if not pages:
        print("No page markers found, skipping split.")
        return

    total_pages = max(pages.keys())
    split_dir = os.path.join(output_dir, "split")
    os.makedirs(split_dir, exist_ok=True)

    # Generate split files
    filenames = []
    for start in range(1, total_pages + 1, pages_per_file):
        end = min(start + pages_per_file - 1, total_pages)
        fname = f"{pdf_basename}_pages_{start:03d}_{end:03d}.md"
        filenames.append((start, end, fname))

        fpath = os.path.join(split_dir, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(
                f"# {pdf_basename.replace('_', ' ')} - Pages {start}-{end}\n\n"
            )
            for p in range(start, end + 1):
                if p in pages:
                    # Fix image paths: split files are inside split/ dir,
                    # so split/figures/ -> figures/
                    page_content = pages[p].replace("](split/figures/", "](figures/")
                    f.write(page_content)
                    f.write("\n")
        print(f"  Split: {fname}")

    # Collect headings from split files for index
    split_files = sorted(
        _glob.glob(os.path.join(split_dir, f"{pdf_basename}_pages_*.md"))
    )
    toc_entries = []
    chapter_headings = []

    for fpath in split_files:
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^(#{1,3})\s+(.+)", line.strip())
                if m:
                    level = len(m.group(1))
                    title = m.group(2).strip()
                    if re.match(r".+ - Pages \d+", title):
                        continue
                    anchor = heading_to_slug(title)
                    toc_entries.append((level, title, fname, anchor))
                    if level <= 2:
                        chapter_headings.append((title, fname, anchor))

    # Write index file
    book_title = pdf_basename.replace("_", " ")
    index_path = os.path.join(split_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# {book_title}\n\n")

        f.write("## Chapters\n\n")
        for title, fname, anchor in chapter_headings:
            f.write(f"- [{title}]({fname}#{anchor})\n")

        f.write("\n---\n\n")

        f.write("## Detailed Table of Contents\n\n")
        for level, title, fname, anchor in toc_entries:
            indent = "  " * (level - 1)
            f.write(f"{indent}- [{title}]({fname}#{anchor})\n")

        f.write("\n---\n\n")

        f.write("## Browse by Page Range\n\n")
        f.write("| Page Range | Link |\n")
        f.write("|:---|:---|\n")
        for start, end, fname in filenames:
            f.write(f"| Pages {start}-{end} | [{fname}]({fname}) |\n")
        f.write("\n")

    print(f"  Index: {index_path}")
    print(
        f"  {len(filenames)} split files, {len(chapter_headings)} chapters, "
        f"{len(toc_entries)} headings"
    )


def normalize_openai_base_url(base_url):
    """Accept either http://host:port or http://host:port/v1."""
    base_url = base_url.rstrip("/")
    if base_url.endswith("/v1"):
        return base_url
    return base_url + "/v1"


def call_sglang_api(
    *,
    image_path,
    base_url,
    api_key,
    model,
    prompt,
    max_tokens,
    temperature,
    top_p,
    repetition_penalty,
    request_overrides,
):
    """Send one page image to the SGLang OpenAI-compatible API."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": _image_file_data_url(Path(image_path))},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "repetition_penalty": repetition_penalty,
    }
    if top_p is not None:
        payload["top_p"] = top_p
    payload.update(request_overrides)

    result = _request_json(
        base_url=base_url,
        path="/chat/completions",
        api_key=api_key,
        payload=payload,
    )

    message = ((result.get("choices") or [{}])[0].get("message") or {})
    content = message.get("content")
    if content is None:
        content = message.get("reasoning_content", "")
    if content is None:
        content = ""
    usage = result.get("usage", {})
    return content, usage

def postprocess_markdown(md_text):
    """Post-process markdown to fix common rendering issues."""
    # 1. Strip <div class="chart" ...> wrapper tags, keep inner content
    md_text = re.sub(
        r'<div\s+class=\"chart\"[^>]*>\s*',
        '',
        md_text,
        flags=re.IGNORECASE
    )
    # Remove corresponding closing </div>
    md_text = re.sub(r'\n*</div>\s*\n*', '\n\n', md_text, flags=re.IGNORECASE)

    # 2. Ensure blank line between HTML closing tags and markdown headings
    md_text = re.sub(
        r'(</(?:table|div|pre|blockquote|details|summary|section|article|aside|nav|header|footer|figure|figcaption)>)\s*\n(#{1,6}\s)',
        r'\1\n\n\2',
        md_text,
        flags=re.IGNORECASE
    )

    # 3. Ensure blank line after </table> before any content
    md_text = re.sub(
        r'(</table>)\s*\n([^\n])',
        r'\1\n\n\2',
        md_text,
        flags=re.IGNORECASE
    )

    return md_text


def process_page(
    page_num,
    total_pages,
    img_path,
    raw_dir,
    figures_dir,
    output_dir,
    request_config,
    qwenvl_cast_html_tag,
):
    """Process a single page: call API, extract figures, convert to markdown."""
    md_path = os.path.join(raw_dir, f"page_{page_num:03d}.md")

    # Skip if already processed
    if os.path.exists(md_path):
        print(f"Page {page_num}/{total_pages} already processed, skipping.")
        return page_num, True

    print(f"Processing page {page_num}/{total_pages}...")
    t0 = time.time()

    try:
        raw_html, usage = call_sglang_api(image_path=img_path, **request_config)
    except Exception as e:
        print(f"  ERROR on page {page_num}: {e}")
        return page_num, False

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    elapsed = time.time() - t0
    print(
        f"  Page {page_num}: prompt={prompt_tokens}, completion={completion_tokens}, "
        f"took {elapsed:.1f}s"
    )

    # Save raw HTML output
    with open(os.path.join(raw_dir, f"page_{page_num:03d}_raw.html"), "w") as f:
        f.write(raw_html)

    # Extract figures from high-res source images if available
    hi_res_dir = os.path.join(output_dir, "page_images_hires")
    fig_img_path = img_path
    if os.path.isdir(hi_res_dir):
        hi_res_img = os.path.join(hi_res_dir, f"page_{page_num:03d}.png")
        if os.path.exists(hi_res_img):
            fig_img_path = hi_res_img

    html_with_figs = extract_and_save_figures(
        raw_html, fig_img_path, figures_dir, page_num
    )

    # Convert to markdown
    markdown = qwenvl_cast_html_tag(html_with_figs)
    markdown = postprocess_markdown(markdown)

    with open(md_path, "w") as f:
        f.write(markdown)

    return page_num, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf_path", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument(
        "--base_url",
        "--api_url",
        dest="base_url",
        type=str,
        default=os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:30000/v1"),
        help="OpenAI-compatible SGLang base URL. Accepts either ...:port or ...:port/v1.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("SGLANG_MODEL"),
        help="Model id exposed by /v1/models. If omitted, auto-detect the first served model.",
    )
    parser.add_argument(
        "--model_path",
        type=Path,
        default=Path(os.environ.get("MODEL_PATH", str(DEFAULT_MODEL_PATH))),
        help="Weight dir for reading generation_config and matching inference_v2 decode behavior.",
    )
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--prompt", type=str, default="QwenVL HTML")
    parser.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top_p", type=float, default=DEFAULT_TOP_P)
    parser.add_argument(
        "--decode_mode",
        choices=("hf-equivalent", "sampling"),
        default=os.environ.get("SGLANG_DECODE_MODE", "hf-equivalent"),
        help=(
            "hf-equivalent: match inference_v2.py effective decode behavior. "
            "sampling: send temperature/top_p literally to SGLang."
        ),
    )
    parser.add_argument(
        "--repetition_penalty",
        type=float,
        default=DEFAULT_REPETITION_PENALTY,
        help="Match inference_v2 model.generate repetition_penalty (default 1.05).",
    )
    parser.add_argument(
        "--start_page", type=int, default=1, help="Start from this page (1-indexed)"
    )
    parser.add_argument(
        "--end_page",
        type=int,
        default=-1,
        help="End at this page (1-indexed, -1 for all)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=16,
        help="Number of concurrent API requests",
    )
    parser.add_argument(
        "--combine_only",
        action="store_true",
        help="Skip inference, only re-combine existing raw output",
    )
    parser.add_argument(
        "--split_pages",
        type=int,
        default=10,
        help="Split output into files of N pages each and generate index (0=disabled)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    images_dir = os.path.join(args.output_dir, "page_images")
    split_dir = os.path.join(args.output_dir, "split")
    figures_dir = os.path.join(split_dir, "figures")
    raw_dir = os.path.join(args.output_dir, "raw_output")
    os.makedirs(split_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)

    pdf_basename = os.path.splitext(os.path.basename(args.pdf_path))[0]
    output_file = os.path.join(args.output_dir, f"{pdf_basename}.md")

    # Import the HTML to markdown converter
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from inference_v2 import qwenvl_cast_html_tag

    if not args.combine_only:
        base_url = normalize_openai_base_url(args.base_url)
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

        request_config = {
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "prompt": args.prompt,
            "max_tokens": args.max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "repetition_penalty": args.repetition_penalty,
            "request_overrides": request_overrides,
        }

        # Step 1: Convert PDF to images
        print("=" * 60)
        print(f"Step 1: Converting PDF to images (DPI={args.dpi})...")
        print("=" * 60)
        image_paths = pdf_to_images(args.pdf_path, images_dir, args.dpi)
        total_pages = len(image_paths)
        print(f"Total pages: {total_pages}")

        # Step 2: Verify API is available
        print("=" * 60)
        print(f"Step 2: Verifying SGLang API at {base_url}...")
        print("=" * 60)
        try:
            models = _request_json(
                base_url=base_url,
                path="/models",
                api_key=api_key,
                timeout=10.0,
            )
            print(f"API OK. Models: {[m['id'] for m in models['data']]}")
        except Exception as e:
            print(f"ERROR: Cannot reach SGLang API at {base_url}: {e}")
            sys.exit(1)

        # Step 3: Run inference (concurrent)
        print("=" * 60)
        print(
            f"Step 3: Running inference (concurrency={args.concurrency})..."
        )
        print("=" * 60)

        start_idx = args.start_page - 1
        end_idx = (
            total_pages if args.end_page == -1 else min(args.end_page, total_pages)
        )

        t_start = time.time()
        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            futures = {}
            for i in range(start_idx, end_idx):
                img_path = image_paths[i]
                page_num = i + 1
                future = executor.submit(
                    process_page,
                    page_num,
                    total_pages,
                    img_path,
                    raw_dir,
                    figures_dir,
                    args.output_dir,
                    request_config,
                    qwenvl_cast_html_tag,
                )
                futures[future] = page_num

            for future in as_completed(futures):
                page_num, ok = future.result()
                if ok:
                    success_count += 1
                else:
                    fail_count += 1

        t_total = time.time() - t_start
        print(
            f"\nInference done: {success_count} succeeded, {fail_count} failed, "
            f"total {t_total:.1f}s"
        )
    else:
        total_pages = len([f for f in os.listdir(raw_dir) if f.endswith(".md")])
        print(f"Combine-only mode: found {total_pages} processed pages")

    # Step 4: Combine all pages with TOC
    print("=" * 60)
    print("Step 4: Combining results with Table of Contents...")
    print("=" * 60)

    all_markdown = []
    for i in range(total_pages):
        page_num = i + 1
        md_path = os.path.join(raw_dir, f"page_{page_num:03d}.md")
        if os.path.exists(md_path):
            with open(md_path, "r") as f:
                content = f.read()
            # Rewrite figure paths: figures/ -> split/figures/ for combined md
            content = content.replace("](figures/", "](split/figures/")
            content = postprocess_markdown(content)
            all_markdown.append(f"<!-- Page {page_num} -->\n\n{content}")
        else:
            all_markdown.append(f"<!-- Page {page_num} - NOT PROCESSED -->\n")

    body_md = "\n\n---\n\n".join(all_markdown)

    toc = generate_toc(body_md)

    if toc:
        final_md = toc + "\n---\n\n" + body_md
    else:
        final_md = body_md

    with open(output_file, "w") as f:
        f.write(final_md)

    heading_count = len(re.findall(r"^#{1,6}\s+", body_md, re.MULTILINE))
    print(f"Generated TOC with {heading_count} headings")
    print(f"Done! Output saved to {output_file}")
    print(f"Figures saved to {figures_dir}")

    # Step 5: Split into per-page-range files and generate index
    if args.split_pages > 0:
        print("=" * 60)
        print(f"Step 5: Splitting into {args.split_pages}-page files with index...")
        print("=" * 60)
        split_and_index(output_file, args.output_dir, args.split_pages, pdf_basename)


if __name__ == "__main__":
    main()
