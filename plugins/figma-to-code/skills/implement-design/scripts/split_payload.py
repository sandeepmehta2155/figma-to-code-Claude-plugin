#!/usr/bin/env python3
"""Split an LLM Export (figma-llm-export) payload into readable JSON + image files.

Usage: python3 split_payload.py <payload.json> <out_dir>
       python3 split_payload.py self-test
Writes <out_dir>/payload.json (images replaced by file paths), one .png/.svg per crop, and
<out_dir>/variables.json (variables with names and every mode). Prints the visible image and vector
layers that have no usable file, and the visible component instances.
"""
import base64, json, os, re, shutil, sys, tempfile

# LLM Export crops every element of 24px or more together with its children, depth-first, and
# stops at 80 crops without saying so in the bundle.
MAX_EXPORTS = 80
SHAPES = {"VECTOR", "BOOLEAN_OPERATION", "STAR", "POLYGON", "LINE", "ELLIPSE"}


def split(src, out):
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
    with open(os.path.join(out, "variables.json"), "w") as f:
        json.dump(variables(payload), f, indent=1)
    images = payload.get("images", [])
    print(f"{len(payload.get('nodes', []))} node(s), {len(images)} image(s) -> {out}")
    nodata = sum("file" not in img for img in images)
    if nodata:  # every "Download LLM bundle" entry has base64 or svg
        print(f'{nodata} of {len(images)} image(s) have no data: a "Download JSON" export. Re-export with "Download LLM bundle".')
    missing = missing_assets(payload)
    if missing:
        print(f"{len(missing)} visible image or vector layer(s) have no usable file:")
        for n in missing:
            print(f"  {n['id']} {n.get('name')} {size(n)}: {why(n, images)}")
    found = instances(payload)
    if found:
        print(f"{sum(map(len, found.values()))} visible component instance(s):")
        for key, sizes in sorted(found.items(), key=lambda kv: -len(kv[1])):
            print(f"  {len(sizes)}x {key} ({', '.join(sorted(set(sizes)))})")
    return missing


def num(v):
    return v.get("value") if isinstance(v, dict) else v  # sizes bound to a variable are {"value", "variable"}


def size(n):
    return f"{num(n.get('width'))}x{num(n.get('height'))}"


def kids(n):
    return [c for c in n.get("children") or [] if c.get("visible") is not False]


def visible_nodes(nodes):
    for n in nodes:
        if n.get("visible") is not False:
            yield n
            yield from visible_nodes(n.get("children") or [])


def big(n):  # LLM Export's default minimum crop size
    return min(num(n.get("width")) or 0, num(n.get("height")) or 0) >= 24


def vector_only(n):  # drawn only with vector shapes, which the bundle carries no path data for;
    k = kids(n)      # an auto-layout row of parts that are each big enough to list is layout, not one drawing
    return n.get("type") in SHAPES or (n.get("type") in ("GROUP", "FRAME", "COMPONENT") and bool(k)
                                        and all(map(vector_only, k)) and not (n.get("layout") and all(map(big, k))))


def missing_assets(payload):
    """Visible layers the build needs as a file but has no usable one for: image fills (photos, logos)
    with no crop or with their children baked into it, and vector logos/icons of 24px or more."""
    have = {img.get("id") for img in payload.get("images", []) if "file" in img}
    out = []

    def walk(nodes):
        for n in nodes:
            if n.get("visible") is False:
                continue
            image = any(isinstance(f, dict) and f.get("type") == "IMAGE" and f.get("visible") is not False for f in n.get("fills") or [])
            vector = vector_only(n)
            if image and (n.get("id") not in have or kids(n)) or (
                    vector and big(n) and n.get("type") not in ("ELLIPSE", "LINE") and n.get("id") not in have):
                out.append(n)
            if not vector:
                walk(n.get("children") or [])

    walk(payload.get("nodes", []))
    return out


def why(node, images):
    entry = next((img for img in images if img.get("id") == node.get("id")), None)
    if entry and "file" in entry:
        return f"its crop has its {len(kids(node))} child layer(s) baked in: hide them in your copy of the file, then export it"
    if entry:
        return 'exported without data ("Download JSON")'
    if not big(node):
        return "under LLM Export's minimum crop size (24px by default)"
    return f"cut off by LLM Export's {MAX_EXPORTS}-image limit" if len(images) >= MAX_EXPORTS else "not exported"


def instances(payload):
    """Visible component instances by key, with their sizes; instances under hidden layers are left out."""
    found = {}
    for n in visible_nodes(payload.get("nodes", [])):
        if n.get("mainComponent"):
            found.setdefault(n["mainComponent"], []).append(size(n))
    return found


def hex_color(c):
    h = "#" + "".join(f"{int(c[k] * 255 + 0.5):02x}" for k in "rgb")  # rounds like LLM Export's Math.round
    return h + f"{int(c['a'] * 255 + 0.5):02x}" if c.get("a", 1) < 1 else h


def variables(payload):
    """Collections ticked in LLM Export hold the whole theme in every mode; without them, only the
    variables the selection uses. Same shape either way: values by mode name, colors as hex,
    aliases as {"alias": "Collection/name"}. Used variables in no ticked collection (a library, an
    unticked collection, or deleted ones still bound) are added with "usedOnly": true."""
    cols = payload.get("variableCollections")
    if not cols:
        return {"source": "selection", "variables": payload.get("variables", [])}
    used = {u.get("id"): u for u in payload.get("variables", [])}
    names = {v["id"]: f"{c['name']}/{v['name']}" for c in cols for v in c["variables"]}

    def value(raw, resolved):
        if isinstance(raw, dict) and raw.get("type") == "VARIABLE_ALIAS":
            target = raw.get("id")
            if target in names:
                return {"alias": names[target]}
            if target in used:
                return {"alias": f"{used[target]['collection']}/{used[target]['name']}"}
            return {"alias": resolved.get("aliasName"), "value": value(resolved.get("resolvedValue"), {})}
        return hex_color(raw) if isinstance(raw, dict) and "r" in raw else raw

    ticked = [
        {"name": v["name"], "collection": c["name"], "type": v.get("type"), "scopes": v.get("scopes"),
         "codeSyntax": v.get("codeSyntax"), "description": v.get("description"),
         "valuesByMode": {c["modes"].get(m, m): value(raw, (v.get("resolvedValuesByMode") or {}).get(m) or {})
                          for m, raw in v.get("valuesByMode", {}).items()}}
        for c in cols for v in c["variables"]]
    return {"source": "collections", "variables": ticked + [dict(u, usedOnly=True) for i, u in used.items() if i not in names]}


def self_test():
    out = tempfile.mkdtemp()
    src = os.path.join(out, "bundle.json")
    png = base64.b64encode(b"png").decode()
    cyan = {"r": 0.0235294122248888, "g": 0.7137255072593689, "b": 0.8313725590705872, "a": 1}
    image = [{"type": "IMAGE", "visible": True}]
    vec = {"type": "VECTOR", "width": 20, "height": 20}
    bundle = {
        "source": "figma",
        "nodes": [{"id": "1:1", "name": "Home", "type": "FRAME", "width": 100, "height": 50, "children": [
            {"id": "1:2", "name": "hero", "width": 80, "height": 40, "fills": image, "children": [{"id": "1:7", "name": "title"}]},
            {"id": "1:3", "name": "logo", "width": {"value": 30, "variable": "S/logo"}, "height": 30, "fills": image},
            {"id": "1:4", "name": "off", "width": 9, "height": 9, "fills": [{"type": "IMAGE", "visible": False}]},
            {"id": "1:5", "name": "hidden", "visible": False, "fills": image, "children": [{"id": "1:6", "fills": image}]},
            {"id": "1:8", "name": "wordmark", "type": "GROUP", "width": 60, "height": 24, "children": [dict(vec, id="1:9"), dict(vec, id="1:10")]},
            {"id": "1:11", "name": "dot", "type": "ELLIPSE", "width": 30, "height": 30},
            {"id": "1:12", "name": "Button", "type": "INSTANCE", "mainComponent": "Button / Size=md", "width": 80, "height": 32},
            {"id": "1:13", "name": "old", "visible": False, "children": [{"id": "1:14", "mainComponent": "Old"}]},
            {"id": "1:15", "name": "social", "type": "FRAME", "layout": {"mode": "HORIZONTAL"}, "width": 72, "height": 32, "children": [
                {"id": "1:16", "type": "GROUP", "width": 32, "height": 32, "children": [dict(vec, id="1:17")]},
                {"id": "1:18", "type": "GROUP", "width": 32, "height": 32, "children": [dict(vec, id="1:19")]}]},
            {"id": "1:20", "name": "lockup", "type": "FRAME", "layout": {"mode": "HORIZONTAL"}, "width": 90, "height": 30, "children": [
                dict(vec, id="1:21", width=30, height=30), dict(vec, id="1:22", width=50, height=12)]}]}],
        "images": [{"id": "1:1", "name": "Home", "base64": png}, {"id": "1:2", "name": "hero", "base64": png}, {"id": "1:3", "name": "logo"}],
        "variables": [{"id": "lib1", "name": "gray/900", "type": "COLOR", "collection": "Lib", "valuesByMode": {"Default": "#111827"}}],
        "variableCollections": [{"name": "DS", "modes": {"m1": "Light", "m2": "Dark"}, "variables": [
            {"id": "v1", "name": "brand/cyan", "type": "COLOR", "scopes": ["ALL_SCOPES"], "codeSyntax": {},
             "description": "", "valuesByMode": {"m1": cyan, "m2": {**cyan, "a": 0.5}}},
            {"id": "v2", "name": "text/link", "type": "COLOR",
             "valuesByMode": {"m1": {"type": "VARIABLE_ALIAS", "id": "v1"}, "m2": {"type": "VARIABLE_ALIAS", "id": "x9"}},
             "resolvedValuesByMode": {"m2": {"resolvedValue": cyan, "alias": "x9", "aliasName": "other/blue"}}},
            {"id": "v3", "name": "text/body", "type": "COLOR", "valuesByMode": {"m1": {"type": "VARIABLE_ALIAS", "id": "lib1"}}}]}],
    }
    with open(src, "w") as f:
        json.dump(bundle, f)
    missing = split(src, out)
    assert [n["id"] for n in missing] == ["1:2", "1:3", "1:8", "1:16", "1:18", "1:20"], [n["id"] for n in missing]
    with open(os.path.join(out, "payload.json")) as f:
        images = json.load(f)["images"]
    assert [why(n, images).split()[0] for n in missing][:3] == ["its", "exported", "not"], [why(n, images) for n in missing]
    assert why({"width": 18, "height": 30}, [{}] * 80).startswith("under") and why({"width": 900, "height": 400}, [{}] * 80).startswith("cut off")
    assert instances(bundle) == {"Button / Size=md": ["80x32"]}
    with open(os.path.join(out, "variables.json")) as f:
        v = json.load(f)
    assert v["source"] == "collections", v
    brand, link, body, lib = v["variables"]
    assert brand["valuesByMode"] == {"Light": "#06b6d4", "Dark": "#06b6d480"}, brand
    assert link["valuesByMode"] == {"Light": {"alias": "DS/brand/cyan"}, "Dark": {"alias": "other/blue", "value": "#06b6d4"}}, link
    assert body["valuesByMode"] == {"Light": {"alias": "Lib/gray/900"}} and lib["usedOnly"] is True, (body, lib)
    assert variables({"variables": ["x"]}) == {"source": "selection", "variables": ["x"]}
    shutil.rmtree(out)
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["self-test"]:
        self_test()
    elif len(sys.argv) == 3:
        split(sys.argv[1], sys.argv[2])
    else:
        sys.exit(__doc__)
