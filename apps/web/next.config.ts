import type { NextConfig } from "next";

const config: NextConfig = {
  // The workspace package is TypeScript source.
  transpilePackages: ["@seti/protocol"],
  serverExternalPackages: ["node:sqlite"],
  poweredByHeader: false,
  // Images are served as they are (webp files in public/assets); the optimizer needs the native sharp module, which a Worker cannot load.
  images: { unoptimized: true },
};

export default config;
