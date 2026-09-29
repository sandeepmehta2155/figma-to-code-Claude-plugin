#!/usr/bin/env python3
"""Split an LLM Export (figma-llm-export) payload into readable JSON + image files.

Usage: python3 split_payload.py <payload.json> <out_dir>
Writes <out_dir>/payload.json (images replaced by file paths) and one .png/.svg per crop.
"""
import base64, json, os, re, sys

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
with open(src) as f:
    payload = json.load(f)

for img in payload.get("images", []):
    name = re.sub(r"[^\w.-]+", "_", f"{img.get('name', 'node')}_{img.get('id', '')}").strip("_")
    if "base64" in img:
        path = os.path.join(out, name + ".png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(img.pop("base64")))
    elif "svg" in img:
        path = os.path.join(out, name + ".svg")
        with open(path, "w") as f:
            f.write(img.pop("svg"))
    else:
        continue  # "Download JSON" export: image metadata only, no data
    img["file"] = path

with open(os.path.join(out, "payload.json"), "w") as f:
    json.dump(payload, f, indent=1)
print(f"{len(payload.get('nodes', []))} node(s), {len(payload.get('images', []))} image(s) -> {out}")
