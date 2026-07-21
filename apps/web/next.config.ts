import type { NextConfig } from "next";
import path from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const webRoot = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(webRoot, "../..");

function loadRootEnvFile() {
  const envPath = path.join(repoRoot, ".env");
  if (!existsSync(envPath)) return;

  for (const line of readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const separator = trimmed.indexOf("=");
    if (separator === -1) continue;
    const key = trimmed.slice(0, separator).trim();
    let value = trimmed.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

loadRootEnvFile();

// Only forward non-empty public env into the client bundle.
const publicEnv: Record<string, string> = {};
if (process.env.NEXT_PUBLIC_API_URL?.trim()) {
  publicEnv.NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL.trim();
}
if (process.env.NEXT_PUBLIC_MAPBOX_TOKEN?.trim()) {
  publicEnv.NEXT_PUBLIC_MAPBOX_TOKEN =
    process.env.NEXT_PUBLIC_MAPBOX_TOKEN.trim();
}

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    // Monorepo has a root package-lock.json; without this, Turbopack resolves
    // modules from repo root where next is not installed (apps/web/node_modules).
    root: webRoot,
  },
  env: publicEnv,
};

export default nextConfig;
