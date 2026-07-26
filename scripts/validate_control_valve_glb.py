#!/usr/bin/env python3

from control_valve_validation import (
    ASSET,
    CREATIVE,
    EXPECTED_GROUPS,
    controlled_ancestor,
    fail,
    node_parent_map,
    read_glb_json,
    read_json,
    sha256,
)


document = read_glb_json()
report = read_json(CREATIVE / "conversion-report.json")
nodes = document.get("nodes", [])
names = [node.get("name") for node in nodes]
for group in EXPECTED_GROUPS:
    if names.count(group) != 1:
        fail(f"semantic control node {group} must occur exactly once")

parents = node_parent_map(document)
uncontrolled_meshes = [
    names[index] or f"node-{index}"
    for index, node in enumerate(nodes)
    if "mesh" in node
    and controlled_ancestor(document, index, parents) not in EXPECTED_GROUPS
]
if uncontrolled_meshes:
    fail(f"mesh nodes escape the six semantic controls: {uncontrolled_meshes[:8]}")
if document.get("animations"):
    fail("shot GLB must not contain baked animation")
if document.get("skins"):
    fail("shot GLB must not contain skins")
if ASSET.stat().st_size >= 12 * 1024 * 1024:
    fail(f"GLB exceeds the 12 MiB shot-asset ceiling: {ASSET.stat().st_size}")
if report.get("output", {}).get("bytes") != ASSET.stat().st_size:
    fail("conversion report byte size does not match GLB")
if report.get("output", {}).get("sha256") != sha256(ASSET):
    fail("conversion report hash does not match GLB")
if report.get("conversion", {}).get("semanticGroupCount") != 6:
    fail("conversion must report exactly six semantic groups")

triangles = 0
accessors = document.get("accessors", [])
for mesh in document.get("meshes", []):
    for primitive in mesh.get("primitives", []):
        if primitive.get("mode", 4) != 4:
            continue
        if "indices" in primitive:
            triangles += accessors[primitive["indices"]].get("count", 0) // 3
        else:
            position = primitive.get("attributes", {}).get("POSITION")
            if position is not None:
                triangles += accessors[position].get("count", 0) // 3
if triangles <= 0:
    fail("GLB exposes no triangle geometry")

print(
    f"PASS: GLB is controlled by exactly six semantic nodes, "
    f"{triangles} triangles, {ASSET.stat().st_size} bytes"
)
