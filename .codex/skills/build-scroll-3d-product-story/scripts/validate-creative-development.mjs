#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { fail, parseArgs } from "./lib/cli.mjs";

const PHASES = [
  "case-research",
  "creative-routes",
  "five-shot-script",
  "animatic",
  "automatic-release",
];
const CAPABILITIES = new Set([
  "structured-named-parts",
  "separated-unnamed-parts",
  "partially-merged",
  "fused-single-mesh",
]);
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/u;

function nonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function nonEmptyStrings(value) {
  return Array.isArray(value) && value.length > 0 && value.every(nonEmptyString);
}

function validDate(value) {
  return nonEmptyString(value) && Number.isFinite(Date.parse(value));
}

function validRange(value) {
  return (
    Array.isArray(value) &&
    value.length === 2 &&
    value.every(Number.isFinite) &&
    value[0] >= 0 &&
    value[1] <= 1 &&
    value[0] < value[1]
  );
}

function requireStringFields(value, fields, prefix, errors) {
  for (const field of fields) {
    if (!nonEmptyString(value?.[field])) {
      errors.push(`${prefix}.${field} must be a non-empty string`);
    }
  }
}

export function validateCreativeDevelopment(
  plan,
  { through = "release" } = {},
) {
  const errors = [];
  if (!["animatic", "release"].includes(through)) {
    return ["through must be animatic or release"];
  }
  if (!plan || typeof plan !== "object" || Array.isArray(plan)) {
    return ["creative development must be a JSON object"];
  }
  if (plan.schemaVersion !== 1) {
    errors.push("schemaVersion must equal 1");
  }
  if (!SLUG.test(plan.planId ?? "")) {
    errors.push("planId must be a lowercase kebab-case identifier");
  }

  const audit = plan.modelAudit;
  requireStringFields(audit, ["modelPath"], "modelAudit", errors);
  if (!CAPABILITIES.has(audit?.capability)) {
    errors.push("modelAudit.capability is invalid");
  }
  for (const field of ["truths", "limitations", "prohibitedClaims"]) {
    if (!nonEmptyStrings(audit?.[field])) {
      errors.push(`modelAudit.${field} must contain evidence-backed statements`);
    }
  }

  const cases = plan.research?.caseStudies;
  if (!Array.isArray(cases) || cases.length < 3) {
    errors.push("research.caseStudies must contain at least three cases");
  } else {
    cases.forEach((caseStudy, index) => {
      const prefix = `research.caseStudies[${index}]`;
      requireStringFields(
        caseStudy,
        ["title", "sourceUrl", "narrativeThesis"],
        prefix,
        errors,
      );
      if (!/^https?:\/\//u.test(caseStudy?.sourceUrl ?? "")) {
        errors.push(`${prefix}.sourceUrl must be an HTTP(S) source URL`);
      }
      for (const field of ["transferableMethods", "limitations"]) {
        if (!nonEmptyStrings(caseStudy?.[field])) {
          errors.push(`${prefix}.${field} must contain at least one item`);
        }
      }
    });
  }

  const routes = plan.creativeRoutes;
  const routeIds = new Set();
  if (!Array.isArray(routes) || routes.length < 2) {
    errors.push("creativeRoutes must contain at least two routes");
  } else {
    routes.forEach((route, index) => {
      const prefix = `creativeRoutes[${index}]`;
      if (!SLUG.test(route?.id ?? "")) {
        errors.push(`${prefix}.id must be kebab-case`);
      } else if (routeIds.has(route.id)) {
        errors.push(`duplicate creative route id: ${route.id}`);
      }
      routeIds.add(route?.id);
      requireStringFields(
        route,
        ["title", "thesis", "audienceTakeaway", "modelFit"],
        prefix,
        errors,
      );
      if (
        !Array.isArray(route?.shotArc) ||
        route.shotArc.length !== 5 ||
        !route.shotArc.every((id) => SLUG.test(id))
      ) {
        errors.push(`${prefix}.shotArc must contain five kebab-case shot IDs`);
      }
      if (!nonEmptyStrings(route?.risks)) {
        errors.push(`${prefix}.risks must contain at least one risk`);
      }
    });
  }
  if (!routeIds.has(plan.selectedRouteId)) {
    errors.push("selectedRouteId must identify one creative route");
  }

  const shots = plan.shots;
  const shotIds = new Set();
  if (!Array.isArray(shots) || shots.length !== 5) {
    errors.push("shots must contain exactly five authored shots");
  } else {
    let previousEnd = 0;
    shots.forEach((shot, index) => {
      const prefix = `shots[${index}]`;
      if (!SLUG.test(shot?.id ?? "")) {
        errors.push(`${prefix}.id must be kebab-case`);
      } else if (shotIds.has(shot.id)) {
        errors.push(`duplicate shot id: ${shot.id}`);
      }
      shotIds.add(shot?.id);
      if (shot?.order !== index + 1) {
        errors.push(`${prefix}.order must equal ${index + 1}`);
      }
      if (!validRange(shot?.range)) {
        errors.push(`${prefix}.range is invalid`);
      } else {
        if (Math.abs(shot.range[0] - previousEnd) > 1e-9) {
          errors.push(`${prefix}.range must continue from the previous shot`);
        }
        previousEnd = shot.range[1];
      }
      requireStringFields(
        shot,
        [
          "narrativePurpose",
          "viewerTakeaway",
          "startState",
          "endState",
          "action",
          "lighting",
          "layout",
          "transitionIn",
          "transitionOut",
          "rhythm",
          "hold",
        ],
        prefix,
        errors,
      );
      requireStringFields(
        shot?.camera,
        ["framing", "movement"],
        `${prefix}.camera`,
        errors,
      );
      if (!nonEmptyStrings(shot?.activeComponents)) {
        errors.push(`${prefix}.activeComponents must not be empty`);
      }
      if (!nonEmptyStrings(shot?.truthConstraints)) {
        errors.push(`${prefix}.truthConstraints must not be empty`);
      }
      for (const field of ["eyebrow", "title", "body"]) {
        if (typeof shot?.content?.[field] !== "string") {
          errors.push(`${prefix}.content.${field} must be a string`);
        }
      }
    });
    if (Math.abs(previousEnd - 1) > 1e-9) {
      errors.push("shot ranges must cover the complete normalized timeline");
    }
  }

  const selectedRoute = routes?.find(
    (route) => route.id === plan.selectedRouteId,
  );
  if (
    selectedRoute &&
    JSON.stringify(selectedRoute.shotArc) !==
      JSON.stringify(shots?.map((shot) => shot.id))
  ) {
    errors.push("selected route shotArc must match the authored five shots");
  }

  const animatic = plan.animatic;
  const cameraPrevis = plan.cameraPrevis;
  requireStringFields(cameraPrevis, ["uri", "hiddenCut"], "cameraPrevis", errors);
  if (!Number.isInteger(cameraPrevis?.fps) || cameraPrevis.fps <= 0) {
    errors.push("cameraPrevis.fps must be a positive integer");
  }
  if (
    !Number.isInteger(cameraPrevis?.totalFrames) ||
    cameraPrevis.totalFrames <= 0 ||
    cameraPrevis?.frameStateCount !== cameraPrevis?.totalFrames
  ) {
    errors.push("cameraPrevis must provide exactly one state per canonical frame");
  }
  if (!nonEmptyStrings(cameraPrevis?.continuityPath)) {
    errors.push("cameraPrevis.continuityPath must contain the authored path");
  }
  if (
    !Number.isFinite(cameraPrevis?.maxAbsRollDegrees) ||
    cameraPrevis.maxAbsRollDegrees > 12
  ) {
    errors.push("cameraPrevis.maxAbsRollDegrees must not exceed 12");
  }
  const heroHold = cameraPrevis?.stableHeroHold;
  if (
    !Array.isArray(heroHold) ||
    heroHold.length !== 2 ||
    !heroHold.every(Number.isInteger) ||
    heroHold[0] < 0 ||
    heroHold[1] !== cameraPrevis?.totalFrames - 1 ||
    heroHold[1] - heroHold[0] + 1 < Math.ceil(cameraPrevis?.totalFrames * 0.15)
  ) {
    errors.push("cameraPrevis stable hero hold must cover the final 15% of frames");
  }
  if (cameraPrevis?.reviewed !== true) {
    errors.push("cameraPrevis.reviewed must be true");
  }

  requireStringFields(animatic, ["uri"], "animatic", errors);
  if (animatic?.kind !== "animatic-video") {
    errors.push("animatic.kind must be animatic-video");
  }
  if (!Number.isFinite(animatic?.durationSeconds) || animatic.durationSeconds <= 0) {
    errors.push("animatic.durationSeconds must be greater than zero");
  }
  if (animatic?.reviewed !== true) {
    errors.push("animatic.reviewed must be true");
  }
  if (!nonEmptyStrings(animatic?.reviewNotes)) {
    errors.push("animatic.reviewNotes must contain review evidence");
  }

  const release = plan.confirmation;
  if (through === "animatic") {
    if (!["pending", "automated"].includes(release?.status)) {
      errors.push(
        "confirmation.status must be pending or automated at the animatic gate",
      );
    }
  } else {
    requireStringFields(
      release,
      ["approvalId", "evidenceRef"],
      "confirmation",
      errors,
    );
    if (release?.status !== "automated") {
      errors.push("confirmation.status must be automated");
    }
    if (!validDate(release?.releasedAt)) {
      errors.push("confirmation.releasedAt must be a valid timestamp");
    }
    if (!nonEmptyStrings(release?.checks)) {
      errors.push("confirmation.checks must contain automatic release evidence");
    }
  }

  const history = plan.phaseHistory;
  const expectedPhases =
    through === "animatic" ? PHASES.slice(0, 4) : PHASES;
  const validHistoryLength =
    Array.isArray(history) &&
    (through === "animatic"
      ? history.length >= expectedPhases.length
      : history.length === expectedPhases.length);
  if (!validHistoryLength) {
    errors.push(
      `phaseHistory must contain at least the ${expectedPhases.length} required phases through ${through}`,
    );
  } else {
    let previousTime = -Infinity;
    history.slice(0, expectedPhases.length).forEach((entry, index) => {
      if (entry?.phase !== expectedPhases[index]) {
        errors.push(
          `phaseHistory[${index}].phase must be ${expectedPhases[index]}`,
        );
      }
      if (!validDate(entry?.completedAt)) {
        errors.push(`phaseHistory[${index}].completedAt is invalid`);
      } else {
        const time = Date.parse(entry.completedAt);
        if (time < previousTime) {
          errors.push("phaseHistory timestamps must be ordered");
        }
        previousTime = time;
      }
    });
    if (
      through === "release" &&
      validDate(release?.releasedAt) &&
      history[expectedPhases.length - 1]?.completedAt !== release.releasedAt
    ) {
      errors.push("release timestamp must match the automatic-release phase");
    }
  }
  return errors;
}

export async function loadApprovedCreativeDevelopment(path) {
  const plan = JSON.parse(await readFile(path, "utf8"));
  const errors = validateCreativeDevelopment(plan, { through: "release" });
  if (errors.length) {
    const details = errors.map((error) => `- ${error}`).join("\n");
    throw new Error(
      `Creative development validation failed with ${errors.length} error(s)\n${details}`,
    );
  }
  return plan;
}

async function main() {
  const args = parseArgs(process.argv.slice(2), {
    plan: "required",
    through: "optional",
  });
  const through = args.through ?? "release";
  const plan = JSON.parse(await readFile(args.plan, "utf8"));
  const errors = validateCreativeDevelopment(plan, { through });
  if (errors.length) {
    const details = errors.map((error) => `- ${error}`).join("\n");
    throw new Error(
      `Creative development validation failed with ${errors.length} error(s)\n${details}`,
    );
  }
  process.stdout.write(
    `PASS: creative development is ordered and complete through ${through}\n`,
  );
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main().catch(fail);
}
