/**
 * StoryTangl shared type definitions.
 *
 * These interfaces mirror the payloads returned by the StoryTangl API.  They are heavily
 * referenced throughout the UI, so keeping them explicit and well documented makes
 * composables and stores significantly easier to work with.
 */

/**
 * Media roles supported by the API.
 */
export type MediaRole =
  | 'none'
  | 'image'
  | 'narrative_im'
  | 'info_im'
  | 'logo_im'
  | 'portrait_im'
  | 'avatar_im'
  | 'dialog_im'
  | 'cover_im'
  | 'audio'
  | 'voice_over'
  | 'dialog_vo'
  | 'music'
  | 'sfx'
  | 'video'
  | 'animation'

/**
 * Metadata describing a single media item.
 */
export interface JournalMediaItem {
  media_role: MediaRole
  url?: string
  data?: unknown
  orientation?: 'portrait' | 'landscape' | 'square' | string
}

export type JournalMediaItems = JournalMediaItem[]

/**
 * Helper dictionary keyed by media role for quick lookup in components.
 */
export type JournalMediaDict = Partial<Record<MediaRole, JournalMediaItem>>

/**
 * Summary of runtime evaluations returned by diagnostics endpoints.
 */
export interface RuntimeInfo {
  expr: string
  result: string
  errors?: string
}

/**
 * Basic details about a story node, primarily used for debugging displays.
 */
export interface StoryNodeInfo {
  uid: string
  [key: string]: unknown
}

/**
 * High-level status information for the running engine instance.
 */
export interface SystemStatus {
  engine: string
  version: string
  uptime: string
  worlds: number
  users: number
  media?: JournalMediaItems
  media_dict?: JournalMediaDict
  app_url?: string
  api_url?: string
  guide_url?: string
  homepage_url?: string
}

/**
 * Authenticated user metadata.
 */
export interface UserInfo {
  user_id: string
  user_secret: string
  created_dt: string
  last_played_dt: string
  worlds_played: string[]
  stories_finished: number
  turns_played: number
  achievements?: string[]
}

export interface UserSecretResponse {
  user_id: string
  user_secret: string
}

/**
 * Optional configuration that allows worlds to adjust UI appearance.
 */
export interface UIConfig {
  brand_color: string
  brand_font?: string
}

/**
 * Detailed information about a world, including media and UI hints.
 */
export interface WorldInfo {
  world_id: string
  version?: string
  title: string
  author: string | string[]
  date: string
  comments?: string
  ui_config?: UIConfig
  media?: JournalMediaItems
  media_dict?: JournalMediaDict
  [key: string]: unknown
}

export type StyleHints = Record<string, unknown>

/**
 * Shared fields for styled journal payloads.
 */
export interface StyledJournalItem {
  uid: string
  text?: string
  icon?: string
  media?: JournalMediaItems
  media_dict?: JournalMediaDict
  style_id?: string
  style_cls?: string
  style_dict?: StyleHints
}

/**
 * Core story fragment delivered to the client when the narrative advances.
 */
export interface JournalStoryUpdate extends StyledJournalItem {
  actions?: JournalAction[]
  dialog?: StyledJournalItem[]
}

/**
 * Interactive choice presented to the reader.
 */
export interface JournalAction extends StyledJournalItem {
  text: string
  payload?: string
}

/**
 * Generic key/value item displayed in status panels.
 */
export interface JournalKVItem {
  key: string
  value?: number | string | unknown[]
  icon?: string
  style_id?: string
  style_cls?: string
  style_dict?: StyleHints
}

export type JournalEntry = JournalStoryUpdate[]
export type StoryStatus = JournalKVItem[]
export type WorldSceneList = JournalKVItem[]
export type WorldList = JournalKVItem[]
