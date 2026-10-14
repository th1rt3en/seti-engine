// The image optimizer is turned off (next.config.ts: images.unoptimized), so this is never called.
module.exports = function sharp() {
  throw new Error("sharp is not available: images are served unoptimized");
};
