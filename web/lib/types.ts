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
  search_prompt?: string;
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
    render_settings?: {
      subtitles_enabled?: boolean;
      subtitle_style?: string;
      preset?: string;
      subtitle_position?: string;
      subtitles_behind_subject?: boolean;
      caption_motion?: string;
      words_per_beat?: number;
      subtitle_y_percent?: number;
      enable_emojis?: boolean;
      custom_colors?: {
        main?: string;
        second?: string;
        third?: string;
      };
      bgm_track_id?: string;
      bgm_volume?: number;
      bgm_ducking?: boolean;
      [key: string]: any;
    };
    subtitles?: Array<{
      id: string;
      text: string;
      startTime: number;
      endTime: number;
      words?: Array<{
        word: string;
        start: number;
        end: number;
        semantic_type?: string;
        emoji?: string;
        emphasis?: string;
        layer?: string;
      }>;
      behindSubject?: boolean;
      behind_subject?: boolean;
      style?: any;
    }>;
    razor_captions?: any[];
    shots: ShotDetail[];
  };
}
