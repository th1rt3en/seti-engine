import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// The website runs as a Cloudflare Worker (decision D30); the defaults are enough: no cache, no queues.
export default defineCloudflareConfig();
