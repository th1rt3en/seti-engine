// Next.js calls this for every error of a server component, a route or a server action that was not caught: the report is stored in the bucket.
import { loadConfig } from "@/lib/config";
import { reportError } from "@/lib/errorReport";

export async function onRequestError(
  error: unknown,
  request: { path: string; method: string },
  context: { routerKind: string; routePath: string; routeType: string },
): Promise<void> {
  const cfg = loadConfig();
  await reportError(cfg, error, {
    route: request.path,
    method: request.method,
    routePath: context.routePath,
    routeType: context.routeType,
  });
}
