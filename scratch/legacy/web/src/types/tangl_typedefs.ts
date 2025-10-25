/* tslint:disable */
/* eslint-disable */

export type MediaRole =
  | "none"

  | "image"
  | "narrative_im"
  | "info_im"
  | "logo_im"
  | "portrait_im"
  | "avatar_im"
  | "dialog_im"
  | "cover_im"

  | "audio"
  | "voice_over"
  | "dialog_vo"
  | "music"
  | "sfx"

  | "video"
  | "animation";

export interface JournalMediaItem {
  media_role: MediaRole;
  url?: string;
  data?: unknown;
  // orientation?: string;
}
export type JournalMediaItems = JournalMediaItem[];
export type JournalMediaDict = Record<MediaRole, JournalMediaItem>;

export interface RuntimeInfo {
  expr: string;
  result: string;
  errors?: string;
}
export interface StoryNodeInfo {
  uid: string;
  [k: string]: unknown;
}
export interface SystemStatus {
  engine: string;
  version: string;
  uptime: string;
  worlds: number;
  users: number;
  media?: JournalMediaItems
  media_dict?: JournalMediaDict
  app_url?: string
  api_url?: string;
  guide_url?: string;
  homepage_url?: string;
}
export interface UserInfo {
  user_id: string;
  user_secret: string;
  created_dt: string;
  last_played_dt: string;
  worlds_played: string[];
  stories_finished: number;
  turns_played: number;
  achievements?: string[];
}
export interface UserSecretResponse {
  user_id: string;
  user_secret: string;
}

export interface UIConfig {
  brand_color: string;
  brand_font?: string;
}

export interface WorldInfo {
  world_id: string;
  version?: string;
  title: string;
  author: string | string[];
  date: string;
  comments?: string;
  ui_config?: UIConfig;
  media?: JournalMediaItems;
  media_dict?: JournalMediaDict;
}
export type StyleHints = { [k: string]: unknown; };

export interface StyledJournalItem {
  uid: string;
  text?: string;
  icon?: string;
  media?: JournalMediaItems;
  media_dict?: JournalMediaDict;
  style_id?: string;
  style_cls?: string;
  style_dict?: StyleHints
}

export interface JournalStoryUpdate {
  uid: string;
  text?: string;
  icon?: string;
  media?: JournalMediaItems;
  media_dict?: JournalMediaDict;
  style_id?: string;
  style_cls?: string;
  style_dict?: StyleHints

  actions?: JournalAction[];
  dialog?: StyledJournalItem[];
}

export interface JournalAction {
  uid: string;
  text: string;
  icon?: string;
  media?: JournalMediaItems;
  media_dict?: JournalMediaDict;
  style_id?: string;
  style_cls?: string;
  style_dict?: StyleHints;

  payload?: string;
}

export interface JournalKVItem {
  key: string;
  value?: number | string | unknown[];
  icon?: string;
  style_id?: string;
  style_cls?: string;
  style_dict?: StyleHints;
}

export type JournalEntry = JournalStoryUpdate[];
export type StoryStatus = JournalKVItem[];
export type WorldSceneList = JournalKVItem[];
export type WorldList = JournalKVItem[];
