#!/usr/bin/env node

import { basename } from "node:path";

import { fail, parseArgs, printOrWrite } from "./lib/cli.mjs";
import { inspectModel } from "./lib/model-analysis.mjs";

async function main() {
  const args = parseArgs(process.argv.slice(2), {
    model: "required",
    out: "optional",
  });
  const inspection = await inspectModel(args.model, {
    publicPath: basename(args.model),
  });
  await printOrWrite(inspection, args.out);
}

main().catch(fail);
