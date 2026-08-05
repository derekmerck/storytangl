const PLAYER_SECRET_KEY = 'storytangl.player-secret'

/** Return the browser-local recovery secret for the current player. */
export const loadPlayerSecret = (): string | null => localStorage.getItem(PLAYER_SECRET_KEY)

/** Persist the recovery secret that reconnects this browser to its player. */
export const savePlayerSecret = (secret: string): void => {
  localStorage.setItem(PLAYER_SECRET_KEY, secret)
}

/** Forget a stale browser-local recovery secret. */
export const clearPlayerSecret = (): void => {
  localStorage.removeItem(PLAYER_SECRET_KEY)
}

/** Create a transport secret for a first-visit player. */
export const createPlayerSecret = (): string => crypto.randomUUID()
