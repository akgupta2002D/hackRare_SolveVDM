// Scene helpers for non-floater visual reference objects.
// These objects move with camera pan immediately (no lag),
// so users can compare world motion vs floater lag behavior.

export function initSceneObjects(count = 42, seedStart = 1337) {
  let seed = seedStart;
  const rand = () => {
    seed = (1664525 * seed + 1013904223) >>> 0;
    return seed / 4294967296;
  };

  return Array.from({ length: count }, () => {
    const t = rand();
    return {
      x: (rand() - 0.5) * 3600,
      y: -80 + (rand() - 0.5) * 55,
      size: 24 + rand() * 56,
      type: t < 0.4 ? "tree" : t < 0.72 ? "house" : "pole",
    };
  });
}
