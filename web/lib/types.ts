export interface BGMTrackOption {
  id: string;
  name: string;
  filename: string;
  genre: string;
  default_volume: number;
  description?: string;
  available: boolean;
  preview_url: string;
}

export interface StockVideoCandidate {
  id: number;
  thumbnail: string;
  duration: number;
  width: number;
  height: number;
  url: string;
  download_url: string;
}

export interface MemeTemplateOption {
  key: string;
  name: string;
  filename: string;
  category: string;
  description?: string;
  is_featured?: boolean;
  preview_url: string;
  fields: { name: string; label: string; placeholder: string }[];
}

export interface CuratedMoment {
  moment_id: string;
  timestamp_range: string;
  start_time_sec: number;
  end_time_sec: number;
  screen_hook: string;
  post_caption: string;
  broll_theme?: string;
  broll_sources: string[];
  angle?: string;
}

export interface CampaignSummary {
  id: string;
  name: string;
  client: string;
  rate: string;
  total_budget: string;
  platforms: string[];
  description: string;
  allow_bgm: boolean;
  allow_ai_broll: boolean;
  max_broll_ratio: number;
  watermark_required: boolean;
  subtitle_style: string;
  rules_checklist: string[];
  instant_rejections: string[];
  curated_moments: CuratedMoment[];
}

export interface JobSummary {
  job_id: string;
  filename: string;
  status: string;
  progress: number;
  created_at: string;
  updated_at: string;
  error_message?: string;
  has_video: boolean;
  output_video_path?: string;
  emotional_summary?: string;
  drive_file_url?: string;
  campaign_id?: string;
  review_data?: {
    verdict: string;
    score: number;
    feedback: string;
  };
}

export interface ShotDetail {
  shot_id: string;
  start_time: number;
  end_time: number;
  duration?: number;
  speed?: number;
  dialogue_quote?: string;
  emotional_core?: string;
  visceral_human_metaphor?: string;
  asset_title?: string;
  emotional_score?: number;
  video_url?: string;
  thumbnail_url?: string;
  status?: string;
  style?: string;
  meme_template?: string;
  meme_captions?: Record<string, string>;
  meme_template_resolved?: string;
  transition?: {
    type_in: string;
    duration_in: number;
    type_out: string;
    duration_out: number;
    stinger_sfx?: {
      file: string;
      path: string;
      volume: number;
      audio_url?: string;
    };
  };
  contextual_sfx?: {
    id: number;
    name: string;
    file: string;
    category: string;
    volume: number;
    start_offset: number;
    reason?: string;
    audio_url?: string;
  };
  emotion?: string;
  sentiment?: string;
  tone_of_voice?: string;
  tone_intensity?: number;
  impact_score?: number;
  visualizability?: number;
  broll_priority?: number;
  visual_strategy?: string;
  broll_search_queries?: string[];
  avoid_visuals?: string[];
  search_query?: string;
  search_prompt?: string;
  category?: string;
}

export interface JobDetail extends JobSummary {
  transcript_text?: string;
  edit_plan?: {
    summary: string;
    total_duration?: number;
    broll_shot_count?: number;
    openreel_custom_edited?: boolean;
    last_openreel_sync?: string;
    last_render_revision?: number;
    edit_revision?: number;
    render_stale?: boolean;
    subtitles_behind_subject?: boolean;
    short_edits?: Array<{
      job_id: string;
      title: string;
      source: string;
      start: number;
      end: number;
      batch_id?: string | null;
      candidate_id?: string | null;
      status?: string;
    }>;
    workflow?: {
      type?: string;
      source?: string;
      parent_job_id?: string;
      batch_id?: string | null;
      candidate_id?: string | null;
      status?: string;
      title?: string;
      source_interval?: { start: number; end: number };
      caption_style?: string | null;
      caption_motion?: string | null;
      subtitles_behind_subject?: boolean | null;
      error?: string;
    };
    hook_text?: string;
    subtitles?: Array<Record<string, any>>;
    zooms?: Array<Record<string, any>>;
    render_settings?: {
      subtitles_enabled?: boolean;
      subtitle_style?: string;
      subtitle_position?: string;
      subtitles_behind_subject?: boolean;
      bgm_track_id?: string;
      bgm_volume?: number;
      bgm_ducking?: boolean;
      preset?: string;
      words_per_beat?: number;
      caption_motion?: string;
      enable_emojis?: boolean;
      subtitle_y_percent?: number;
      custom_colors?: {
        main?: string;
        second?: string;
        third?: string;
        [key: string]: string | undefined;
      };
    };
    shots: ShotDetail[];
  };
}
