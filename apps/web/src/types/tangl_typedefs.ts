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
 * Runtime acknowledgment and story-session summary payloads returned by the API.
 */
export interface RuntimeInfo {
  status: string
  code?: string | null
  message?: string | null
  cursor_id?: string | null
  step?: number | null
  details?: Record<string, unknown> | null
  [key: string]: unknown
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
  summary?: string
  ui_config?: UIConfig
  media?: JournalMediaItems
  media_dict?: JournalMediaDict
  guide_url?: string
  homepage_url?: string
  [key: string]: unknown
}

export type StyleHints = Record<string, unknown>

/**
 * Shared fields for styled journal payloads.
 */
export interface StyledJournalItem {
  uid: string
  text?: string
  label?: string
  icon?: string
  key?: string
  media?: JournalMediaItems
  media_dict?: JournalMediaDict
  style_id?: string
  style_cls?: string
  style_dict?: StyleHints
  style?: StyleHints
  [key: string]: unknown
}

/**
 * Individual dialog line rendered within a story block.
 */
export interface DialogBlock extends StyledJournalItem {
  label?: string
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
  style?: StyleHints
}

export type PrimitiveValue = string | number | boolean

export interface KvRow {
  key: string
  value: PrimitiveValue
  max?: PrimitiveValue | null
  delta?: number | null
  unit?: string | null
  hint?: 'bar' | 'fraction' | 'delta' | 'tag' | string | null
  emphasis?: 'ok' | 'warn' | 'danger' | 'subtle' | string | null
  hints?: PresentationHints | null
}

export interface ScalarValue {
  value_type: 'scalar'
  value: PrimitiveValue
}

export interface KvListValue {
  value_type: 'kv_list'
  items: KvRow[]
}

export interface ProjectedItem {
  label: string
  detail?: string | null
  tags?: string[]
}

export interface ItemListValue {
  value_type: 'item_list'
  items: ProjectedItem[]
}

export interface TableValue {
  value_type: 'table'
  columns: string[]
  rows: PrimitiveValue[][]
}

export interface BadgeListValue {
  value_type: 'badges'
  items: string[]
}

export type SectionValue = ScalarValue | KvListValue | ItemListValue | TableValue | BadgeListValue

export interface ProjectedSection {
  section_id: string
  title: string
  kind?: string | null
  value: SectionValue
  hints?: StyleHints | null
}

export interface ProjectedState {
  sections: ProjectedSection[]
}

export interface InfoAffordance {
  kind: string
  label?: string | null
  shortcuts?: string[]
  query?: Record<string, unknown> | null
}

export interface InfoState {
  version?: number | null
  dirty_kinds?: string[]
  available_kinds?: string[]
}

export type StoryStatus = ProjectedState
export type WorldSceneList = JournalKVItem[]
export type WorldList = JournalKVItem[]

export type FragmentId = string

export interface PresentationHints {
  style_name?: string | null
  style_tags?: string[]
  style_dict?: StyleHints
  icon?: string | null
  [key: string]: unknown
}

export interface BaseStoryFragment {
  uid: FragmentId
  fragment_type: string
  content?: unknown
  label?: string | null
  origin_id?: string | null
  step?: number | null
  tags?: string[]
  [key: string]: unknown
}

export interface ContentStoryFragment extends BaseStoryFragment {
  fragment_type: 'content'
  content?: unknown
  source_id?: string | null
  content_format?: string | null
  format?: string | null
  hints?: PresentationHints | null
  presentation_hints?: PresentationHints | null
}

export interface AttributedStoryFragment extends BaseStoryFragment {
  fragment_type: 'attributed'
  who: string
  how: string
  media: string
  content?: unknown
  hints?: PresentationHints | null
}

export interface MediaStoryFragment extends BaseStoryFragment {
  fragment_type: 'media'
  content?: unknown
  content_format?: 'url' | 'data' | 'xml' | 'json' | 'rit' | string
  media_role?: MediaRole | string | null
  scope?: string | null
  staging_hints?: Record<string, unknown> | null
  generation_status?: string | null
  url?: string
  src?: string
  data?: unknown
  text?: string
}

export interface GroupStoryFragment extends BaseStoryFragment {
  fragment_type: 'group' | 'dialog'
  group_type?: string | null
  member_ids: FragmentId[]
  hints?: PresentationHints | null
  presentation_hints?: PresentationHints | null
  zone_role?: string | null
  constraints?: Record<string, unknown> | null
  layout_hints?: Record<string, unknown> | null
}

export interface PieceStoryFragment extends BaseStoryFragment {
  fragment_type: 'piece'
  piece_id?: FragmentId | null
  kind?: string | null
  realized?: boolean | null
  available?: boolean | null
  unavailable_reason?: string | null
  display_state?: string | null
  zone_ref?: FragmentId | null
  properties?: Record<string, unknown> | null
  cost?: Array<Record<string, unknown>> | null
  hints?: PresentationHints | null
  presentation_hints?: PresentationHints | null
}

export interface KvStoryFragment extends BaseStoryFragment {
  fragment_type: 'kv'
  content: KvRow[]
  hints?: PresentationHints | null
}

export interface CostPreview {
  ledger_key: string
  delta: number
  unit?: string | null
}

export interface Blocker {
  code?: string | null
  message: string
  refs?: FragmentId[]
  [key: string]: unknown
}

export interface PieceConstraints {
  same_property?: string[] | null
  different_property?: string[] | null
  target_zone_ref?: FragmentId | null
  source_zone_ref?: FragmentId | null
  target_kind?: string[] | null
  predicate_ref?: string | null
}

export interface LengthValidator {
  kind: 'length'
  min?: number | null
  max?: number | null
}

export interface RegexValidator {
  kind: 'regex'
  pattern: string
  flags?: string | null
  message?: string | null
}

export interface EnumValidator {
  kind: 'enum'
  values: string[]
  case_sensitive?: boolean
}

export interface BackendValidator {
  kind: 'backend'
}

export type AcceptsValidator = LengthValidator | RegexValidator | EnumValidator | BackendValidator

export interface PickAccepts {
  kind: 'pick'
  cost_previews?: CostPreview[]
}

export interface TextAccepts {
  kind: 'text'
  required?: boolean
  placeholder?: string | null
  validators?: AcceptsValidator[]
}

export interface QuantityAccepts {
  kind: 'quantity'
  required?: boolean
  min?: number | null
  max?: number | null
  step?: number
  unit?: string | null
  ledger_ref?: string | null
  cost_previews?: CostPreview[]
}

export interface PiecesAccepts {
  kind: 'pieces'
  min?: number
  max?: number
  constraints?: PieceConstraints | null
}

export interface PlaceAccepts {
  kind: 'place'
  source_zone_ref?: FragmentId | null
  target_zone_ref?: FragmentId | null
  edge_ref?: FragmentId | null
  predicate_ref?: string | null
  source_constraints?: PieceConstraints | null
  required?: boolean
}

export interface LegacyPayloadAccepts {
  input: string
  payload_type?: string | null
  min?: number | null
  max?: number | null
  step?: number | null
  unit?: string | null
  placeholder?: string | null
  required?: boolean
  validators?: AcceptsValidator[]
}

export interface ComposePart {
  role: string
  accepts: PickAccepts | TextAccepts | QuantityAccepts | PiecesAccepts | PlaceAccepts
}

export interface ComposeAccepts {
  kind: 'compose'
  parts: ComposePart[]
}

export type ChoiceAccepts =
  | PickAccepts
  | TextAccepts
  | QuantityAccepts
  | PiecesAccepts
  | PlaceAccepts
  | ComposeAccepts
  | LegacyPayloadAccepts

export interface ChoiceUIHints {
  hotkey?: string | null
  icon?: string | null
  emphasis?: 'primary' | 'subtle' | 'warning' | 'danger' | string | null
  widget?: string | null
  source_kind?: string | null
  contribution?: string | null
  direction?: string | null
  time_delta?: unknown
  cost_previews?: CostPreview[]
  [key: string]: unknown
}

export interface ChoiceStoryFragment extends BaseStoryFragment {
  fragment_type: 'choice'
  edge_id: FragmentId
  text: string
  available?: boolean
  unavailable_reason?: string | null
  blockers?: Blocker[] | null
  accepts?: ChoiceAccepts | null
  ui_hints?: ChoiceUIHints | null
  payload?: unknown
}

export interface ControlStoryFragment extends BaseStoryFragment {
  fragment_type: 'update' | 'delete'
  ref_type?: string
  ref_id?: FragmentId
  reference_type?: string
  reference_id?: FragmentId
  payload?: Record<string, unknown> | null
}

export interface RollStoryFragment extends BaseStoryFragment {
  fragment_type: 'roll'
  label?: string | null
  kind?: string | null
  inputs?: Record<string, unknown> | null
  outcome?: string | null
  narrative?: string | null
  against?: Record<string, unknown> | null
  ritual_hints?: Record<string, unknown> | null
}

export type StoryFragment =
  | ContentStoryFragment
  | AttributedStoryFragment
  | MediaStoryFragment
  | GroupStoryFragment
  | PieceStoryFragment
  | KvStoryFragment
  | ChoiceStoryFragment
  | ControlStoryFragment
  | RollStoryFragment
  | BaseStoryFragment

export interface UxEvent {
  event_id: string
  event_type: string
  message: string
  presentation: 'inline' | 'interrupt'
  replay: boolean
  severity: 'info' | 'success' | 'warning' | 'error'
  details?: Record<string, unknown>
}

export interface RuntimeEnvelope {
  cursor_id?: string | null
  step?: number | null
  fragments: StoryFragment[]
  ux_events?: UxEvent[]
  last_redirect?: Record<string, unknown> | null
  redirect_trace?: Array<Record<string, unknown>>
  metadata?: Record<string, unknown>
}

export interface StorySceneModel {
  key: string
  uid: FragmentId
  memberIds: FragmentId[]
  metadata?: Record<string, unknown>
}
