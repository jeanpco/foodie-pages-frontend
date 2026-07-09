#!/usr/bin/env python3
"""Build a self-contained before/after QA report HTML for the qa-report skill.

Takes an HTML template containing `__IMG_<key>__` tokens and a manifest mapping
each key to a source image anywhere on disk. For every token it opens the source,
downscales it (long edge -> --max), re-encodes JPEG (--quality), base64-inlines it
as a data: URI, and substitutes the token. The result is a single .html file with
zero external requests — safe for the Artifact CSP (which blocks all remote hosts).

Why inline: an Artifact is published to claude.ai with a strict CSP; remote images,
CDNs and fonts are blocked, so every asset must be embedded.

Usage (from anywhere; paths may be absolute or relative):
    python3 build-report.py \
        --template report.template.html \
        --manifest  images.json \
        --out       report.html \
        [--max 900] [--quality 72]

  images.json = {"b1-before": "/abs/path/before.jpeg", "b1-after": "...", ...}
    - keys must match the __IMG_<key>__ tokens in the template
    - values are any readable image path (png/jpg/webp/...); they are NOT mutated

Requires Pillow (`python3 -c "import PIL"`). Prints a report: keys used, any
missing manifest entries, any leftover tokens, and the final file size. Exits
non-zero — WITHOUT writing the output — if any token has no manifest entry, a
source file is unreadable, or a `__IMG_<key>__` token remains unresolved, so a
broken report never ships silently.
"""
import argparse, base64, io, json, os, re, sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install Pillow (or use the repo's python env).")

TOKEN = re.compile(r"__IMG_([A-Za-z0-9_\-]+)__")


def encode(src_path: str, max_edge: int, quality: int) -> str:
    """Downscale + JPEG-encode a source image -> base64 data URI string."""
    im = Image.open(src_path)
    # Flatten alpha onto white so PNGs with transparency don't turn black as JPEG.
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")  # normalize LA / palette-with-alpha to RGBA first
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])  # composite over white using the alpha channel
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((max_edge, max_edge), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--manifest", required=True, help="JSON {token_key: image_path}")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=900, help="max long edge px (default 900)")
    ap.add_argument("--quality", type=int, default=72, help="JPEG quality (default 72)")
    args = ap.parse_args()

    tpl = open(args.template, encoding="utf-8").read()
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    keys = sorted(set(TOKEN.findall(tpl)))

    missing, unreadable = [], []
    for k in keys:
        src = manifest.get(k)
        if not src:
            missing.append(k)
            continue
        if not os.path.exists(src):
            unreadable.append(f"{k} -> {src}")
            continue
        try:
            tpl = tpl.replace(f"__IMG_{k}__", encode(src, args.max, args.quality))
        except Exception as e:  # noqa: BLE001 - surface any decode/encode failure
            unreadable.append(f"{k} -> {src} ({e})")

    leftover = TOKEN.findall(tpl)
    unused = [k for k in manifest if k not in keys]

    print(f"tokens in template : {len(keys)}")
    print(f"missing manifest   : {missing or 'none'}")
    print(f"unreadable sources : {unreadable or 'none'}")
    print(f"leftover tokens    : {sorted(set(leftover)) or 'none'}")
    if unused:
        print(f"manifest keys unused: {unused}")

    if missing or unreadable or leftover:
        sys.exit("REFUSING to write: unresolved images above. Fix the manifest/template.")

    open(args.out, "w", encoding="utf-8").write(tpl)
    print(f"wrote {args.out} ({os.path.getsize(args.out)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
