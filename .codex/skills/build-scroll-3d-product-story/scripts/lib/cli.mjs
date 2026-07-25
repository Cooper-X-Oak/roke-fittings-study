import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";

export function parseArgs(argv, definitions) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) {
      throw new Error(`Unexpected argument: ${token}`);
    }
    const key = token.slice(2);
    if (!(key in definitions)) {
      throw new Error(`Unknown option: --${key}`);
    }
    const definition = definitions[key];
    if (definition === "boolean") {
      result[key] = true;
      continue;
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      throw new Error(`Missing value for --${key}`);
    }
    result[key] = value;
    index += 1;
  }
  for (const [key, definition] of Object.entries(definitions)) {
    if (definition === "required" && !result[key]) {
      throw new Error(`Missing required option: --${key}`);
    }
  }
  return result;
}

export async function writeJson(outputPath, value) {
  const absolute = resolve(outputPath);
  await mkdir(dirname(absolute), { recursive: true });
  await writeFile(absolute, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export function printOrWrite(value, outputPath) {
  if (outputPath) {
    return writeJson(outputPath, value);
  }
  process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
  return Promise.resolve();
}

export function fail(error) {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`ERROR: ${message}\n`);
  process.exitCode = 1;
}
