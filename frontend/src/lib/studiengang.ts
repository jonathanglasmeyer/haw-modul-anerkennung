/**
 * Studiengang utilities for filtering units/modules
 */

export type Studiengang = 'BAPuMa' | 'MAPuMa' | 'BAEGov';

export const STUDIENGAENGE: Record<Studiengang, string> = {
  BAPuMa: 'BA Public Management',
  MAPuMa: 'MA Public Management',
  BAEGov: 'BA E-Government',
};

/**
 * Extract studiengang from module/unit ID
 * @param id - Module or Unit ID (e.g. "BAPuMa_M01" or "BAEGov_M05_U1")
 * @returns Studiengang prefix or null if not found
 */
export function getStudiengangFromId(id: string): Studiengang | null {
  const prefix = id.split('_')[0];
  if (prefix in STUDIENGAENGE) {
    return prefix as Studiengang;
  }
  return null;
}

/**
 * Check if a module/unit ID belongs to a specific studiengang
 */
export function matchesStudiengang(id: string, studiengang: Studiengang): boolean {
  return id.startsWith(studiengang);
}
