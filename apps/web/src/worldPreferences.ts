import type { PreferenceDeclaration, PreferenceValue } from '@/types'

/**
 * Viewer preferences a world declares in its `ui-preferences` channel. Values
 * live in this browser, one record per world, and never reach the service or
 * the ledger: they bind presentation only (`media_visibility`, clip choice).
 */
export type PreferenceValues = Record<string, PreferenceValue>

const storageKey = (worldId: string): string => `storytangl.ui-preferences.${worldId}`

const admits = (declaration: PreferenceDeclaration, value: unknown): value is PreferenceValue =>
  declaration.kind === 'boolean'
    ? typeof value === 'boolean'
    : typeof value === 'string' && declaration.values.includes(value)

/**
 * Each declared preference's value: the one stored for this world when the
 * declaration still admits it, else the world's default. A stored value is
 * browser data from an earlier visit, so a world that has since changed its
 * declarations quietly resets the values it no longer admits.
 */
export const loadPreferenceValues = (
  worldId: string,
  declarations: PreferenceDeclaration[]
): PreferenceValues => {
  const raw = localStorage.getItem(storageKey(worldId))
  const stored: Record<string, unknown> = raw ? JSON.parse(raw) : {}
  return Object.fromEntries(
    declarations.map((declaration) => {
      const value = stored[declaration.id]
      return [declaration.id, admits(declaration, value) ? value : declaration.default]
    })
  )
}

export const savePreferenceValues = (worldId: string, values: PreferenceValues): void => {
  localStorage.setItem(storageKey(worldId), JSON.stringify(values))
}
