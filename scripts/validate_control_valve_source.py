#!/usr/bin/env python3

from control_valve_validation import CREATIVE, fail, read_json


audit = read_json(CREATIVE / "source-audit.json")
report = read_json(CREATIVE / "conversion-report.json")
retention = read_json(CREATIVE / "shot-retention-matrix.json")

source = audit.get("source", {})
structure = audit.get("structuralInspection", {})
if source.get("sha256") != "378EFDBB1291612D1BA09A6A6C3533636AB372BFE16099F0DAC9CE39D4DB06B9":
    fail("supplied STEP hash is not traceable")
if source.get("bytes") != 18730985:
    fail("supplied STEP byte size changed")
if structure.get("productDefinitions") != 45:
    fail("STEP product-definition count must remain evidenced")
if structure.get("assemblyOccurrences") != 124:
    fail("STEP assembly occurrence count must remain evidenced")
if structure.get("classification") != "structured-named-parts":
    fail("model classification must be structured-named-parts")
if report.get("source", {}).get("sha256") != source.get("sha256"):
    fail("conversion report is not bound to the audited STEP")

decisions = retention.get("decisions", [])
if len(decisions) != 6:
    fail("retention matrix must define exactly six semantic groups")
if {item.get("group") for item in decisions} != {
    "VALVE_BODY_BONNET",
    "PNEUMATIC_ACTUATOR",
    "STEM_CASCADE_PLUG",
    "CASCADE_TRIM",
    "SEALS_SUPPORT",
    "PRODUCTION_DETAILS",
}:
    fail("retention matrix group identities are incomplete")
if any(not item.get("shots") or not item.get("decision") for item in decisions):
    fail("each retained group needs shots and a geometry decision")

print(
    "PASS: the real DN80 CL2500 STEP, conversion path and six-group "
    "shot-retention decisions are traceable"
)
