// Where the circles of a triggerable mission are on the picture of its card, as fractions of the width and the height of the picture, so that a
// circle can be clicked on the card itself. Measured on the pictures (the circles are in the order of the engine's definition, left to right).
// The cards that are not in the list have no known place: the page then offers the circles as buttons.
export type CirclePlace = { x: number; y: number };

const row = (y: number, ...xs: number[]): CirclePlace[] => xs.map((x) => ({ x, y }));

const THREE = [0.24, 0.52, 0.8] as const;
const THREE_EXP = [0.23, 0.5, 0.78] as const;

export const MISSION_CIRCLES: Record<string, CirclePlace[]> = {
  "1": row(0.765, 0.54, 0.83),
  "2": row(0.765, 0.54, 0.83),
  "3": row(0.765, 0.54, 0.83),
  "4": row(0.765, 0.54, 0.83),
  "76": row(0.76, ...THREE),
  "77": row(0.81, ...THREE),
  "78": row(0.815, ...THREE),
  "79": row(0.815, ...THREE),
  "80": row(0.76, ...THREE),
  "82": row(0.77, 0.31, 0.7),
  "94": row(0.81, ...THREE),
  "101": row(0.76, ...THREE),
  "106": row(0.814, ...THREE),
  "107": row(0.81, 0.32, 0.725),
  "116": row(0.81, ...THREE),
  "117": row(0.81, 0.32, 0.72),
  "128": row(0.757, ...THREE),
  "129": row(0.757, ...THREE),
  "131": row(0.81, 0.32, 0.72),
  "138": row(0.816, ...THREE),
  "ET.13": row(0.81, ...THREE),
  "ET.29": row(0.81, ...THREE),
  SE_EN_02: row(0.8, 0.3, 0.73),
  "SA.21": row(0.777, 0.29, 0.72),
  "SA.23": row(0.81, 0.31, 0.72),
  "SA.24": row(0.764, 0.32, 0.7),
  "SA.25": row(0.767, 0.31, 0.69),
  "SA.26": row(0.77, 0.31, 0.7),
  "SA.33": row(0.81, 0.51),
  "GL.3": row(0.75, ...THREE_EXP),
  "GL.4": row(0.75, ...THREE_EXP),
  "GL.5": row(0.8, 0.31, 0.71),
  "GL.6": row(0.8, 0.31, 0.72),
  "GL.7": row(0.805, ...THREE_EXP),
  "AM.15": row(0.81, 0.31, 0.71),
  "AM.16": row(0.81, 0.31, 0.71),
  "AM.17": row(0.81, ...THREE_EXP),
  "AM.18": row(0.81, 0.3, 0.71),
};
