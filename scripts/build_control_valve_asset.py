#!/usr/bin/env python3
"""Convert the supplied STEP assembly into an exactly six-group shot GLB.

This is a build tool, not an acceptance dependency. It requires CadQuery/OCP
in the invoking environment. Acceptance validates the generated GLB directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path


GROUPS = (
    "VALVE_BODY_BONNET",
    "PNEUMATIC_ACTUATOR",
    "STEM_CASCADE_PLUG",
    "CASCADE_TRIM",
    "SEALS_SUPPORT",
    "PRODUCTION_DETAILS",
)

GROUP_COLORS = {
    "VALVE_BODY_BONNET": (0.22, 0.24, 0.27, 1.0),
    "PNEUMATIC_ACTUATOR": (0.36, 0.39, 0.43, 1.0),
    "STEM_CASCADE_PLUG": (0.86, 0.30, 0.12, 1.0),
    "CASCADE_TRIM": (0.83, 0.60, 0.18, 1.0),
    "SEALS_SUPPORT": (0.12, 0.48, 0.52, 1.0),
    "PRODUCTION_DETAILS": (0.52, 0.55, 0.59, 1.0),
}


def classify(name: str) -> str:
    lowered = name.casefold()
    if any(token in lowered for token in ("阀笼", "阀座")):
        return "CASCADE_TRIM"
    if any(token in lowered for token in ("串级式阀芯", "气缸推杆", "导向套", "哈夫板")):
        return "STEM_CASCADE_PLUG"
    if any(
        token in lowered
        for token in (
            "密封",
            "支撑环",
            "挡圈",
            "卡套角接头",
            "tlxcd",
            "tlyb",
            "tlyt",
            "tlφ",
        )
    ):
        return "SEALS_SUPPORT"
    if any(token in lowered for token in ("壳体", "上盖")):
        return "VALVE_BODY_BONNET"
    if any(
        token in lowered
        for token in (
            "气缸",
            "行程牌",
            "支架",
            "活塞",
        )
    ):
        return "PNEUMATIC_ACTUATOR"
    return "PRODUCTION_DETAILS"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_step_assembly(cq, path: Path):
    """Load an AP214 assembly through OCP's XCAF document model.

    CadQuery 2.5 exposes the assembly and GLB exporters but leaves
    ``Assembly.load`` unimplemented. The XCAF reader below is the small,
    name/location-preserving subset used by newer CadQuery releases.
    """

    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Interface import Interface_Static
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    def label_name(label: TDF_Label) -> str:
        attribute = TDataStd_Name()
        if label.IsAttribute(TDataStd_Name.GetID_s()):
            label.FindAttribute(TDataStd_Name.GetID_s(), attribute)
            return str(attribute.Get().ToExtString())
        return ""

    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    reader.SetLayerMode(True)
    reader.SetSHUOMode(True)
    Interface_Static.SetIVal_s("read.stepcaf.subshapes.name", 1)
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise ValueError(f"OpenCascade could not read STEP source: {path}")

    document = TDocStd_Document(TCollection_ExtendedString("ControlValveXCAF"))
    if not reader.Transfer(document):
        raise ValueError("OpenCascade could not transfer STEP assembly to XCAF")
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())

    def unique_name(parent, proposed: str) -> str:
        base = proposed.strip() or "UNNAMED_COMPONENT"
        candidate = base
        serial = 2
        while candidate in parent.objects:
            candidate = f"{base}__{serial}"
            serial += 1
        return candidate

    def process(label: TDF_Label, parent):
        components = TDF_LabelSequence()
        shape_tool.GetComponents_s(label, components)
        for index in range(1, components.Length() + 1):
            component = components.Value(index)
            component_name = label_name(component)
            location = shape_tool.GetLocation_s(component)
            cq_location = cq.Location(location) if location else cq.Location()
            if not shape_tool.IsReference_s(component):
                continue
            reference = TDF_Label()
            shape_tool.GetReferredShape_s(component, reference)
            reference_name = label_name(reference)
            semantic_name = (
                f"{reference_name}::{component_name}"
                if reference_name and component_name
                else reference_name or component_name
            )
            if shape_tool.IsAssembly_s(reference):
                name = unique_name(
                    parent,
                    semantic_name or "SUBASSEMBLY",
                )
                child = cq.Assembly(name=name)
                process(reference, child)
                parent.add(child, loc=cq_location, name=name)
            elif shape_tool.IsSimpleShape_s(reference):
                name = unique_name(
                    parent,
                    semantic_name or "PART",
                )
                shape = cq.Shape.cast(shape_tool.GetShape_s(reference))
                parent.add(shape, loc=cq_location, name=name)

    labels = TDF_LabelSequence()
    shape_tool.GetFreeShapes(labels)
    if labels.Length() < 1:
        raise ValueError("STEP contains no free assembly shapes")
    top = labels.Value(1)
    if shape_tool.IsReference_s(top):
        reference = TDF_Label()
        shape_tool.GetReferredShape_s(top, reference)
        top = reference
    if not shape_tool.IsAssembly_s(top):
        raise ValueError("STEP top-level shape is not an assembly")
    root = cq.Assembly(name=label_name(top) or "CONTROL_VALVE_SOURCE")
    process(top, root)
    return root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--linear-tolerance", type=float, default=0.35)
    parser.add_argument("--angular-tolerance", type=float, default=0.20)
    args = parser.parse_args()

    try:
        import cadquery as cq
    except ImportError as exc:
        print(
            "CadQuery is required for this build step. Install it outside the "
            "repository and expose it through PYTHONPATH.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    step = args.step.resolve()
    if not step.is_file():
        raise SystemExit(f"STEP source does not exist: {step}")

    assembly = load_step_assembly(cq, step)
    grouped_shapes: dict[str, list] = defaultdict(list)
    members: dict[str, list[str]] = defaultdict(list)
    source_instances = 0

    # CadQuery's assembly iterator returns the accumulated world location for
    # each shape-bearing leaf. Bake that location into each retained shape so
    # the six exported group nodes can start at identity transforms.
    for shape, path_name, world_location, _source_color in assembly:
        source_instances += 1
        group = classify(path_name)
        placed = shape.located(world_location)
        grouped_shapes[group].append(placed)
        members[group].append(path_name)

    missing = [group for group in GROUPS if not grouped_shapes[group]]
    if missing:
        raise SystemExit(f"semantic groups have no geometry: {missing}")

    output = cq.Assembly(name="DN80_CL2500_CONTROL_VALVE_SHOT_ASSET")
    group_stats = []
    for group in GROUPS:
        compound = cq.Compound.makeCompound(grouped_shapes[group])
        color = cq.Color(*GROUP_COLORS[group])
        output.add(compound, name=group, color=color)
        bounds = compound.BoundingBox()
        group_stats.append(
            {
                "name": group,
                "sourceInstanceCount": len(grouped_shapes[group]),
                "sourcePaths": sorted(members[group]),
                "boundsMm": {
                    "min": [bounds.xmin, bounds.ymin, bounds.zmin],
                    "max": [bounds.xmax, bounds.ymax, bounds.zmax],
                    "size": [bounds.xlen, bounds.ylen, bounds.zlen],
                },
                "solidCount": len(compound.Solids()),
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.export(
        str(args.out),
        exportType="GLB",
        tolerance=args.linear_tolerance,
        angularTolerance=args.angular_tolerance,
    )

    report = {
        "schemaVersion": 1,
        "source": {
            "path": step.as_posix(),
            "bytes": step.stat().st_size,
            "sha256": sha256(step),
            "format": "STEP AP214",
        },
        "conversion": {
            "engine": f"CadQuery {cq.__version__} / OpenCascade",
            "linearToleranceMm": args.linear_tolerance,
            "angularToleranceRadians": args.angular_tolerance,
            "sourceShapeInstances": source_instances,
            "semanticGroupCount": len(GROUPS),
        },
        "groups": group_stats,
        "output": {
            "path": args.out.as_posix(),
            "bytes": args.out.stat().st_size,
            "sha256": sha256(args.out),
        },
        "truthBoundary": {
            "purpose": "Commercial camera asset with six bounded animation groups",
            "notADigitalTwin": True,
            "notCFD": True,
            "notMaintenanceOrder": True,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["output"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
