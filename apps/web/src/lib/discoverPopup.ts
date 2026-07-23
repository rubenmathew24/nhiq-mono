/** Shared popup copy for Discover tract inspection (no report links). */

export function popupCopy(geoid: string, score: number | null): string {
  if (score == null) {
    return `Score unavailable · Tract ${geoid}`;
  }
  return `Overall ${score.toFixed(1)} · Tract ${geoid}`;
}
