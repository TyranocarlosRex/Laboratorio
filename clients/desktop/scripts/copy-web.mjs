import { cp, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const currentDir = dirname(fileURLToPath(import.meta.url));
const desktopDir = resolve(currentDir, "..");
const repoRoot = resolve(desktopDir, "..", "..");
const source = resolve(repoRoot, "clients", "web", "dist");
const destination = resolve(desktopDir, "renderer");

await rm(destination, { force: true, recursive: true });
await mkdir(destination, { recursive: true });
await cp(source, destination, { recursive: true });
