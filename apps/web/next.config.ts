import type { NextConfig } from "next";

// The headers of every page. The first five are enforced. The content security policy is only reported for now (the browser's console shows what it would
// have blocked): Next.js needs inline scripts and styles, so the policy is switched to enforcing once the owner has seen that it blocks nothing that is used.
const workerOrigins = [process.env.NEXT_PUBLIC_WORKER_WS_URL, process.env.WORKER_WS_URL, process.env.WORKER_URL].filter(
  (u): u is string => !!u,
);
const policy = [
  "default-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "img-src 'self' data: blob:",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com",
  "frame-src https://challenges.cloudflare.com",
  `connect-src 'self' ${workerOrigins.join(" ")}`.trim(),
].join("; ");
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "Content-Security-Policy-Report-Only", value: policy },
];

const config: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  // The workspace package is TypeScript source.
  transpilePackages: ["@seti/protocol"],
  serverExternalPackages: ["node:sqlite"],
  poweredByHeader: false,
  // Images are served as they are (webp files in public/assets); the optimizer needs the native sharp module, which a Worker cannot load.
  images: { unoptimized: true },
};

export default config;
