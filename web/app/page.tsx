"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Upload,
  Play,
  Film,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  Brain,
  Star,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Send,
  Trash2,
  Plus,
  Download,
  Eye,
  Zap,
  Sliders,
  FolderSync,
  Layers,
  X,
  AlertTriangle,
  Link2,
  Video,
  FileCode,
  Archive,
  Volume2,
  VolumeX,
  Search,
  Music,
  Pause,
  Scissors,
  Type,
  Tv
} from "lucide-react";
import { formatDuration, getStatusColor } from "../lib/utils";

interface BGMTrackOption {
  id: string;
  name: string;
  filename: string;
  genre: string;
  default_volume: number;
  description?: string;
  available: boolean;
  preview_url: string;
}

interface StockVideoCandidate {
  id: number;
  thumbnail: string;
  duration: number;
  width: number;
  height: number;
  url: string;
  download_url: string;
}

interface MemeTemplateOption {
  key: string;
  name: string;
  filename: string;
  category: string;
  description?: string;
  is_featured?: boolean;
  preview_url: string;
  fields: { name: string; label: string; placeholder: string }[];
}

interface CuratedMoment {
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

interface CampaignSummary {
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

interface JobSummary {
  job_id: string;
  filename: string;
  status: string;
  progress: number;
  created_at: string;
  updated_at: string;
  error_message?: string;
  has_video: boolean;
  emotional_summary?: string;
  drive_file_url?: string;
  campaign_id?: string;
  review_data?: {
    verdict: string;
    score: number;
    feedback: string;
  };
}

interface ShotDetail {
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
}

interface JobDetail extends JobSummary {
  transcript_text?: string;
  edit_plan?: {
    summary: string;
    total_duration?: number;
    broll_shot_count?: number;
    render_settings?: {
      subtitles_enabled?: boolean;
      subtitle_style?: string;
      subtitle_position?: string;
      bgm_track_id?: string;
      bgm_volume?: number;
      bgm_ducking?: boolean;
    };
    shots: ShotDetail[];
  };
}

export default function StudioDashboard() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [stats, setStats] = useState({
    total_jobs: 0,
    completed_count: 0,
    in_progress_count: 0,
    average_emotional_score: 9.0,
    active_learning_rules: 4,
  });
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showUploadMode, setShowUploadMode] = useState(false);
  const [showProjectPicker, setShowProjectPicker] = useState(false);
  const [uploadTab, setUploadTab] = useState<"file" | "youtube">("file");
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [isImportingYouTube, setIsImportingYouTube] = useState(false);
  const [jobToDelete, setJobToDelete] = useState<{ id: string; name: string } | null>(null);
  const [showClearAllModal, setShowClearAllModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(10);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  // Meme Studio & Customizer State
  const [showMemeModal, setShowMemeModal] = useState(false);
  const [memeTargetShot, setMemeTargetShot] = useState<ShotDetail | null>(null);
  const [memeTemplates, setMemeTemplates] = useState<MemeTemplateOption[]>([]);
  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string>("stepped_in_shit");
  const [memeCaptions, setMemeCaptions] = useState<Record<string, string>>({});
  const [selectedSfxFile, setSelectedSfxFile] = useState<string>("81_vine_boom.mp3");
  const [sfxCatalog, setSfxCatalog] = useState<any[]>([]);
  const [isGeneratingMeme, setIsGeneratingMeme] = useState(false);
  const [isRerenderingMaster, setIsRerenderingMaster] = useState(false);
  const [memeSearchQuery, setMemeSearchQuery] = useState("");
  const [standaloneMemeResult, setStandaloneMemeResult] = useState<{ video_url?: string; image_url?: string; shot_id?: string } | null>(null);
  const [isStandaloneMode, setIsStandaloneMode] = useState(false);

  // Subtitles & BGM Engine States
  const [bgmTracks, setBgmTracks] = useState<BGMTrackOption[]>([]);
  const [subtitlesEnabled, setSubtitlesEnabled] = useState<boolean>(true);
  const [subtitleStyle, setSubtitleStyle] = useState<string>("hormozi");
  const [subtitlePosition, setSubtitlePosition] = useState<string>("bottom");
  const [selectedBgmId, setSelectedBgmId] = useState<string>("chill_lofi");
  const [bgmVolume, setBgmVolume] = useState<number>(0.16);
  const [bgmDucking, setBgmDucking] = useState<boolean>(true);
  const [playingBgmPreview, setPlayingBgmPreview] = useState<string | null>(null);
  const [isSavingSettings, setIsSavingSettings] = useState<boolean>(false);
  const bgmAudioRef = useRef<HTMLAudioElement | null>(null);

  // Playhead Cutaway Inserter States
  const [showInsertCutawayModal, setShowInsertCutawayModal] = useState<boolean>(false);
  const [insertCutawayTime, setInsertCutawayTime] = useState<number>(0);
  const [insertCutawayDur, setInsertCutawayDur] = useState<number>(1.8);
  const [insertCutawayStyle, setInsertCutawayStyle] = useState<"stockpile" | "meme">("stockpile");
  const [insertCutawayPrompt, setInsertCutawayPrompt] = useState<string>("focused professional");
  const [insertCutawayMemeTemplate, setInsertCutawayMemeTemplate] = useState<string>("stepped_in_shit");
  const [isInsertingCutaway, setIsInsertingCutaway] = useState<boolean>(false);

  // In-Card B-Roll Swapper States
  const [showSwapModal, setShowSwapModal] = useState<boolean>(false);
  const [swapTargetShot, setSwapTargetShot] = useState<ShotDetail | null>(null);
  const [swapSearchQuery, setSwapSearchQuery] = useState<string>("");
  const [stockCandidates, setStockCandidates] = useState<StockVideoCandidate[]>([]);
  const [isSearchingStock, setIsSearchingStock] = useState<boolean>(false);
  const [isSwappingStock, setIsSwappingStock] = useState<boolean>(false);
  const [swapTab, setSwapTab] = useState<"search" | "upload">("search");
  const [isUploadingCustom, setIsUploadingCustom] = useState<boolean>(false);

  // Shot Trimming State
  const [isTrimming, setIsTrimming] = useState<Record<string, boolean>>({});

  // SDR2HDR Upscaler & HDR10 States
  const [showHdrModal, setShowHdrModal] = useState<boolean>(false);
  const [hdrScale, setHdrScale] = useState<number>(1.0);
  const [hdrTone, setHdrTone] = useState<string>("vivid");
  const [hdrFastMode, setHdrFastMode] = useState<boolean>(true);
  const [isUpscalingHdr, setIsUpscalingHdr] = useState<boolean>(false);
  const [hdrProgress, setHdrProgress] = useState<number>(0);
  const [hdrFps, setHdrFps] = useState<number>(0);
  const [viewingHdrVideo, setViewingHdrVideo] = useState<boolean>(false);
  const [hdrAvailable, setHdrAvailable] = useState<boolean>(false);
  const [hdrMeta, setHdrMeta] = useState<any>(null);

  // OpenReel Integration State
  const [isOpenReelExporting, setIsOpenReelExporting] = useState<boolean>(false);
  const [openReelModalData, setOpenReelModalData] = useState<any>(null);
  const [embeddedOpenReelJob, setEmbeddedOpenReelJob] = useState<string | null>(null);

  // Campaigns & Curated Moments State
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("curious_mike");
  const [showMomentsModal, setShowMomentsModal] = useState<boolean>(false);
  const [momentSearchQuery, setMomentSearchQuery] = useState<string>("");
  const [momentFilterAngle, setMomentFilterAngle] = useState<string>("all");
  const [curatedMomentsTab, setCuratedMomentsTab] = useState<"moments" | "rules">("moments");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const customVideoInputRef = useRef<HTMLInputElement>(null);
  const masterVideoRef = useRef<HTMLVideoElement>(null);
  const selectedJobIdRef = useRef<string | null>(null);

  useEffect(() => {
    selectedJobIdRef.current = selectedJobId;
  }, [selectedJobId]);

  useEffect(() => {
    return () => {
      if (bgmAudioRef.current) {
        bgmAudioRef.current.pause();
        bgmAudioRef.current = null;
      }
    };
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Fetch Meme templates, SFX catalog, BGM tracks, and Campaigns
  const fetchResources = async () => {
    try {
      const [tRes, sfxRes, bgmRes, campRes] = await Promise.all([
        fetch("/api/memes/templates?limit=120"),
        fetch("/api/sfx-catalog"),
        fetch("/api/bgm/tracks"),
        fetch("/api/campaigns"),
      ]);
      if (tRes.ok) {
        const tData = await tRes.json();
        setMemeTemplates(tData);
      }
      if (sfxRes.ok) {
        const sfxData = await sfxRes.json();
        setSfxCatalog(sfxData);
      }
      if (bgmRes.ok) {
        const bgmData = await bgmRes.json();
        setBgmTracks(bgmData);
      }
      if (campRes.ok) {
        const campData = await campRes.json();
        setCampaigns(campData);
      }
    } catch (e) {
      console.error("Failed to load studio resources:", e);
    }
  };

  useEffect(() => {
    fetchResources();
  }, []);

  const checkHdrStatus = async () => {
    if (!selectedJobId) return;
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}/hdr-status`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "completed") {
          setHdrAvailable(true);
          setIsUpscalingHdr(false);
          setHdrProgress(100);
          setHdrMeta(data.metadata || null);
        } else if (data.status === "converting") {
          setIsUpscalingHdr(true);
          setHdrProgress(data.progress || 0);
          setHdrFps(data.fps || 0);
        } else if (data.status === "error") {
          setIsUpscalingHdr(false);
        } else {
          setIsUpscalingHdr(false);
        }
      }
    } catch (e) {
      console.error("Error checking HDR status:", e);
    }
  };

  useEffect(() => {
    if (selectedJobId) {
      checkHdrStatus();
      setViewingHdrVideo(false);
    }
  }, [selectedJobId]);

  useEffect(() => {
    if (!isUpscalingHdr) return;
    const interval = setInterval(checkHdrStatus, 2000);
    return () => clearInterval(interval);
  }, [isUpscalingHdr, selectedJobId]);

  const handleStartHdrUpscale = async () => {
    if (!selectedJobId) return;
    setIsUpscalingHdr(true);
    setHdrProgress(0);
    showToast(`⚡ Starting SDR2HDR conversion (${hdrScale}x, tone=${hdrTone})...`);
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}/upscale-hdr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          output_scale: hdrScale,
          tone: hdrTone,
          fast_mode: hdrFastMode,
        }),
      });
      if (res.ok) {
        setShowHdrModal(false);
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`SDR2HDR failed: ${err.detail || "Server error"}`);
        setIsUpscalingHdr(false);
      }
    } catch (e) {
      alert("Error triggering SDR2HDR: " + e);
      setIsUpscalingHdr(false);
    }
  };

  const [isAutoGeneratingMeme, setIsAutoGeneratingMeme] = useState<Record<string, boolean>>({});

  const handleAutoGenerateMeme = async (shotId: string) => {
    if (!selectedJob) return;
    setIsAutoGeneratingMeme((prev) => ({ ...prev, [shotId]: true }));
    try {
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/shots/${encodeURIComponent(shotId)}/auto-meme`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        showToast(`AI generated unique meme: ${data.shot?.meme_template || "Meme"}!`);
        const jres = await fetch(`/api/jobs/${encodeURIComponent(selectedJob.job_id)}`);
        if (jres.ok) setSelectedJob(await jres.json());
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Auto-meme generation failed: ${err.detail || "Server error"}`);
      }
    } catch (e) {
      alert("Error auto-generating meme: " + e);
    } finally {
      setIsAutoGeneratingMeme((prev) => ({ ...prev, [shotId]: false }));
    }
  };

  const openMemeCustomizerForShot = (shot: ShotDetail) => {
    setMemeTargetShot(shot);
    setIsStandaloneMode(false);
    setStandaloneMemeResult(null);
    const initialKey = shot.meme_template || "stepped_in_shit";
    setSelectedTemplateKey(initialKey);

    if (shot.meme_captions && Object.keys(shot.meme_captions).length > 0) {
      setMemeCaptions(shot.meme_captions);
    } else {
      const diag = shot.dialogue_quote || "";
      if (initialKey === "stepped_in_shit") {
        setMemeCaptions({ shoe_text: diag || "Bad Opinion / Excuses" });
      } else if (initialKey === "drake") {
        setMemeCaptions({ top_text: "Making Excuses", bottom_text: diag || "Focusing on Goals" });
      } else {
        setMemeCaptions({ caption: diag || "When focus kicks in" });
      }
    }

    if (shot.contextual_sfx?.file) {
      setSelectedSfxFile(shot.contextual_sfx.file);
    } else {
      setSelectedSfxFile(initialKey === "drake" ? "59_cartoon_slip_whoosh.mp3" : "81_vine_boom.mp3");
    }

    setShowMemeModal(true);
  };

  const openStandaloneMemeStudio = () => {
    setMemeTargetShot(null);
    setIsStandaloneMode(true);
    setStandaloneMemeResult(null);
    setSelectedTemplateKey("stepped_in_shit");
    setMemeCaptions({ shoe_text: "Bad Opinion / Terrible Advice" });
    setSelectedSfxFile("81_vine_boom.mp3");
    setShowMemeModal(true);
  };

  const handleSelectTemplate = (tmplKey: string) => {
    setSelectedTemplateKey(tmplKey);
    const currentQuote = memeTargetShot?.dialogue_quote || "";
    if (tmplKey === "stepped_in_shit") {
      setMemeCaptions({ shoe_text: memeCaptions.shoe_text || currentQuote || "Bad Opinion / Excuses" });
      setSelectedSfxFile("81_vine_boom.mp3");
    } else if (tmplKey === "drake") {
      setMemeCaptions({
        top_text: memeCaptions.top_text || "Making Excuses",
        bottom_text: memeCaptions.bottom_text || currentQuote || "Staying Focused"
      });
      setSelectedSfxFile("59_cartoon_slip_whoosh.mp3");
    } else if (tmplKey === "clown") {
      setMemeCaptions({
        step_1: "Thinking it's easy",
        step_2: "Not doing the work",
        step_3: "Complaining about results",
        step_4: "Blaming bad luck"
      });
      setSelectedSfxFile("01_bonk_impact.mp3");
    } else if (tmplKey === "the_trusted_doctor") {
      setMemeCaptions({ caption: memeCaptions.caption || currentQuote || "The specialist she told you not to worry about" });
      setSelectedSfxFile("81_vine_boom.mp3");
    } else if (tmplKey === "gigachad") {
      setMemeCaptions({ caption: memeCaptions.caption || currentQuote || "Average consistency enjoyer" });
      setSelectedSfxFile("55_subtle_bass_drop.mp3");
    } else if (tmplKey === "hide_the_pain_harold") {
      setMemeCaptions({ caption: memeCaptions.caption || currentQuote || "Smiling through the pain" });
      setSelectedSfxFile("11_bruh.mp3");
    } else if (tmplKey === "same_picture") {
      setMemeCaptions({
        item_1: "Procrastination",
        item_2: "Self-Sabotage"
      });
      setSelectedSfxFile("11_bruh.mp3");
    } else {
      setMemeCaptions({ caption: memeCaptions.caption || currentQuote || "When you see the real reason" });
    }
  };

  const handleGenerateMeme = async () => {
    setIsGeneratingMeme(true);
    try {
      if (isStandaloneMode || !memeTargetShot || !selectedJobId) {
        // Standalone render
        const res = await fetch("/api/memes/render", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            template_key: selectedTemplateKey,
            captions: memeCaptions,
            sfx_file: selectedSfxFile,
            duration: 2.0
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setStandaloneMemeResult(data);
          showToast("Meme cutaway video generated successfully!");
        } else {
          const err = await res.json().catch(() => ({}));
          alert(`Meme generation failed: ${err.detail || "Server error"}`);
        }
      } else {
        // Apply to shot
        const shotId = memeTargetShot.shot_id;
        const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}/shots/${encodeURIComponent(shotId)}/meme`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            template_key: selectedTemplateKey,
            captions: memeCaptions,
            sfx_file: selectedSfxFile,
            duration: memeTargetShot.duration ? Math.min(2.0, memeTargetShot.duration) : 1.8
          }),
        });

        if (res.ok) {
          const data = await res.json();
          showToast(`🎭 Meme cutaway applied to Shot ${shotId}!`);
          setShowMemeModal(false);

          // Update local state immediately
          if (selectedJob && selectedJob.edit_plan) {
            const updatedShots = selectedJob.edit_plan.shots.map((s) =>
              s.shot_id === shotId ? { ...s, ...data.shot } : s
            );
            setSelectedJob({
              ...selectedJob,
              edit_plan: {
                ...selectedJob.edit_plan,
                shots: updatedShots
              }
            });
          }
        } else {
          const err = await res.json().catch(() => ({}));
          alert(`Failed to apply meme cutaway: ${err.detail || "Server error"}`);
        }
      }
    } catch (err) {
      alert("Error generating meme: " + err);
    } finally {
      setIsGeneratingMeme(false);
    }
  };

  const handleRerenderMaster = async () => {
    if (!selectedJobId) return;
    setIsRerenderingMaster(true);
    showToast("Saving settings & burning kinetic subtitles + ducked BGM (FFmpeg)...");

    try {
      // 1. Sync latest render settings to backend
      await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subtitles_enabled: subtitlesEnabled,
          subtitle_style: subtitleStyle,
          subtitle_position: subtitlePosition,
          bgm_track_id: selectedBgmId === "none" ? null : selectedBgmId,
          bgm_volume: bgmVolume,
          bgm_ducking: bgmDucking,
          hdr_upscale_enabled: hdrAvailable,
          hdr_output_scale: hdrScale,
          hdr_tone: hdrTone,
        }),
      });

      // 2. Trigger re-render
      const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}/rerender`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (res.ok) {
        showToast("Master video re-rendered with viral subtitles & BGM ducking!");
        if (masterVideoRef.current) {
          masterVideoRef.current.load();
        }
        fetchData();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to re-render: ${err.detail || "Server error"}`);
      }
    } catch (err) {
      alert("Error re-rendering: " + err);
    } finally {
      setIsRerenderingMaster(false);
    }
  };

  const handleExportToOpenReel = async () => {
    if (!selectedJob || !selectedJob.edit_plan) {
      alert("No active edit plan to export to OpenReel.");
      return;
    }
    setIsOpenReelExporting(true);
    showToast("Exporting non-destructive OpenReel project (.oreel)...");
    try {
      const res = await fetch("/api/export-openreel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          edit_plan: selectedJob.edit_plan,
          project_name: selectedJob.filename || "Stockpile Edit",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setOpenReelModalData(data);
        showToast("🎬 Project exported to OpenReel Schema 1.2.0!");
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Export failed: ${err.detail || "Server error"}`);
      }
    } catch (e) {
      alert("Error exporting to OpenReel: " + e);
    } finally {
      setIsOpenReelExporting(false);
    }
  };

  const handleUpdateSettings = async (partial: {
    subtitles_enabled?: boolean;
    subtitle_style?: string;
    subtitle_position?: string;
    bgm_track_id?: string | null;
    bgm_volume?: number;
    bgm_ducking?: boolean;
  }) => {
    if (!selectedJobId) return;
    setIsSavingSettings(true);
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(partial),
      });
      if (res.ok) {
        showToast("Settings updated! Click Re-render to burn in.");
      }
    } catch (e) {
      console.error("Error saving settings:", e);
    } finally {
      setIsSavingSettings(false);
    }
  };

  const toggleBgmPreview = (trackId: string) => {
    if (playingBgmPreview === trackId) {
      if (bgmAudioRef.current) {
        bgmAudioRef.current.pause();
      }
      setPlayingBgmPreview(null);
    } else {
      if (bgmAudioRef.current) {
        bgmAudioRef.current.pause();
      }
      const audio = new Audio(`/api/bgm/${encodeURIComponent(trackId)}/audio`);
      audio.volume = Math.min(1.0, bgmVolume * 2.5);
      audio.play().catch((e) => console.error("BGM audio play error:", e));
      audio.onended = () => setPlayingBgmPreview(null);
      bgmAudioRef.current = audio;
      setPlayingBgmPreview(trackId);
    }
  };

  const handleTrimShot = async (shotId: string, newStart: number, newEnd: number) => {
    if (!selectedJobId) return;
    const clampedStart = Math.max(0, Math.round(newStart * 10) / 10);
    const clampedEnd = Math.max(clampedStart + 0.3, Math.round(newEnd * 10) / 10);

    setIsTrimming((prev) => ({ ...prev, [shotId]: true }));
    try {
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(selectedJobId)}/shots/${encodeURIComponent(shotId)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            start_time: clampedStart,
            end_time: clampedEnd,
          }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        showToast(`Trimmed Cutaway: ${clampedStart}s → ${clampedEnd}s`);
        if (selectedJob && selectedJob.edit_plan) {
          setSelectedJob({
            ...selectedJob,
            edit_plan: {
              ...selectedJob.edit_plan,
              shots: data.shots,
            },
          });
        }
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(`Trim failed: ${err.detail || "Invalid timestamp"}`);
      }
    } catch (err) {
      console.error("Error trimming shot:", err);
    } finally {
      setIsTrimming((prev) => ({ ...prev, [shotId]: false }));
    }
  };

  const handleDeleteShot = async (shotId: string) => {
    if (!selectedJobId) return;
    if (!confirm(`Are you sure you want to remove Cutaway ${shotId}?`)) return;

    try {
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(selectedJobId)}/shots/${encodeURIComponent(shotId)}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        showToast(`Removed Cutaway ${shotId}`);
        if (selectedJob && selectedJob.edit_plan) {
          setSelectedJob({
            ...selectedJob,
            edit_plan: {
              ...selectedJob.edit_plan,
              shots: selectedJob.edit_plan.shots.filter((s) => s.shot_id !== shotId),
            },
          });
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to delete cutaway: ${err.detail || "Server error"}`);
      }
    } catch (err) {
      alert("Error deleting cutaway: " + err);
    }
  };

  const openInsertCutawayAtCurrentTime = () => {
    setInsertCutawayTime(Math.round(currentTime * 10) / 10);
    setInsertCutawayDur(2.5);
    setInsertCutawayStyle("stockpile");
    setInsertCutawayPrompt("focused professional working");
    setInsertCutawayMemeTemplate("stepped_in_shit");
    setShowInsertCutawayModal(true);
  };

  const handleConfirmInsertCutaway = async () => {
    if (!selectedJobId) return;
    setIsInsertingCutaway(true);
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}/shots`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_time: insertCutawayTime,
          duration: insertCutawayDur,
          style: insertCutawayStyle,
          search_prompt: insertCutawayPrompt,
          meme_template: insertCutawayMemeTemplate,
          dialogue_quote: insertCutawayPrompt,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`✨ Added new ${insertCutawayStyle === "meme" ? "Meme" : "Stock"} Cutaway at ${insertCutawayTime.toFixed(1)}s!`);
        setShowInsertCutawayModal(false);
        if (selectedJob && selectedJob.edit_plan) {
          setSelectedJob({
            ...selectedJob,
            edit_plan: {
              ...selectedJob.edit_plan,
              shots: data.shots,
            },
          });
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to insert cutaway: ${err.detail || "Server error"}`);
      }
    } catch (err) {
      alert("Error inserting cutaway: " + err);
    } finally {
      setIsInsertingCutaway(false);
    }
  };

  const openSwapModalForShot = (shot: ShotDetail) => {
    setSwapTargetShot(shot);
    setSwapTab("search");
    const initQuery = shot.asset_title || shot.dialogue_quote || "focused professional";
    setSwapSearchQuery(initQuery);
    setShowSwapModal(true);
    handleSearchStock(initQuery);
  };

  const handleSearchStock = async (query: string) => {
    if (!query.trim()) return;
    setIsSearchingStock(true);
    try {
      const res = await fetch(`/api/stock/search?query=${encodeURIComponent(query.trim())}`);
      if (res.ok) {
        const data = await res.json();
        setStockCandidates(data);
      }
    } catch (e) {
      console.error("Failed to search stock footage:", e);
    } finally {
      setIsSearchingStock(false);
    }
  };

  const handleSelectStockCandidate = async (cand: StockVideoCandidate) => {
    if (!selectedJobId || !swapTargetShot) return;
    setIsSwappingStock(true);
    try {
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(selectedJobId)}/shots/${encodeURIComponent(swapTargetShot.shot_id)}/swap-stock`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            download_url: cand.download_url,
            prompt: swapSearchQuery,
          }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        showToast(`Replaced footage for Cutaway ${swapTargetShot.shot_id}!`);
        setShowSwapModal(false);
        if (selectedJob && selectedJob.edit_plan) {
          const updated = selectedJob.edit_plan.shots.map((s) =>
            s.shot_id === swapTargetShot.shot_id ? { ...s, ...data.shot } : s
          );
          setSelectedJob({
            ...selectedJob,
            edit_plan: { ...selectedJob.edit_plan, shots: updated },
          });
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to swap stock footage: ${err.detail || "Server error"}`);
      }
    } catch (err) {
      alert("Error swapping footage: " + err);
    } finally {
      setIsSwappingStock(false);
    }
  };

  const handleCustomVideoUpload = async (file: File) => {
    if (!selectedJobId || !swapTargetShot) return;
    setIsUploadingCustom(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(selectedJobId)}/shots/${encodeURIComponent(swapTargetShot.shot_id)}/upload-custom`,
        {
          method: "POST",
          body: fd,
        }
      );
      if (res.ok) {
        const data = await res.json();
        showToast(`Custom clip applied to Cutaway ${swapTargetShot.shot_id}!`);
        setShowSwapModal(false);
        if (selectedJob && selectedJob.edit_plan) {
          const updated = selectedJob.edit_plan.shots.map((s) =>
            s.shot_id === swapTargetShot.shot_id ? { ...s, ...data.shot } : s
          );
          setSelectedJob({
            ...selectedJob,
            edit_plan: { ...selectedJob.edit_plan, shots: updated },
          });
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Custom clip upload failed: ${err.detail || "Server error"}`);
      }
    } catch (err) {
      alert("Error uploading custom footage: " + err);
    } finally {
      setIsUploadingCustom(false);
    }
  };

  // Import YouTube Video
  const handleYouTubeImport = async () => {
    if (!youtubeUrl.trim()) return;
    setIsImportingYouTube(true);
    showToast("Connecting to YouTube & downloading video stream...");

    try {
      const res = await fetch("/api/jobs/youtube", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: youtubeUrl.trim(),
          campaign_id: selectedCampaignId,
        }),
      });

      if (res.ok) {
        const result = await res.json();
        setSelectedJobId(result.job_id);
        setShowUploadMode(false);
        setYoutubeUrl("");
        showToast("YouTube video imported! B-roll autopilot running...");
        fetchData();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(`YouTube import failed: ${errData.detail || "Could not access or download YouTube video"}`);
      }
    } catch (err) {
      alert("Error importing YouTube video: " + err);
    } finally {
      setIsImportingYouTube(false);
    }
  };

  // Fetch jobs & stats
  const fetchData = async () => {
    try {
      const [jobsRes, statsRes] = await Promise.all([
        fetch("/api/jobs"),
        fetch("/api/stats")
      ]);
      if (jobsRes.ok) {
        const data: JobSummary[] = await jobsRes.json();
        setJobs(data);

        // Prefer 0914(6) which has hybrid meme cutaways
        if (!selectedJobIdRef.current && data.length > 0) {
          const preferred =
            data.find((j) => j.status === "COMPLETED" && j.filename.includes("0914(6)")) ||
            data.find((j) => j.status === "COMPLETED" && j.filename.includes("0914(1)")) ||
            data.find((j) => j.status === "COMPLETED") ||
            data[0];
          setSelectedJobId(preferred.job_id);
        } else if (data.length === 0) {
          setShowUploadMode(true);
        }
      }
      if (statsRes.ok) {
        const sdata = await statsRes.json();
        setStats(sdata);
      }
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  // Fetch selected job detail
  useEffect(() => {
    if (!selectedJobId) return;
    let isMounted = true;

    const fetchDetail = async () => {
      try {
        const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}`);
        if (res.ok && isMounted) {
          const detail = await res.json();
          setSelectedJob(detail);
          setFeedbackSubmitted(false);
          if (detail.edit_plan?.render_settings) {
            const rs = detail.edit_plan.render_settings;
            if (rs.subtitles_enabled !== undefined) setSubtitlesEnabled(rs.subtitles_enabled);
            if (rs.subtitle_style) setSubtitleStyle(rs.subtitle_style);
            if (rs.subtitle_position) setSubtitlePosition(rs.subtitle_position);
            if (rs.bgm_track_id !== undefined) setSelectedBgmId(rs.bgm_track_id || "none");
            if (rs.bgm_volume !== undefined) setBgmVolume(rs.bgm_volume);
            if (rs.bgm_ducking !== undefined) setBgmDucking(rs.bgm_ducking);
          }
        }
      } catch (err) {
        console.error("Failed to fetch job detail:", err);
      }
    };

    fetchDetail();
    const detailInterval = setInterval(() => {
      if (selectedJob?.status && selectedJob.status !== "COMPLETED" && selectedJob.status !== "FAILED") {
        fetchDetail();
      }
    }, 2500);

    return () => {
      isMounted = false;
      clearInterval(detailInterval);
    };
  }, [selectedJobId, selectedJob?.status]);

  // Track master video time for interactive timeline
  const handleTimeUpdate = () => {
    if (masterVideoRef.current) {
      setCurrentTime(masterVideoRef.current.currentTime);
    }
  };

  // Jump to specific cutaway in master video
  const jumpToCutaway = (startTime: number) => {
    if (masterVideoRef.current) {
      masterVideoRef.current.currentTime = startTime;
      masterVideoRef.current.play();
    }
  };

  // Single Clip File Upload Handler
  const handleFileUpload = async (file: File) => {
    if (!file) return;
    setIsUploading(true);
    setUploadProgress(25);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("campaign_id", selectedCampaignId);

    try {
      setUploadProgress(50);
      const res = await fetch("/api/jobs/upload", {
        method: "POST",
        body: formData,
      });
      setUploadProgress(100);
      if (res.ok) {
        const result = await res.json();
        setSelectedJobId(result.job_id);
        setShowUploadMode(false);
        showToast(`Uploaded ${file.name} - Autopilot pipeline running!`);
        fetchData();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(`Upload failed: ${errData.detail || "Please ensure the file is a valid video (MP4, MOV, MKV, WebM)."}`);
      }
    } catch (err) {
      alert("Error uploading video: " + err);
    } finally {
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 600);
    }
  };

  // Execute Job Deletion
  const executeDeleteJob = async (jobId: string) => {
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast("Project deleted successfully");
        const remaining = jobs.filter((j) => j.job_id !== jobId);
        setJobs(remaining);
        if (remaining.length > 0) {
          setSelectedJobId(remaining[0].job_id);
        } else {
          setSelectedJobId(null);
          setSelectedJob(null);
          setShowUploadMode(true);
        }
      } else {
        alert("Failed to delete project");
      }
    } catch (err) {
      alert("Error deleting project: " + err);
    } finally {
      setJobToDelete(null);
    }
  };

  // Execute Clear All Projects
  const executeClearAll = async () => {
    try {
      const res = await fetch("/api/jobs/clear", { method: "POST" });
      if (res.ok) {
        showToast("All projects cleared from studio library");
        setJobs([]);
        setSelectedJobId(null);
        setSelectedJob(null);
        setShowUploadMode(true);
        setShowProjectPicker(false);
      } else {
        alert("Failed to clear library");
      }
    } catch (err) {
      alert("Error clearing library: " + err);
    } finally {
      setShowClearAllModal(false);
    }
  };

  // Submit Feedback
  const handleSubmitFeedback = async () => {
    if (!selectedJobId || !feedbackText.trim()) return;

    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: selectedJobId,
          rating: feedbackRating,
          feedback: feedbackText,
          thematic_category: "Emotional Metaphor",
        }),
      });

      if (res.ok) {
        setFeedbackSubmitted(true);
        setFeedbackText("");
        showToast("Feedback saved to SQLite! Engine learned your preference.");
        fetchData();
      }
    } catch (err) {
      alert("Failed to submit feedback: " + err);
    }
  };

  const isProcessing = selectedJob && selectedJob.status !== "COMPLETED" && selectedJob.status !== "FAILED";
  const totalDuration = selectedJob?.edit_plan?.total_duration || 12;
  const shots = selectedJob?.edit_plan?.shots || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-indigo-600 text-white text-xs font-semibold px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 border border-indigo-400 animate-bounce">
          <CheckCircle2 className="w-4 h-4 text-emerald-300" />
          {toastMessage}
        </div>
      )}

      {/* CONFIRMATION MODAL: Single Project Delete */}
      {jobToDelete && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4 text-center">
            <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto border border-rose-500/20">
              <Trash2 className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-white">Delete Project?</h3>
              <p className="text-xs text-zinc-400">
                Are you sure you want to permanently delete <strong className="text-zinc-200">"{jobToDelete.name}"</strong>? This will remove the rendered video, audio, and cutaways.
              </p>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setJobToDelete(null)}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold py-2.5 rounded-xl transition-colors border border-zinc-700/60"
              >
                Cancel
              </button>
              <button
                onClick={() => executeDeleteJob(jobToDelete.id)}
                className="flex-1 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold py-2.5 rounded-xl transition-colors shadow-lg shadow-rose-600/30 flex items-center justify-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CONFIRMATION MODAL: Clear All Projects */}
      {showClearAllModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6 max-w-md w-full shadow-2xl space-y-4 text-center">
            <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto border border-rose-500/20">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-white">Clear All Projects?</h3>
              <p className="text-xs text-zinc-400">
                This will delete all saved edits and history from your studio database and free up disk space.
              </p>
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={() => setShowClearAllModal(false)}
                className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold py-2.5 rounded-xl transition-colors border border-zinc-700/60"
              >
                Cancel
              </button>
              <button
                onClick={executeClearAll}
                className="flex-1 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold py-2.5 rounded-xl transition-colors shadow-lg shadow-rose-600/30 flex items-center justify-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Yes, Clear All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top Navigation Bar: Single-Clip Studio Header */}
      <div className="bg-zinc-900/80 border border-zinc-800/90 rounded-2xl p-4 backdrop-blur-md flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white shadow-md">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-zinc-100 tracking-tight">AI B-Roll Autopilot</h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full">
                Single-Clip Studio
              </span>
            </div>
            <p className="text-xs text-zinc-400">
              One video at a time • Autonomous AI Memes (Speed, Johnny Sins, CaseOh) • Stockpile footage • 9:16 vertical
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
          {/* Campaign Preset Selector */}
          <div className="flex items-center gap-1.5 bg-zinc-950/90 border border-zinc-800 p-1 rounded-xl shadow-inner">
            <div className="flex items-center gap-1 px-1.5 py-0.5">
              <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Campaign:</span>
              <select
                value={selectedCampaignId}
                onChange={(e) => setSelectedCampaignId(e.target.value)}
                className="bg-zinc-900 border border-zinc-700/80 rounded-lg text-xs font-semibold text-zinc-100 px-2.5 py-1 focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.id === "curious_mike" ? "🎯 Curious Mike ($1.25/1k)" : `⚡ ${c.name}`}
                  </option>
                ))}
                {campaigns.length === 0 && (
                  <>
                    <option value="curious_mike">🎯 Curious Mike ($1.25/1k)</option>
                    <option value="default">⚡ Default Viral Shorts</option>
                  </>
                )}
              </select>
            </div>
            {selectedCampaignId === "curious_mike" && (
              <button
                type="button"
                onClick={() => setShowMomentsModal(true)}
                className="bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all"
                title="Browse 50 pre-curated timestamped moments and 6 rules"
              >
                <Sparkles className="w-3 h-3 text-emerald-400" />
                <span>50 Moments & Rules</span>
              </button>
            )}
          </div>

          {/* Active Clip Switcher */}
          {jobs.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setShowProjectPicker(!showProjectPicker)}
                className="bg-zinc-800/80 hover:bg-zinc-700/80 text-zinc-200 text-xs font-medium px-3.5 py-2 rounded-xl border border-zinc-700/70 flex items-center gap-2 transition-all"
              >
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span className="max-w-[160px] truncate">
                  {selectedJob ? selectedJob.filename : "Select Project"}
                </span>
                <ChevronRight className={`w-3.5 h-3.5 transition-transform ${showProjectPicker ? "rotate-90" : ""}`} />
              </button>

              {/* Project Picker Dropdown */}
              {showProjectPicker && (
                <div className="absolute right-0 mt-2 w-80 bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl p-2.5 z-50 space-y-1">
                  <div className="flex items-center justify-between px-2 py-1 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                    <span>Saved Projects ({jobs.length})</span>
                    <button
                      onClick={() => setShowClearAllModal(true)}
                      className="text-rose-400 hover:text-rose-300 text-[10px] flex items-center gap-1 font-medium hover:underline"
                    >
                      <Trash2 className="w-3 h-3" /> Clear All
                    </button>
                  </div>

                  <div className="max-h-60 overflow-y-auto space-y-1 pr-1">
                    {jobs.map((j) => (
                      <div
                        key={j.job_id}
                        className={`p-2 rounded-xl text-xs flex items-center justify-between transition-colors group ${
                          j.job_id === selectedJobId
                            ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                            : "hover:bg-zinc-800/90 text-zinc-300 border border-transparent"
                        }`}
                      >
                        <div
                          onClick={() => {
                            setSelectedJobId(j.job_id);
                            setShowUploadMode(false);
                            setShowProjectPicker(false);
                          }}
                          className="truncate flex-1 cursor-pointer pr-2"
                        >
                          <p className="font-semibold truncate">{j.filename}</p>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="text-[10px] text-zinc-500">
                              {j.filename.includes("0914(1)") ? "2 B-Roll Cuts" : j.status}
                            </span>
                            <span className={`text-[9px] px-1.5 py-0.2 rounded font-medium ${getStatusColor(j.status)}`}>
                              {j.status}
                            </span>
                          </div>
                        </div>

                        {/* Direct Delete Button in Row */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setJobToDelete({ id: j.job_id, name: j.filename });
                          }}
                          title={`Delete ${j.filename}`}
                          className="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors shrink-0"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Main Top Navigation Tabs */}
          <div className="flex items-center bg-zinc-950 p-1 rounded-xl border border-zinc-800">
            <button
              type="button"
              onClick={() => {
                setShowUploadMode(true);
                setShowProjectPicker(false);
              }}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                showUploadMode || !selectedJob
                  ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Video</span>
            </button>
            {selectedJob && (
              <button
                type="button"
                onClick={() => {
                  setShowUploadMode(false);
                  setShowProjectPicker(false);
                }}
                className={`text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                  !showUploadMode
                    ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Film className="w-3.5 h-3.5" />
                <span>Editor & Cutaways</span>
              </button>
            )}
          </div>

          {/* Re-render Master Video Button */}
          {selectedJob && !showUploadMode && (
            <button
              onClick={handleRerenderMaster}
              disabled={isRerenderingMaster}
              className="bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/40 text-xs font-semibold px-3.5 py-2 rounded-xl flex items-center gap-1.5 transition-all shadow-sm"
              title="Re-render master video compositing with updated meme cutaways & Foley SFX"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-amber-400 ${isRerenderingMaster ? "animate-spin" : ""}`} />
              <span>{isRerenderingMaster ? "Rendering..." : "Re-render Master"}</span>
            </button>
          )}

          {/* Prominent Header Delete Button */}
          {selectedJob && !showUploadMode && (
            <button
              onClick={() => setJobToDelete({ id: selectedJob.job_id, name: selectedJob.filename })}
              title="Delete this project"
              className="bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold px-3 py-2 rounded-xl flex items-center gap-1.5 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete Edit</span>
            </button>
          )}
        </div>
      </div>

      {/* VIEW 1: UPLOAD SCREEN (Single Clip Dropzone) */}
      {(showUploadMode || !selectedJob) && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-10 text-center space-y-6 shadow-2xl backdrop-blur-sm">
          <div className="max-w-xl mx-auto space-y-2">
            <h2 className="text-2xl font-extrabold text-zinc-100 tracking-tight">Drop 1 Video Clip to Begin</h2>
            <p className="text-sm text-zinc-400">
              The AI autopilot will transcribe dialogue, extract emotional themes, source B-roll cutaways, and render a complete 9:16 vertical video.
            </p>
          </div>

          {/* Active Campaign Rules Banner */}
          {selectedCampaignId === "curious_mike" ? (
            <div className="max-w-2xl mx-auto bg-gradient-to-r from-zinc-950 via-emerald-950/20 to-zinc-950 border border-emerald-500/30 rounded-3xl p-5 text-left shadow-xl space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-lg shadow-inner">
                    🎯
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-white">Curious Mike Clipping Campaign</h3>
                      <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full">
                        $1.25 / 1k views • $7.5k Budget
                      </span>
                    </div>
                    <p className="text-xs text-zinc-400">
                      Client: Michael Porter Jr. • Trae Young Episode • 2,000 views min to qualify ($2.50 - $300/clip)
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowMomentsModal(true)}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3.5 py-2 rounded-xl shadow-md shadow-emerald-600/25 transition-all flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>50 Curated Moments & Rules</span>
                </button>
              </div>

              {/* 6 Campaign Rules Checklist Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 pt-2 border-t border-zinc-800/80">
                <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2 text-center">
                  <div className="text-[11px] font-bold text-emerald-400">Rule 1: Geo</div>
                  <div className="text-[10px] text-zinc-400">40%+ US/CA/UK</div>
                </div>
                <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2 text-center">
                  <div className="text-[11px] font-bold text-emerald-400">Rule 2: Hook</div>
                  <div className="text-[10px] text-zinc-400">1%+ Engagement</div>
                </div>
                <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2 text-center">
                  <div className="text-[11px] font-bold text-emerald-400">Rule 3: Real B-roll</div>
                  <div className="text-[10px] text-zinc-400">0% AI Video (Max 33%)</div>
                </div>
                <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2 text-center">
                  <div className="text-[11px] font-bold text-emerald-400">Rule 4: Audio</div>
                  <div className="text-[10px] text-zinc-400">Dialogue Only (No BGM)</div>
                </div>
                <div className="bg-zinc-900/90 border border-zinc-800 rounded-xl p-2 text-center">
                  <div className="text-[11px] font-bold text-emerald-400">Rule 5: Subtitles</div>
                  <div className="text-[10px] text-zinc-400">Word-by-word Clean</div>
                </div>
                <div className="bg-emerald-950/40 border border-emerald-500/40 rounded-xl p-2 text-center">
                  <div className="text-[11px] font-bold text-emerald-300">Rule 6: Watermark</div>
                  <div className="text-[10px] text-emerald-400 font-mono">YT: @mpj (100%)</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto bg-zinc-950/70 border border-zinc-800 rounded-2xl p-3.5 text-left flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <span className="text-lg">⚡</span>
                <div>
                  <h4 className="text-xs font-bold text-zinc-200">Default Viral Short-Form Preset</h4>
                  <p className="text-[11px] text-zinc-400">
                    High-velocity meme hooks (Speed, CaseOh, Jynxzi), phonk BGM with voice ducking, Hormozi kinetic captions.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCampaignId("curious_mike")}
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 shrink-0 underline"
              >
                Switch to Curious Mike Campaign →
              </button>
            </div>
          )}

          {/* Tab Selector: Upload File vs Import YouTube */}
          <div className="flex items-center justify-center gap-2 max-w-md mx-auto bg-zinc-950 p-1.5 rounded-2xl border border-zinc-800">
            <button
              type="button"
              onClick={() => setUploadTab("file")}
              className={`flex-1 py-2 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                uploadTab === "file"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              Upload Local Video
            </button>
            <button
              type="button"
              onClick={() => setUploadTab("youtube")}
              className={`flex-1 py-2 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                uploadTab === "youtube"
                  ? "bg-rose-600 text-white shadow-md shadow-rose-600/20"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Link2 className="w-3.5 h-3.5" />
              Import YouTube URL
            </button>
          </div>

          {uploadTab === "file" ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDraggingFile(true);
              }}
              onDragEnter={(e) => {
                e.preventDefault();
                setIsDraggingFile(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setIsDraggingFile(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setIsDraggingFile(false);
                if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`max-w-2xl mx-auto border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer transition-all group shadow-inner ${
                isDraggingFile
                  ? "border-indigo-400 bg-indigo-500/20 scale-[1.01]"
                  : "border-indigo-500/40 hover:border-indigo-400 bg-indigo-500/5 hover:bg-indigo-500/10"
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                accept="video/*,.mp4,.mov,.mkv,.webm,.avi"
                className="hidden"
                onClick={(e) => {
                  e.stopPropagation();
                  (e.target as HTMLInputElement).value = "";
                }}
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
                }}
              />
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform shadow-lg">
                <Upload className="w-8 h-8" />
              </div>
              <h3 className="font-bold text-base text-zinc-100">Drop your raw MP4 or MOV here</h3>
              <p className="text-xs text-zinc-400 mt-1.5">Single-clip pipeline • Up to 500MB • Zero watermarks guarantee</p>

              <div className="mt-4">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition-all shadow-md shadow-indigo-600/20 inline-flex items-center gap-2"
                >
                  <Upload className="w-4 h-4" />
                  Browse Files
                </button>
              </div>

              {isUploading && (
                <div className="mt-6 max-w-sm mx-auto space-y-2">
                  <div className="w-full bg-zinc-800 rounded-full h-2 overflow-hidden">
                    <div className="bg-indigo-500 h-2 transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                  </div>
                  <p className="text-xs text-indigo-400 animate-pulse">Uploading and launching pipeline...</p>
                </div>
              )}
            </div>
          ) : (
            <div className="max-w-2xl mx-auto bg-zinc-950 border border-zinc-800/90 rounded-3xl p-8 space-y-5 text-left shadow-inner">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 flex items-center justify-center border border-rose-500/20 shadow-md">
                  <Video className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-zinc-100">Import Video from YouTube or Shorts</h3>
                  <p className="text-xs text-zinc-400">
                    Paste a link to any YouTube speech, podcast clip, or short video to auto-cut B-rolls.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="relative">
                  <input
                    type="url"
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                    placeholder="https://www.youtube.com/watch?v=... or https://youtube.com/shorts/..."
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl px-4 py-3.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleYouTubeImport();
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-zinc-500 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-amber-400" />
                    Powered by yt-dlp & Whisper AI Transcription
                  </span>
                  <button
                    onClick={handleYouTubeImport}
                    disabled={isImportingYouTube || !youtubeUrl.trim()}
                    className={`bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-semibold px-5 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-rose-600/20 transition-all ${
                      isImportingYouTube ? "animate-pulse" : "hover:scale-[1.02]"
                    }`}
                  >
                    {isImportingYouTube ? (
                      <>
                        <Clock className="w-3.5 h-3.5 animate-spin" />
                        Downloading Stream...
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-white" />
                        Fetch & Auto-Generate B-Rolls
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Quick return button if an active project exists */}
          {selectedJob && (
            <button
              onClick={() => setShowUploadMode(false)}
              className="text-xs text-zinc-400 hover:text-zinc-200 underline font-medium pt-2"
            >
              ← Cancel & return to active project: <strong>{selectedJob.filename}</strong>
            </button>
          )}
        </div>
      )}

      {/* VIEW 2: PROCESSING SCREEN (Single Clip Progress HUD) */}
      {!showUploadMode && isProcessing && selectedJob && (
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-3xl p-8 space-y-8 shadow-2xl backdrop-blur-md">
          <div className="text-center space-y-2 max-w-lg mx-auto">
            <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full text-xs text-amber-400 font-semibold mb-2">
              <Clock className="w-3.5 h-3.5 animate-spin" />
              Pipeline In Progress
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">Editing "{selectedJob.filename}"</h2>
            <p className="text-xs text-zinc-400">Processing stages: Whisper Speech Analysis $\to$ Emotional Director $\to$ Stockpile B-Roll $\to$ Composition</p>
          </div>

          {/* Large Progress Bar */}
          <div className="max-w-2xl mx-auto space-y-2">
            <div className="flex justify-between text-xs text-zinc-400 font-medium">
              <span>Overall Progress</span>
              <span className="text-indigo-400 font-bold">{Math.round(selectedJob.progress * 100)}%</span>
            </div>
            <div className="w-full bg-zinc-800/80 rounded-full h-2.5 overflow-hidden border border-zinc-700/50">
              <div
                className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 h-2.5 transition-all duration-500"
                style={{ width: `${Math.round(selectedJob.progress * 100)}%` }}
              />
            </div>
          </div>

          {/* Stage Breakdown Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto">
            <div className={`p-4 rounded-xl border ${selectedJob.progress >= 0.2 ? "bg-indigo-600/10 border-indigo-500/40 text-white" : "bg-zinc-900/40 border-zinc-800/60 text-zinc-500"}`}>
              <div className="text-xs font-bold mb-1">1. Transcription</div>
              <p className="text-[11px] text-zinc-400">Whisper converts speech to timed word segments</p>
            </div>
            <div className={`p-4 rounded-xl border ${selectedJob.progress >= 0.4 ? "bg-indigo-600/10 border-indigo-500/40 text-white" : "bg-zinc-900/40 border-zinc-800/60 text-zinc-500"}`}>
              <div className="text-xs font-bold mb-1">2. Emotional Director</div>
              <p className="text-[11px] text-zinc-400">Gemini extracts visceral metaphors & micro-prompts</p>
            </div>
            <div className={`p-4 rounded-xl border ${selectedJob.progress >= 0.7 ? "bg-indigo-600/10 border-indigo-500/40 text-white" : "bg-zinc-900/40 border-zinc-800/60 text-zinc-500"}`}>
              <div className="text-xs font-bold mb-1">3. B-Roll Assembly</div>
              <p className="text-[11px] text-zinc-400">Rapid-fire montages composited & verified clean</p>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 3: COMPLETED SINGLE-CLIP STUDIO */}
      {!showUploadMode && !isProcessing && selectedJob && (
        <div className="space-y-6">
          {/* CLIPPER REFINEMENT TOOLBAR: Viral Kinetic Subtitles & Auto-Ducking BGM */}
          <div className="bg-gradient-to-r from-zinc-900 via-zinc-900/90 to-zinc-900 border border-indigo-500/30 rounded-3xl p-5 shadow-2xl space-y-4 backdrop-blur-md">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-white shadow-md">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-white">Clipper Video Studio</h3>
                    {selectedJob.campaign_id === "curious_mike" ? (
                      <span className="text-[9px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full flex items-center gap-1">
                        🎯 Curious Mike Compliant
                      </span>
                    ) : (
                      <span className="text-[9px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full">
                        Viral Ready
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    {selectedJob.campaign_id === "curious_mike"
                      ? "YT: @mpj Watermark Burned • Subtitle Safe-Zone Offset • Pure Dialogue (No BGM) • Real Footage Only"
                      : "Alex Hormozi kinetic word-highlights • Royalty-Free BGM library • Voice sidechain auto-ducking"}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2.5">
                {/* SDR2HDR Upscale & HDR10 Button */}
                <button
                  onClick={() => setShowHdrModal(true)}
                  className={`border text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all hover:scale-[1.02] ${
                    hdrAvailable
                      ? "bg-gradient-to-r from-purple-600 via-pink-600 to-rose-600 text-white border-pink-400 shadow-pink-600/30"
                      : isUpscalingHdr
                      ? "bg-purple-900/60 text-purple-200 border-purple-500 animate-pulse"
                      : "bg-zinc-800/90 hover:bg-zinc-700 text-zinc-100 border-zinc-700 shadow-zinc-900/50"
                  }`}
                  title="Upscale to 4K / Convert to 10-bit Rec.2020 HDR10 with AI"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${isUpscalingHdr ? "animate-spin text-pink-300" : "text-amber-300"}`} />
                  <span>
                    {isUpscalingHdr
                      ? `⚡ SDR2HDR: ${hdrProgress.toFixed(0)}%`
                      : hdrAvailable
                      ? "✨ HDR10 Active (Options)"
                      : "⚡ SDR2HDR Upscale"}
                  </span>
                </button>

                {/* Re-render Master Button */}
                <button
                  onClick={handleRerenderMaster}
                  disabled={isRerenderingMaster}
                  className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 disabled:opacity-50 text-black text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02]"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isRerenderingMaster ? "animate-spin" : ""}`} />
                  <span>{isRerenderingMaster ? "Burning Subtitles & BGM..." : "⚡ Re-render Master Edit"}</span>
                </button>

                {/* Open in OpenReel Button */}
                <button
                  onClick={handleExportToOpenReel}
                  disabled={isOpenReelExporting}
                  className="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
                  title="Export non-destructive multitrack project to OpenReel Schema 1.2.0 (.oreel)"
                >
                  <Film className={`w-3.5 h-3.5 ${isOpenReelExporting ? "animate-spin" : ""}`} />
                  <span>{isOpenReelExporting ? "Exporting OpenReel..." : "🎬 Open in OpenReel"}</span>
                </button>
              </div>
            </div>

            {/* Settings Grid: Subtitles (Left) + BGM Engine (Right) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* 1. Viral Kinetic Subtitles Panel */}
              <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Type className="w-4 h-4 text-amber-400" />
                    <span className="text-xs font-bold text-zinc-200 uppercase tracking-wider">
                      Viral Kinetic Subtitles
                    </span>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer text-xs">
                    <span className="text-[11px] text-zinc-400">{subtitlesEnabled ? "Enabled" : "Off"}</span>
                    <input
                      type="checkbox"
                      checked={subtitlesEnabled}
                      onChange={(e) => {
                        setSubtitlesEnabled(e.target.checked);
                        handleUpdateSettings({ subtitles_enabled: e.target.checked });
                      }}
                      className="w-4 h-4 accent-amber-500 rounded cursor-pointer"
                    />
                  </label>
                </div>

                {subtitlesEnabled && (
                  <div className="space-y-3 pt-1">
                    {/* Style Presets */}
                    <div className="space-y-1">
                      <label className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">Highlight Style</label>
                      <div className="grid grid-cols-3 gap-2">
                        {[
                          { key: "hormozi", name: "🟡 Hormozi", desc: "Yellow Punch" },
                          { key: "mrbeast", name: "🟢 MrBeast", desc: "Neon Green" },
                          { key: "clean", name: "⚪ Clean", desc: "White Minimal" },
                        ].map((preset) => (
                          <button
                            key={preset.key}
                            onClick={() => {
                              setSubtitleStyle(preset.key);
                              handleUpdateSettings({ subtitle_style: preset.key });
                            }}
                            className={`p-2 rounded-xl text-left border transition-all ${
                              subtitleStyle === preset.key
                                ? "bg-amber-500/15 border-amber-500/50 text-white shadow-sm"
                                : "bg-zinc-900/80 hover:bg-zinc-800/80 text-zinc-400 border-zinc-800"
                            }`}
                          >
                            <div className="text-xs font-bold">{preset.name}</div>
                            <div className="text-[10px] text-zinc-500">{preset.desc}</div>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Position Picker */}
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] text-zinc-400">Subtitle Position:</span>
                      <div className="flex items-center gap-1.5 bg-zinc-900 p-1 rounded-xl border border-zinc-800">
                        <button
                          onClick={() => {
                            setSubtitlePosition("bottom");
                            handleUpdateSettings({ subtitle_position: "bottom" });
                          }}
                          className={`text-[10px] font-bold px-2.5 py-1 rounded-lg transition-all ${
                            subtitlePosition === "bottom"
                              ? "bg-amber-500 text-black shadow-sm"
                              : "text-zinc-400 hover:text-zinc-200"
                          }`}
                        >
                          Bottom
                        </button>
                        <button
                          onClick={() => {
                            setSubtitlePosition("center");
                            handleUpdateSettings({ subtitle_position: "center" });
                          }}
                          className={`text-[10px] font-bold px-2.5 py-1 rounded-lg transition-all ${
                            subtitlePosition === "center"
                              ? "bg-amber-500 text-black shadow-sm"
                              : "text-zinc-400 hover:text-zinc-200"
                          }`}
                        >
                          Center
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 2. Background Music & Auto-Ducking Panel */}
              <div className="bg-zinc-950/70 border border-zinc-800/80 rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Music className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-zinc-200 uppercase tracking-wider">
                      Background Music & Auto-Ducking
                    </span>
                  </div>
                  {/* Auto-Ducking Badge Toggle */}
                  <button
                    onClick={() => {
                      const next = !bgmDucking;
                      setBgmDucking(next);
                      handleUpdateSettings({ bgm_ducking: next });
                    }}
                    className={`text-[10px] font-bold px-2.5 py-1 rounded-full border transition-all flex items-center gap-1 ${
                      bgmDucking
                        ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm"
                        : "bg-zinc-800 text-zinc-500 border-zinc-700"
                    }`}
                    title="Sidechain compress BGM volume during speech"
                  >
                    <Zap className={`w-3 h-3 ${bgmDucking ? "text-emerald-400" : "text-zinc-500"}`} />
                    <span>{bgmDucking ? "⚡ Auto-Duck: Active" : "Auto-Duck: Off"}</span>
                  </button>
                </div>

                <div className="space-y-3 pt-1">
                  {/* Track Selector & Live Preview Button */}
                  <div className="space-y-1">
                    <label className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">Curated Track</label>
                    <div className="flex items-center gap-2">
                      <select
                        value={selectedBgmId}
                        onChange={(e) => {
                          setSelectedBgmId(e.target.value);
                          handleUpdateSettings({ bgm_track_id: e.target.value });
                        }}
                        className="flex-1 bg-zinc-900 border border-zinc-700/80 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="none">None (No Background Music)</option>
                        {bgmTracks.map((t) => (
                          <option key={t.id} value={t.id}>
                            🎵 {t.name} ({t.genre})
                          </option>
                        ))}
                      </select>

                      {selectedBgmId !== "none" && (
                        <button
                          onClick={() => toggleBgmPreview(selectedBgmId)}
                          className="bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/40 text-xs font-semibold px-3 py-2 rounded-xl flex items-center gap-1.5 transition-all shrink-0"
                          title="Preview track audio"
                        >
                          {playingBgmPreview === selectedBgmId ? (
                            <>
                              <Pause className="w-3.5 h-3.5 text-indigo-300" />
                              <span>Stop</span>
                            </>
                          ) : (
                            <>
                              <Play className="w-3.5 h-3.5 text-indigo-300" />
                              <span>Preview</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Volume Slider */}
                  {selectedBgmId !== "none" && (
                    <div className="flex items-center justify-between gap-4 pt-1">
                      <span className="text-[11px] text-zinc-400 shrink-0">BGM Level:</span>
                      <div className="flex-1 flex items-center gap-2">
                        <input
                          type="range"
                          min="0.02"
                          max="0.40"
                          step="0.01"
                          value={bgmVolume}
                          onChange={(e) => setBgmVolume(parseFloat(e.target.value))}
                          onMouseUp={() => handleUpdateSettings({ bgm_volume: bgmVolume })}
                          onTouchEnd={() => handleUpdateSettings({ bgm_volume: bgmVolume })}
                          className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-zinc-800 rounded-lg"
                        />
                        <span className="text-xs font-mono font-bold text-zinc-200 w-10 text-right">
                          {Math.round(bgmVolume * 100)}%
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* LEFT COLUMN: Master 9:16 Vertical Video Player & Timeline (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-zinc-900/80 border border-zinc-800/90 rounded-3xl p-5 shadow-2xl space-y-4">
              {/* Video Title & Meta */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-bold text-zinc-100 truncate max-w-[240px]">{selectedJob.filename}</h2>
                  <p className="text-[11px] text-zinc-400">Duration: {totalDuration.toFixed(1)}s • Master Edit</p>
                </div>
                <span className="text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Ready
                </span>
              </div>

              {/* Master 9:16 Video Player */}
              <div className="bg-black rounded-2xl overflow-hidden border border-zinc-800 flex flex-col items-center py-2 shadow-2xl relative">
                {/* SDR vs HDR10 Stream Switcher */}
                {hdrAvailable && (
                  <div className="flex items-center gap-1.5 mb-2 z-10">
                    <button
                      onClick={() => setViewingHdrVideo(false)}
                      className={`text-[10px] font-bold px-3 py-1 rounded-lg border transition-all ${
                        !viewingHdrVideo
                          ? "bg-zinc-700 text-white border-zinc-500 shadow-sm"
                          : "bg-zinc-900/90 text-zinc-400 border-zinc-800 hover:text-zinc-200"
                      }`}
                    >
                      SDR Standard
                    </button>
                    <button
                      onClick={() => setViewingHdrVideo(true)}
                      className={`text-[10px] font-bold px-3 py-1 rounded-lg border transition-all flex items-center gap-1.5 ${
                        viewingHdrVideo
                          ? "bg-gradient-to-r from-purple-600 to-pink-600 text-white border-pink-400 shadow-md shadow-pink-600/30"
                          : "bg-zinc-900/90 text-pink-400 border-zinc-800 hover:text-pink-300"
                      }`}
                    >
                      <Sparkles className="w-3 h-3 text-amber-300" />
                      <span>✨ HDR10 Upscaled (10-bit PQ)</span>
                    </button>
                  </div>
                )}

                {/* In-progress HDR conversion indicator */}
                {isUpscalingHdr && (
                  <div className="w-11/12 bg-purple-950/80 border border-purple-500/40 rounded-xl p-2.5 mb-2 text-center space-y-1.5 shadow-lg">
                    <div className="flex items-center justify-between text-[11px] font-semibold text-purple-200">
                      <span className="flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 animate-spin text-pink-400" />
                        AI SDR2HDR Upscaling in progress...
                      </span>
                      <span className="font-mono text-pink-300 font-bold">{hdrProgress.toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-zinc-900 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-pink-500 h-1.5 transition-all duration-300"
                        style={{ width: `${hdrProgress}%` }}
                      />
                    </div>
                    {hdrFps > 0 && (
                      <div className="text-[9px] text-purple-400 font-mono text-right">
                        Speed: {hdrFps.toFixed(1)} fps • 10-bit Rec.2020 SMPTE 2084
                      </div>
                    )}
                  </div>
                )}

                <video
                  ref={masterVideoRef}
                  key={`${selectedJob.job_id}_${viewingHdrVideo ? "hdr" : "sdr"}`}
                  controls
                  playsInline
                  onTimeUpdate={handleTimeUpdate}
                  className="max-h-[500px] w-auto rounded-xl shadow-lg aspect-[9/16]"
                  src={
                    viewingHdrVideo
                      ? `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/hdr-video`
                      : `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/video`
                  }
                >
                  Your browser does not support the video tag.
                </video>
              </div>

              {/* Interactive B-Roll Cutaway Timeline Bar */}
              {shots.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-zinc-800">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-zinc-300 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                      Visual Cutaway Timeline
                    </span>
                    <span className="text-zinc-500 font-mono text-[10px]">
                      {currentTime.toFixed(1)}s / {totalDuration.toFixed(1)}s
                    </span>
                  </div>

                  {/* Visual Bar showing Cutaways */}
                  <div className="relative w-full h-7 bg-zinc-950 rounded-lg overflow-hidden border border-zinc-800 p-0.5 flex">
                    {shots.map((shot, idx) => {
                      const leftPct = Math.max(0, (shot.start_time / totalDuration) * 100);
                      const widthPct = Math.min(100 - leftPct, ((shot.end_time - shot.start_time) / totalDuration) * 100);
                      const isCurrent = currentTime >= shot.start_time && currentTime <= shot.end_time;

                      return (
                        <button
                          key={idx}
                          onClick={() => jumpToCutaway(shot.start_time)}
                          title={`Click to jump: Shot ${idx + 1} (${shot.start_time}s - ${shot.end_time}s)`}
                          style={{
                            left: `${leftPct}%`,
                            width: `${widthPct}%`,
                          }}
                          className={`absolute top-0.5 bottom-0.5 rounded cursor-pointer transition-all flex items-center justify-center text-[10px] font-bold ${
                            isCurrent
                              ? "bg-amber-400 text-black shadow-lg ring-2 ring-amber-300 z-20"
                              : "bg-indigo-600/80 hover:bg-indigo-500 text-white z-10"
                          }`}
                        >
                          Cut {idx + 1}
                        </button>
                      );
                    })}
                  </div>
                  <p className="text-[10px] text-zinc-500 text-center">
                    💡 Click "Cut 1" or "Cut 2" to jump the master player directly to the B-roll!
                  </p>

                  {/* Playhead Cutaway Inserter Button */}
                  <div className="pt-2">
                    <button
                      onClick={openInsertCutawayAtCurrentTime}
                      className="w-full bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 transition-all hover:scale-[1.01]"
                      title="Split and insert a B-roll or Meme cutaway at the exact current playhead timestamp"
                    >
                      <Scissors className="w-3.5 h-3.5 text-indigo-200" />
                      <span>+ Add Cutaway at {currentTime.toFixed(1)}s</span>
                    </button>
                    <p className="text-[10px] text-zinc-500 text-center mt-1">
                      Scrub player to any second & click to insert stock footage or meme
                    </p>
                  </div>
                </div>
              )}

              {/* Action Buttons: Download + Delete Button */}
              <div className="flex items-center gap-2 pt-1">
                <a
                  href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/video`}
                  download={`final_${selectedJob.filename}`}
                  className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition-colors border border-zinc-700/60"
                >
                  <Download className="w-3.5 h-3.5 text-indigo-400" />
                  Download 9:16 Video
                </a>

                {/* Prominent Delete Button under Video Player */}
                <button
                  onClick={() => setJobToDelete({ id: selectedJob.job_id, name: selectedJob.filename })}
                  className="bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-semibold py-2.5 px-3 rounded-xl flex items-center gap-1.5 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete
                </button>

                {selectedJob.drive_file_url && (
                  <a
                    href={selectedJob.drive_file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-semibold py-2.5 px-3 rounded-xl flex items-center gap-1.5 transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Drive
                  </a>
                )}
              </div>

              {/* OpenReel Suite Integration Row */}
              <div className="pt-2 border-t border-zinc-800/80 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEmbeddedOpenReelJob(selectedJob.job_id)}
                    title="Launch live multi-track OpenReel video editor inside this dashboard"
                    className="flex-1 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:via-teal-500 hover:to-cyan-500 text-white text-[12px] font-bold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-950/30 hover:scale-[1.01]"
                  >
                    <Sparkles className="w-4 h-4 text-emerald-200 animate-pulse" />
                    <span>Launch OpenReel Studio</span>
                  </button>
                  <a
                    href={`http://localhost:5173/#/editor?loadJob=${encodeURIComponent(selectedJob.job_id)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="Open OpenReel in a dedicated browser tab"
                    className="bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/40 text-[11px] font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Popout Tab</span>
                  </a>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/export/openreel`}
                    download={`${selectedJob.filename.replace(/\.[^/.]+$/, "")}.oreel`}
                    title="Download native OpenReel Schema 1.2.0 project file (.oreel)"
                    className="flex-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-semibold py-2 px-2.5 rounded-xl flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Layers className="w-3.5 h-3.5 text-emerald-400" />
                    OpenReel .oreel
                  </a>
                  <a
                    href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/qc-report`}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="View 5-Factor Quality Control and Safe Zone Audit Report"
                    className="flex-1 bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[11px] font-semibold py-2 px-2.5 rounded-xl flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                    AI QC Audit
                  </a>
                </div>
              </div>

              {/* NLE & ZIP Export Action Row (Inspired by Rotodraft Suite) */}
              <div className="pt-2 border-t border-zinc-800/80 flex items-center gap-2">
                <a
                  href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/export/xml`}
                  download={`timeline_${selectedJob.filename.replace(/\.[^/.]+$/, "")}.xml`}
                  title="Export Final Cut Pro 7 XML timeline compatible with Adobe Premiere Pro and DaVinci Resolve"
                  className="flex-1 bg-violet-500/10 hover:bg-violet-500/20 text-violet-300 border border-violet-500/30 text-[11px] font-semibold py-2 px-2.5 rounded-xl flex items-center justify-center gap-1.5 transition-colors"
                >
                  <FileCode className="w-3.5 h-3.5 text-violet-400" />
                  Premiere / DaVinci XML
                </a>
                <a
                  href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/export/zip`}
                  download={`package_${selectedJob.filename.replace(/\.[^/.]+$/, "")}.zip`}
                  title="Download 1-Click Production ZIP with XML timeline, master video, SRT subtitles, and cutaways"
                  className="flex-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-semibold py-2 px-2.5 rounded-xl flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Archive className="w-3.5 h-3.5 text-amber-400" />
                  1-Click ZIP Bundle
                </a>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: B-Roll Cutaway Cards, Isolated Players, AI Review & Feedback (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* Header */}
            <div className="bg-zinc-900/60 border border-zinc-800/90 rounded-2xl p-4">
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <Film className="w-4 h-4 text-indigo-400" />
                  Generated B-Roll Cutaways ({shots.length} Active Cuts)
                </h3>
                <span className="text-[10px] font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 px-2 py-0.5 rounded-full">
                  Verified Clean
                </span>
              </div>
              <p className="text-xs text-zinc-400">
                {selectedJob.edit_plan?.summary || "Narrative-driven B-roll cutaways synchronized to spoken dialogue."}
              </p>
            </div>

            {/* B-Roll Cutaway Cards with Embedded Isolated Video Players */}
            {shots.length > 0 ? (
              <div className="space-y-4">
                {shots.map((shot, idx) => (
                  <div
                    key={idx}
                    className="bg-zinc-900/80 border border-zinc-800/90 hover:border-zinc-700/80 rounded-2xl p-5 space-y-3.5 shadow-xl transition-all"
                  >
                    {/* Header Row */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-indigo-600/30 text-indigo-400 border border-indigo-500/40 flex items-center justify-center text-xs font-bold">
                          {idx + 1}
                        </span>
                        <h4 className="text-xs font-bold text-zinc-100">
                          Cutaway {idx + 1}: {shot.start_time.toFixed(1)}s → {shot.end_time.toFixed(1)}s
                        </h4>
                        <span className="text-[10px] text-zinc-500 font-mono">
                          ({((shot.end_time - shot.start_time) || 2.5).toFixed(1)}s duration)
                        </span>
                        <span className="text-[10px] font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                          ⚡ {shot.speed ? `${shot.speed}x` : (shot.style === "meme" ? "1.30x" : "1.25x")}
                        </span>
                        {idx === 0 && (
                          <span className="text-[10px] font-extrabold bg-gradient-to-r from-fuchsia-600/30 to-rose-600/30 text-fuchsia-300 border border-fuchsia-500/50 px-2.5 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                            🔥 Compulsory Hook Meme (0–5s)
                          </span>
                        )}
                        {shot.style === "meme" && idx !== 0 && (
                          <span className="text-[10px] font-bold bg-fuchsia-500/15 text-fuchsia-400 border border-fuchsia-500/30 px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                            🎭 Auto AI Meme: {shot.meme_template?.replace(/_/g, " ") || "Meme"}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Swap Footage Button */}
                        <button
                          onClick={() => openSwapModalForShot(shot)}
                          className="text-[11px] font-semibold text-cyan-300 hover:text-white bg-cyan-500/15 hover:bg-cyan-600/30 border border-cyan-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
                          title="Swap footage with high-quality Pexels stock video or custom upload"
                        >
                          <RefreshCw className="w-3 h-3 text-cyan-400" />
                          <span>Swap Footage</span>
                        </button>

                        {/* Autonomous AI Meme Button / Regenerate */}
                        {shot.style === "meme" ? (
                          <button
                            disabled={isAutoGeneratingMeme[shot.shot_id]}
                            onClick={() => handleAutoGenerateMeme(shot.shot_id)}
                            className="text-[11px] font-semibold text-fuchsia-200 hover:text-white bg-fuchsia-600/25 hover:bg-fuchsia-600/40 border border-fuchsia-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                            title="Regenerate another unique AI meme tailored specifically to this dialogue quote"
                          >
                            <Sparkles className={`w-3 h-3 text-fuchsia-300 ${isAutoGeneratingMeme[shot.shot_id] ? "animate-spin" : ""}`} />
                            <span>{isAutoGeneratingMeme[shot.shot_id] ? "Generating..." : "⚡ AI Regenerate Meme"}</span>
                          </button>
                        ) : (
                          <button
                            disabled={isAutoGeneratingMeme[shot.shot_id]}
                            onClick={() => handleAutoGenerateMeme(shot.shot_id)}
                            className="text-[11px] font-semibold text-fuchsia-300 hover:text-white bg-fuchsia-500/15 hover:bg-fuchsia-600/30 border border-fuchsia-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                            title="Autonomously create a unique meme cutaway tailored to this dialogue quote"
                          >
                            <Sparkles className={`w-3 h-3 text-fuchsia-400 ${isAutoGeneratingMeme[shot.shot_id] ? "animate-spin" : ""}`} />
                            <span>{isAutoGeneratingMeme[shot.shot_id] ? "Creating Meme..." : "⚡ Auto AI Meme"}</span>
                          </button>
                        )}

                        <button
                          onClick={() => jumpToCutaway(shot.start_time)}
                          className="text-[11px] font-semibold text-amber-400 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all"
                        >
                          <Play className="w-3 h-3 fill-amber-400" />
                          Jump
                        </button>

                        {/* Delete Cutaway Button */}
                        <button
                          onClick={() => handleDeleteShot(shot.shot_id)}
                          className="text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 p-1.5 rounded-lg transition-colors"
                          title="Delete this cutaway shot"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Precision Timeline Boundary Controls */}
                    <div className="bg-zinc-950/80 border border-zinc-800/90 rounded-xl p-2.5 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 text-indigo-400" />
                        <span className="text-[10px] font-bold text-zinc-300 uppercase tracking-wider">Trim Boundaries:</span>
                      </div>
                      
                      <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
                        {/* Start Time Nudge */}
                        <div className="flex items-center gap-1 bg-zinc-900 px-2 py-0.5 rounded-lg border border-zinc-800">
                          <span className="text-[10px] text-zinc-400 font-sans uppercase mr-1">Start:</span>
                          <button
                            disabled={isTrimming[shot.shot_id] || shot.start_time <= 0}
                            onClick={() => handleTrimShot(shot.shot_id, shot.start_time - 0.1, shot.end_time)}
                            className="text-[10px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-1.5 py-0.5 rounded transition-colors"
                            title="Nudge start back 0.1s"
                          >
                            -0.1s
                          </button>
                          <span className="text-zinc-100 font-bold px-1">{shot.start_time.toFixed(1)}s</span>
                          <button
                            disabled={isTrimming[shot.shot_id] || shot.start_time >= shot.end_time - 0.3}
                            onClick={() => handleTrimShot(shot.shot_id, shot.start_time + 0.1, shot.end_time)}
                            className="text-[10px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-1.5 py-0.5 rounded transition-colors"
                            title="Nudge start forward 0.1s"
                          >
                            +0.1s
                          </button>
                        </div>

                        {/* End Time Nudge */}
                        <div className="flex items-center gap-1 bg-zinc-900 px-2 py-0.5 rounded-lg border border-zinc-800">
                          <span className="text-[10px] text-zinc-400 font-sans uppercase mr-1">End:</span>
                          <button
                            disabled={isTrimming[shot.shot_id] || shot.end_time <= shot.start_time + 0.3}
                            onClick={() => handleTrimShot(shot.shot_id, shot.start_time, shot.end_time - 0.1)}
                            className="text-[10px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-1.5 py-0.5 rounded transition-colors"
                            title="Nudge end back 0.1s"
                          >
                            -0.1s
                          </button>
                          <span className="text-zinc-100 font-bold px-1">{shot.end_time.toFixed(1)}s</span>
                          <button
                            disabled={isTrimming[shot.shot_id]}
                            onClick={() => handleTrimShot(shot.shot_id, shot.start_time, shot.end_time + 0.1)}
                            className="text-[10px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-1.5 py-0.5 rounded transition-colors"
                            title="Nudge end forward 0.1s"
                          >
                            +0.1s
                          </button>
                        </div>

                        {/* Duration Display */}
                        <span className="text-[10px] text-zinc-400 font-sans">
                          Duration: <strong className="text-zinc-200">{((shot.end_time - shot.start_time) || 2.5).toFixed(1)}s</strong>
                        </span>
                      </div>
                    </div>

                    {/* Dialogue Quote */}
                    {shot.dialogue_quote && (
                      <div className="text-xs text-zinc-300 italic border-l-2 border-indigo-500/60 pl-3 py-0.5 bg-indigo-950/20 rounded-r-lg">
                        "{shot.dialogue_quote}"
                      </div>
                    )}

                    {/* Meme Template & Caption Details */}
                    {shot.style === "meme" && (
                      <div className="text-xs bg-fuchsia-950/30 border border-fuchsia-500/30 p-3 rounded-xl space-y-1.5 shadow-inner">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-fuchsia-400 uppercase tracking-wider flex items-center gap-1">
                            🎭 Template: {shot.meme_template_resolved || shot.meme_template || "Viral Meme"}
                          </span>
                          <span className="text-[10px] text-zinc-400 font-mono">
                            Auto-Generated from 1,036 HD Templates
                          </span>
                        </div>
                        {shot.meme_captions && (
                          <div className="text-[11px] text-zinc-200 bg-zinc-900/70 p-2 rounded-lg border border-zinc-800/80 font-mono space-y-1">
                            {Object.entries(shot.meme_captions).map(([k, v]) => (
                              <div key={k} className="flex items-start gap-2">
                                <span className="text-fuchsia-400 shrink-0 font-semibold">{k}:</span>
                                <span className="text-zinc-300">"{v}"</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Emotional Metaphor */}
                    {shot.visceral_human_metaphor && shot.style !== "meme" && (
                      <div className="text-xs text-zinc-300 bg-zinc-950/70 p-3 rounded-xl border border-zinc-800/80 space-y-1">
                        <div className="flex items-center gap-1.5 text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                          <Sparkles className="w-3 h-3 text-indigo-400" />
                          Emotional Core & Human Metaphor
                        </div>
                        <p className="text-xs text-zinc-200">{shot.visceral_human_metaphor}</p>
                      </div>
                    )}

                    {/* AutoTransition & Audio Sound Effects Row */}
                    {(shot.transition || shot.contextual_sfx) && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                        {/* AutoTransition Badge */}
                        {shot.transition && (
                          <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-xl p-2.5 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider flex items-center gap-1">
                                <Zap className="w-3 h-3 text-violet-400" />
                                AutoTransition
                              </span>
                              <span className="text-[10px] font-mono text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
                                {shot.transition.type_in} ({shot.transition.duration_in}s)
                              </span>
                            </div>
                            {shot.transition.stinger_sfx && (
                              <div className="flex items-center justify-between text-[11px] text-zinc-300 bg-zinc-900/60 px-2 py-1 rounded-lg">
                                <span className="flex items-center gap-1.5 text-zinc-300 truncate max-w-[150px]" title={shot.transition.stinger_sfx.file}>
                                  <Volume2 className="w-3 h-3 text-violet-400 shrink-0" />
                                  <span className="truncate">{shot.transition.stinger_sfx.file}</span>
                                </span>
                                {shot.transition.stinger_sfx.audio_url && (
                                  <audio
                                    controls
                                    className="h-6 w-24 shrink-0 opacity-80 hover:opacity-100"
                                    src={shot.transition.stinger_sfx.audio_url}
                                  />
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Vision Sound Effect (SFX) Badge */}
                        {shot.contextual_sfx && (
                          <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-xl p-2.5 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                                <Volume2 className="w-3 h-3 text-emerald-400" />
                                Video SFX Foley
                              </span>
                              <span className="text-[10px] font-mono text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
                                Vol {Math.round((shot.contextual_sfx.volume || 0.4) * 100)}%
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-[11px] text-zinc-200 bg-zinc-900/60 px-2 py-1 rounded-lg">
                              <span className="font-medium text-emerald-300 truncate max-w-[150px]" title={shot.contextual_sfx.name || shot.contextual_sfx.file}>
                                {shot.contextual_sfx.name || shot.contextual_sfx.file}
                              </span>
                              {shot.contextual_sfx.audio_url && (
                                <audio
                                  controls
                                  className="h-6 w-24 shrink-0 opacity-80 hover:opacity-100"
                                  src={shot.contextual_sfx.audio_url}
                                />
                              )}
                            </div>
                            {shot.contextual_sfx.reason && (
                              <p className="text-[10px] text-zinc-400 italic line-clamp-1" title={shot.contextual_sfx.reason}>
                                {shot.contextual_sfx.reason}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Dedicated Standalone B-Roll Video Player with Poster Thumbnail */}
                    {shot.video_url && (
                      <div className="space-y-2 pt-2 border-t border-zinc-800/70">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className={`font-semibold flex items-center gap-1.5 ${shot.style === "meme" ? "text-fuchsia-400" : "text-cyan-400"}`}>
                            <Eye className="w-3.5 h-3.5" />
                            {shot.style === "meme" ? "Watch Isolated 9:16 Meme Cutaway" : "Watch Isolated B-Roll Cutaway Video"}
                          </span>
                          <span className="text-[10px] text-zinc-500 font-medium">
                            {shot.style === "meme" ? "🎭 9:16 HD Meme Cutaway • Auto-Synced SFX" : "Stockpile Montage • 0 Watermarks"}
                          </span>
                        </div>

                        <div className="rounded-xl overflow-hidden border border-zinc-800 bg-black max-h-[340px] flex items-center justify-center shadow-lg relative group">
                          <video
                            controls
                            playsInline
                            preload="metadata"
                            poster={shot.thumbnail_url}
                            className="max-h-[340px] w-auto max-w-full object-contain mx-auto"
                            src={shot.video_url}
                          >
                            Your browser does not support video playback.
                          </video>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-6 text-center space-y-2">
                <AlertCircle className="w-8 h-8 text-amber-400 mx-auto" />
                <h4 className="text-sm font-bold text-amber-200">No B-Roll Cutaways Overlayed</h4>
                <p className="text-xs text-zinc-400 max-w-md mx-auto">
                  This run did not generate visual cutaways. Click "+ Process New Clip" above to upload a video, or select another project from the switcher.
                </p>
              </div>
            )}

            {/* AI Reviewer Quality Audit Card */}
            {selectedJob.review_data && (
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-2xl p-4 flex items-start gap-3">
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-emerald-400 uppercase tracking-wide">
                      AI Reviewer Audit: {selectedJob.review_data.verdict} ({selectedJob.review_data.score}/10)
                    </span>
                  </div>
                  <p className="text-xs text-zinc-300 leading-relaxed">{selectedJob.review_data.feedback}</p>
                </div>
              </div>
            )}

            {/* Continuous Learning / Feedback Box */}
            <div className="bg-zinc-900/80 border border-indigo-500/20 rounded-2xl p-5 space-y-3.5 shadow-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-zinc-200 flex items-center gap-1.5">
                  <Brain className="w-4 h-4 text-violet-400" />
                  Teach the Engine (Continuous Learning)
                </span>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => (
                    <button
                      key={num}
                      onClick={() => setFeedbackRating(num)}
                      className={`w-6 h-6 rounded-md text-[11px] font-bold transition-all ${
                        feedbackRating >= num
                          ? "bg-amber-400 text-black shadow-sm scale-105"
                          : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  placeholder="Give direction (e.g. 'Loved the cardboard box metaphor! Add more rapid micro-cuts next time...')"
                  className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  onClick={handleSubmitFeedback}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-md shadow-indigo-600/20"
                >
                  <Send className="w-3.5 h-3.5" />
                  Teach Engine
                </button>
              </div>

              {feedbackSubmitted && (
                <p className="text-xs text-emerald-400 font-medium">
                  ✓ Preference saved to SQLite! Future B-roll prompts will incorporate your guidance.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
      )}

      {/* MEME STUDIO & CUSTOMIZER MODAL */}
      {showMemeModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/60">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-fuchsia-600/20 border border-fuchsia-500/30 text-fuchsia-400 flex items-center justify-center text-lg shadow-inner">
                  🎭
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    {isStandaloneMode
                      ? "Meme Studio — 1,036 HD Meme Templates"
                      : `Meme Cutaway Customizer (Cutaway ${memeTargetShot?.shot_id})`}
                  </h3>
                  <p className="text-xs text-zinc-400">
                    {isStandaloneMode
                      ? "Create standalone 9:16 vertical video meme cutaways with punchline SFX."
                      : `Transform this dialogue moment into an editorial meme cutaway with custom captions.`}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowMemeModal(false)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Spoken Quote Banner (if editing a shot) */}
            {memeTargetShot?.dialogue_quote && (
              <div className="bg-indigo-950/40 border-b border-indigo-500/20 px-6 py-2.5 flex items-center justify-between">
                <div className="text-xs text-indigo-200 truncate mr-3">
                  <span className="font-semibold text-indigo-400">Spoken Quote:</span> "{memeTargetShot.dialogue_quote}"
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    disabled={isAutoGeneratingMeme[memeTargetShot.shot_id]}
                    onClick={async () => {
                      await handleAutoGenerateMeme(memeTargetShot.shot_id);
                      setShowMemeModal(false);
                    }}
                    className="text-[11px] font-semibold text-white bg-gradient-to-r from-fuchsia-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 px-3 py-1 rounded-lg transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${isAutoGeneratingMeme[memeTargetShot.shot_id] ? "animate-spin" : ""}`} />
                    <span>{isAutoGeneratingMeme[memeTargetShot.shot_id] ? "Writing Meme..." : "🤖 Auto AI Meme"}</span>
                  </button>
                  <button
                    onClick={() => {
                      const q = memeTargetShot.dialogue_quote || "";
                      if (selectedTemplateKey === "stepped_in_shit") {
                        setMemeCaptions({ shoe_text: q });
                      } else if (selectedTemplateKey === "drake") {
                        setMemeCaptions({ top_text: "Making Excuses", bottom_text: q });
                      } else {
                        setMemeCaptions({ caption: q });
                      }
                    }}
                    className="text-[11px] font-semibold text-indigo-300 hover:text-white bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/30 px-2.5 py-1 rounded-lg transition-all"
                  >
                    📋 Use as Caption
                  </button>
                </div>
              </div>
            )}

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                {/* LEFT: Template Picker & Search (5 cols) */}
                <div className="md:col-span-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-zinc-300 uppercase tracking-wider">
                      Select Template ({memeTemplates.length})
                    </label>
                  </div>

                  {/* Search bar */}
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      value={memeSearchQuery}
                      onChange={(e) => setMemeSearchQuery(e.target.value)}
                      placeholder="Search templates (e.g. stepped, drake, clown)..."
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-9 pr-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
                    />
                  </div>

                  {/* Popular Archetype Pills */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {[
                      { key: "ishowspeed_shock", label: "⚡ Speed Shock" },
                      { key: "moms_kinda_homeless", label: "🥺 Mom's Kinda Homeless" },
                      { key: "not_your_personal_pornstar", label: "🤬 Not Your Personal Pornstar" },
                      { key: "caseoh_rage", label: "🎙️ CaseOh Rage" },
                      { key: "jynxzi_freakout", label: "🎮 Jynxzi Freakout" },
                      { key: "the_trusted_doctor", label: "👨‍⚕️ The Specialist (IYKYK)" },
                      { key: "gigachad", label: "🗿 Gigachad" },
                      { key: "hide_the_pain_harold", label: "👴 Harold" },
                      { key: "stepped_in_shit", label: "👞 Stepped in Shit" },
                      { key: "drake", label: "🙅‍♂️ Drake" },
                      { key: "clown", label: "🤡 Clown" },
                      { key: "same_picture", label: "🏢 Same Picture" },
                      { key: "batman_slap", label: "👋 Batman Slap" },
                      { key: "blinking_guy", label: "😳 Blinking Guy" },
                      { key: "gta_ah_shit", label: "🚶‍♂️ GTA Ah Shit" },
                    ].map((p) => (
                      <button
                        key={p.key}
                        onClick={() => handleSelectTemplate(p.key)}
                        className={`text-[10px] font-semibold px-2 py-1 rounded-lg border transition-all ${
                          selectedTemplateKey === p.key
                            ? "bg-fuchsia-600 text-white border-fuchsia-500 shadow-sm"
                            : "bg-zinc-800/80 hover:bg-zinc-700/80 text-zinc-300 border-zinc-700/60"
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>

                  {/* Scrollable Template Card List */}
                  <div className="max-h-[340px] overflow-y-auto space-y-1.5 pr-1 border border-zinc-800/80 rounded-2xl p-2 bg-zinc-950/60">
                    {memeTemplates
                      .filter((t) => {
                        if (!memeSearchQuery.trim()) return true;
                        const q = memeSearchQuery.toLowerCase();
                        return (
                          t.name.toLowerCase().includes(q) ||
                          t.key.toLowerCase().includes(q) ||
                          t.category.toLowerCase().includes(q)
                        );
                      })
                      .map((t) => {
                        const isSelected = selectedTemplateKey === t.key;
                        return (
                          <div
                            key={t.key}
                            onClick={() => handleSelectTemplate(t.key)}
                            className={`p-2.5 rounded-xl text-xs flex items-center gap-3 cursor-pointer transition-all border ${
                              isSelected
                                ? "bg-fuchsia-600/20 border-fuchsia-500/60 text-white shadow-md"
                                : "hover:bg-zinc-900 border-transparent text-zinc-300"
                            }`}
                          >
                            <img
                              src={t.preview_url}
                              alt={t.name}
                              className="w-12 h-12 rounded-lg object-cover bg-black border border-zinc-800 shrink-0"
                              loading="lazy"
                            />
                            <div className="truncate flex-1">
                              <p className="font-bold truncate text-xs">{t.name}</p>
                              <p className="text-[10px] text-zinc-400 truncate mt-0.5">{t.category}</p>
                            </div>
                            {isSelected && (
                              <CheckCircle2 className="w-4 h-4 text-fuchsia-400 shrink-0" />
                            )}
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* RIGHT: Live Preview, Captions, SFX & Generation (7 cols) */}
                <div className="md:col-span-7 space-y-4">
                  {/* Selected Template Visual Preview Card */}
                  {(() => {
                    const tmpl =
                      memeTemplates.find((t) => t.key === selectedTemplateKey) || memeTemplates[0];
                    return (
                      <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-fuchsia-400 flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5" />
                            Template: {tmpl?.name || selectedTemplateKey}
                          </span>
                          <span className="text-[10px] font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
                            {tmpl?.category}
                          </span>
                        </div>

                        {tmpl?.description && (
                          <p className="text-[11px] text-zinc-400 italic">{tmpl.description}</p>
                        )}

                        {/* Image Preview */}
                        <div className="rounded-xl overflow-hidden border border-zinc-800/80 bg-black/60 max-h-[160px] flex items-center justify-center">
                          <img
                            src={tmpl?.preview_url || `/api/memes/templates/${selectedTemplateKey}/preview`}
                            alt={tmpl?.name}
                            className="max-h-[160px] w-auto max-w-full object-contain mx-auto"
                          />
                        </div>

                        {/* Dynamic Caption Input Fields */}
                        <div className="space-y-2.5 pt-1">
                          <label className="text-xs font-bold text-zinc-300 uppercase tracking-wider block">
                            Meme Captions
                          </label>

                          {tmpl?.fields && tmpl.fields.length > 0 ? (
                            tmpl.fields.map((f: any) => (
                              <div key={f.name} className="space-y-1">
                                <label className="text-[11px] font-semibold text-zinc-400">
                                  {f.label}:
                                </label>
                                <input
                                  type="text"
                                  value={memeCaptions[f.name] || ""}
                                  onChange={(e) =>
                                    setMemeCaptions({ ...memeCaptions, [f.name]: e.target.value })
                                  }
                                  placeholder={f.placeholder}
                                  className="w-full bg-zinc-900 border border-zinc-700/80 rounded-xl px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
                                />
                              </div>
                            ))
                          ) : (
                            <div className="space-y-1">
                              <label className="text-[11px] font-semibold text-zinc-400">Caption:</label>
                              <input
                                type="text"
                                value={memeCaptions.caption || memeCaptions.shoe_text || memeCaptions.text || ""}
                                onChange={(e) =>
                                  setMemeCaptions({ ...memeCaptions, caption: e.target.value })
                                }
                                placeholder="Enter punchline or caption text..."
                                className="w-full bg-zinc-900 border border-zinc-700/80 rounded-xl px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
                              />
                            </div>
                          )}
                        </div>

                        {/* Punchline SFX Selector */}
                        <div className="space-y-1.5 pt-1">
                          <label className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                            <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                            Punchline Sound Effect (189 SFX Library)
                          </label>

                          <div className="flex items-center gap-2">
                            <select
                              value={selectedSfxFile}
                              onChange={(e) => setSelectedSfxFile(e.target.value)}
                              className="flex-1 bg-zinc-900 border border-zinc-700/80 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
                            >
                              <option value="81_vine_boom.mp3">💥 Vine Boom (Dramatic Meme Punchline)</option>
                              <option value="59_cartoon_slip_whoosh.mp3">💨 Cartoon Slip Whoosh</option>
                              <option value="01_bonk_impact.mp3">🔨 Bonk Impact</option>
                              <option value="11_bruh.mp3">😐 Bruh Sound Effect</option>
                              <option value="60_sad_violin.mp3">🎻 Sad Violin (Tragic Humor)</option>
                              <option value="55_subtle_bass_drop.mp3">🔊 Subtle Bass Drop</option>
                              <option value="04_camera_shutter.mp3">📸 Camera Shutter Flash</option>
                              <option value="28_bell_ding.mp3">🔔 Bell Ding</option>
                              {sfxCatalog
                                .filter(
                                  (s) =>
                                    ![
                                      "81_vine_boom.mp3",
                                      "59_cartoon_slip_whoosh.mp3",
                                      "01_bonk_impact.mp3",
                                      "11_bruh.mp3",
                                      "60_sad_violin.mp3",
                                      "55_subtle_bass_drop.mp3",
                                      "04_camera_shutter.mp3",
                                      "28_bell_ding.mp3",
                                    ].includes(s.file)
                                )
                                .slice(0, 30)
                                .map((s) => (
                                  <option key={s.file} value={s.file}>
                                    {s.name || s.file}
                                  </option>
                                ))}
                            </select>

                            <audio
                              controls
                              className="h-7 w-28 shrink-0 opacity-90 hover:opacity-100"
                              src={`/api/sfx/${selectedSfxFile}`}
                            />
                          </div>
                        </div>

                        {/* Standalone Result Preview */}
                        {standaloneMemeResult?.video_url && (
                          <div className="bg-zinc-900 border border-fuchsia-500/40 rounded-xl p-3 space-y-2 pt-2">
                            <div className="flex items-center justify-between text-xs text-fuchsia-300 font-bold">
                              <span>✓ Generated 9:16 Vertical Video:</span>
                              <a
                                href={standaloneMemeResult.video_url}
                                download="meme_cutaway.mp4"
                                className="text-[11px] text-white bg-fuchsia-600 hover:bg-fuchsia-500 px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors"
                              >
                                <Download className="w-3 h-3" />
                                Download MP4
                              </a>
                            </div>
                            <video
                              controls
                              autoPlay
                              className="max-h-[220px] w-auto max-w-full mx-auto rounded-lg border border-zinc-800"
                              src={standaloneMemeResult.video_url}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
              <span className="text-[11px] text-zinc-500 font-mono">
                Renders 1080x1920 9:16 vertical video cutaway with Ken Burns motion & punchline SFX
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowMemeModal(false)}
                  className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleGenerateMeme}
                  disabled={isGeneratingMeme}
                  className="bg-fuchsia-600 hover:bg-fuchsia-500 disabled:opacity-50 text-white text-xs font-semibold px-5 py-2 rounded-xl flex items-center gap-2 shadow-lg shadow-fuchsia-600/30 transition-all hover:scale-[1.02]"
                >
                  <Sparkles className={`w-3.5 h-3.5 ${isGeneratingMeme ? "animate-spin" : ""}`} />
                  <span>
                    {isGeneratingMeme
                      ? "Rendering Meme Video (FFmpeg)..."
                      : isStandaloneMode
                      ? "Generate 9:16 Meme Video"
                      : `Apply Meme to Shot ${memeTargetShot?.shot_id || ""}`}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* IN-CARD B-ROLL SWAPPER MODAL */}
      {showSwapModal && swapTargetShot && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/70">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center shadow-inner">
                  <RefreshCw className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    Swap Footage: Cutaway {swapTargetShot.shot_id}
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Replace existing footage with 4K royalty-free Pexels video or upload your own file.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowSwapModal(false)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tab Selector: Pexels Search vs Custom Upload */}
            <div className="px-6 pt-4 pb-2 border-b border-zinc-800/80 flex items-center gap-3 bg-zinc-950/40">
              <button
                onClick={() => setSwapTab("search")}
                className={`text-xs font-semibold px-4 py-2 rounded-xl transition-all flex items-center gap-2 ${
                  swapTab === "search"
                    ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/20"
                    : "text-zinc-400 hover:text-zinc-200 bg-zinc-900/60"
                }`}
              >
                <Search className="w-3.5 h-3.5" />
                Pexels Stock Search
              </button>
              <button
                onClick={() => setSwapTab("upload")}
                className={`text-xs font-semibold px-4 py-2 rounded-xl transition-all flex items-center gap-2 ${
                  swapTab === "upload"
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                    : "text-zinc-400 hover:text-zinc-200 bg-zinc-900/60"
                }`}
              >
                <Upload className="w-3.5 h-3.5" />
                Upload Custom Video
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-4">
              {swapTab === "search" ? (
                <div className="space-y-4">
                  {/* Search Query Input */}
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        value={swapSearchQuery}
                        onChange={(e) => setSwapSearchQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSearchStock(swapSearchQuery);
                        }}
                        placeholder="Search visual topic (e.g. luxury watch, coding laptop, handshake)..."
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <button
                      onClick={() => handleSearchStock(swapSearchQuery)}
                      disabled={isSearchingStock}
                      className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
                    >
                      <Search className={`w-3.5 h-3.5 ${isSearchingStock ? "animate-spin" : ""}`} />
                      <span>{isSearchingStock ? "Searching..." : "Search"}</span>
                    </button>
                  </div>

                  {/* Quick Pill Suggestions */}
                  <div className="flex flex-wrap gap-1.5">
                    {["luxury watch", "focus typing laptop", "business handshake", "cash counting money", "frustrated stress", "confident smile", "city drone aerial"].map((pill) => (
                      <button
                        key={pill}
                        onClick={() => {
                          setSwapSearchQuery(pill);
                          handleSearchStock(pill);
                        }}
                        className="text-[10px] bg-zinc-800/80 hover:bg-zinc-700/80 text-zinc-300 border border-zinc-700/60 px-2.5 py-1 rounded-lg transition-colors"
                      >
                        {pill}
                      </button>
                    ))}
                  </div>

                  {/* Candidate Results Grid */}
                  <div className="space-y-2 pt-2">
                    <div className="flex items-center justify-between text-xs text-zinc-400">
                      <span>Available Clips ({stockCandidates.length})</span>
                      <span className="text-[10px] text-zinc-500">9:16 Vertical HD • 0 Watermarks</span>
                    </div>

                    {isSearchingStock ? (
                      <div className="p-12 text-center text-xs text-zinc-400 space-y-2">
                        <Clock className="w-6 h-6 animate-spin text-cyan-400 mx-auto" />
                        <p>Querying Pexels HD video catalog...</p>
                      </div>
                    ) : stockCandidates.length > 0 ? (
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-[380px] overflow-y-auto pr-1">
                        {stockCandidates.map((cand) => (
                          <div
                            key={cand.id}
                            className="bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800 hover:border-cyan-500/60 transition-all flex flex-col group"
                          >
                            <div className="relative aspect-[9/16] max-h-[180px] overflow-hidden bg-black flex items-center justify-center">
                              <img
                                src={cand.thumbnail}
                                alt="Candidate"
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                                loading="lazy"
                              />
                              <span className="absolute bottom-1.5 right-1.5 bg-black/80 text-[10px] text-zinc-200 px-1.5 py-0.5 rounded font-mono">
                                {cand.duration}s
                              </span>
                            </div>

                            <div className="p-2.5 space-y-2 flex-1 flex flex-col justify-between">
                              <div className="text-[11px] text-zinc-300 truncate font-medium">
                                Clip #{cand.id}
                              </div>
                              <button
                                disabled={isSwappingStock}
                                onClick={() => handleSelectStockCandidate(cand)}
                                className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-[11px] font-bold py-1.5 rounded-lg flex items-center justify-center gap-1 transition-colors shadow-sm"
                              >
                                <CheckCircle2 className="w-3 h-3" />
                                <span>{isSwappingStock ? "Downloading..." : "Use This Clip"}</span>
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 text-center border border-dashed border-zinc-800 rounded-2xl text-xs text-zinc-500">
                        Search any topic above to preview available footage.
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* Custom File Upload Tab */
                <div className="space-y-4 py-4">
                  <div
                    onClick={() => customVideoInputRef.current?.click()}
                    className="border-2 border-dashed border-indigo-500/40 hover:border-indigo-400 bg-indigo-500/5 hover:bg-indigo-500/10 rounded-2xl p-10 text-center cursor-pointer transition-all"
                  >
                    <input
                      type="file"
                      ref={customVideoInputRef}
                      accept="video/*,.mp4,.mov,.mkv,.webm,.avi"
                      className="hidden"
                      onClick={(e) => {
                        e.stopPropagation();
                        (e.target as HTMLInputElement).value = "";
                      }}
                      onChange={(e) => {
                        if (e.target.files?.[0]) handleCustomVideoUpload(e.target.files[0]);
                      }}
                    />
                    <Upload className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
                    <h4 className="text-sm font-bold text-zinc-100">Upload custom video for this shot</h4>
                    <p className="text-xs text-zinc-400 mt-1">
                      Supports MP4, MOV. Will be automatically formatted to 1080x1920 9:16 vertical.
                    </p>
                    <div className="mt-4">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          customVideoInputRef.current?.click();
                        }}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-indigo-600/20 inline-flex items-center gap-1.5"
                      >
                        <Upload className="w-3.5 h-3.5" />
                        Choose Video File
                      </button>
                    </div>
                    {isUploadingCustom && (
                      <p className="text-xs text-indigo-400 mt-3 animate-pulse">
                        Uploading and formatting video clip with FFmpeg...
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
              <span className="text-[11px] text-zinc-500 font-mono">
                Duration: {((swapTargetShot.end_time - swapTargetShot.start_time) || 2.5).toFixed(1)}s
              </span>
              <button
                onClick={() => setShowSwapModal(false)}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* INSERT CUTAWAY AT PLAYHEAD MODAL */}
      {showInsertCutawayModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-zinc-800 rounded-3xl max-w-lg w-full shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/70">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-violet-600/20 border border-violet-500/30 text-violet-400 flex items-center justify-center shadow-inner">
                  <Scissors className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    Insert Cutaway at {insertCutawayTime.toFixed(1)}s
                  </h3>
                  <p className="text-xs text-zinc-400">
                    Split dialogue and insert visual B-roll or meme at current playhead.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowInsertCutawayModal(false)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              {/* Timing Controls */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">Start Time (s)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={insertCutawayTime}
                    onChange={(e) => setInsertCutawayTime(parseFloat(e.target.value) || 0)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">Duration (s)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="1.0"
                    max="10.0"
                    value={insertCutawayDur}
                    onChange={(e) => setInsertCutawayDur(parseFloat(e.target.value) || 2.5)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
                  />
                </div>
              </div>

              {/* Cutaway Type: Stock Footage vs Meme */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">Cutaway Style</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setInsertCutawayStyle("stockpile")}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      insertCutawayStyle === "stockpile"
                        ? "bg-indigo-600/20 border-indigo-500 text-white shadow-sm"
                        : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    <div className="text-xs font-bold">🎬 Stock Footage</div>
                    <div className="text-[10px] text-zinc-500">Pexels 4K vertical B-roll</div>
                  </button>

                  <button
                    onClick={() => setInsertCutawayStyle("meme")}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      insertCutawayStyle === "meme"
                        ? "bg-fuchsia-600/20 border-fuchsia-500 text-white shadow-sm"
                        : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    <div className="text-xs font-bold">🎭 Meme Cutaway</div>
                    <div className="text-[10px] text-zinc-500">Editorial meme + punchline SFX</div>
                  </button>
                </div>
              </div>

              {/* Search prompt / meme fields */}
              {insertCutawayStyle === "stockpile" ? (
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
                    Visual Search Prompt
                  </label>
                  <input
                    type="text"
                    value={insertCutawayPrompt}
                    onChange={(e) => setInsertCutawayPrompt(e.target.value)}
                    placeholder="e.g. luxury watches, money finance, laptop coding..."
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
                      Meme Template
                    </label>
                    <select
                      value={insertCutawayMemeTemplate}
                      onChange={(e) => setInsertCutawayMemeTemplate(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-fuchsia-500"
                    >
                      <option value="ishowspeed_shock">⚡ IShowSpeed (Screaming Shock)</option>
                      <option value="moms_kinda_homeless">🥺 My Mom's Kinda Homeless (Speed Fortnite)</option>
                      <option value="not_your_personal_pornstar">🤬 Not Your Personal Pornstar! (Meltdown)</option>
                      <option value="caseoh_rage">🎙️ CaseOh (Headset Mic Rage)</option>
                      <option value="jynxzi_freakout">🎮 Jynxzi (Controller Disbelief)</option>
                      <option value="the_trusted_doctor">👨‍⚕️ The Specialist (IYKYK)</option>
                      <option value="gigachad">🗿 Gigachad</option>
                      <option value="hide_the_pain_harold">👴 Harold</option>
                      <option value="stepped_in_shit">👞 Stepped in Shit</option>
                      <option value="drake">🙅‍♂️ Drake Yes/No</option>
                      <option value="clown">🤡 Clown Makeup</option>
                      <option value="same_picture">🏢 Corporate Needs You</option>
                      <option value="batman_slap">👋 Batman Slap</option>
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
                      Caption / Point of Emphasis
                    </label>
                    <input
                      type="text"
                      value={insertCutawayPrompt}
                      onChange={(e) => setInsertCutawayPrompt(e.target.value)}
                      placeholder="Point of humor or emphasis..."
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
              <button
                onClick={() => setShowInsertCutawayModal(false)}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={isInsertingCutaway}
                onClick={handleConfirmInsertCutaway}
                className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2 rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
              >
                <Scissors className={`w-3.5 h-3.5 ${isInsertingCutaway ? "animate-spin" : ""}`} />
                <span>{isInsertingCutaway ? "Inserting Cutaway..." : "Insert Cutaway"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CURIOUS MIKE CAMPAIGN HUB & 50 CURATED MOMENTS MODAL */}
      {showMomentsModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-emerald-500/40 rounded-3xl max-w-5xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/80">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center text-lg shadow-inner">
                  🎯
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">Curious Mike Campaign Hub</h3>
                    <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full">
                      $1.25 / 1k Views • $7,500 Budget
                    </span>
                  </div>
                  <p className="text-xs text-zinc-400">
                    Host: Michael Porter Jr. (@curiousmike / @mpj) • Trae Young Episode • 2,000 views min to qualify
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowMomentsModal(false)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Inner Tabs: Moments Catalog vs Rules */}
            <div className="px-5 py-3 border-b border-zinc-800 bg-zinc-950/40 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCuratedMomentsTab("moments")}
                  className={`text-xs font-bold px-3.5 py-1.5 rounded-xl flex items-center gap-2 transition-all ${
                    curatedMomentsTab === "moments"
                      ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                      : "text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>50 Curated Moments</span>
                  <span className="text-[10px] bg-emerald-800/80 px-1.5 py-0.2 rounded-full font-mono">
                    {campaigns.find((c) => c.id === "curious_mike")?.curated_moments?.length || 50}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => setCuratedMomentsTab("rules")}
                  className={`text-xs font-bold px-3.5 py-1.5 rounded-xl flex items-center gap-2 transition-all ${
                    curatedMomentsTab === "rules"
                      ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                      : "text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800"
                  }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Campaign Rules & The No List</span>
                </button>
              </div>

              {curatedMomentsTab === "moments" && (
                <div className="relative max-w-xs w-full">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                  <input
                    type="text"
                    value={momentSearchQuery}
                    onChange={(e) => setMomentSearchQuery(e.target.value)}
                    placeholder="Search moments (Trae, Knicks, AAU, pass)..."
                    className="w-full bg-zinc-900 border border-zinc-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              )}
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              {curatedMomentsTab === "moments" ? (
                <div className="space-y-4">
                  {/* Category Chips */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    {[
                      { key: "all", label: "All Moments" },
                      { key: "debate", label: "⚔️ Debates & Controversies" },
                      { key: "story", label: "📖 Stories & AAU Memories" },
                      { key: "technique", label: "🏀 Skills & Technique" },
                      { key: "take", label: "🔥 Hot Takes" },
                    ].map((chip) => (
                      <button
                        key={chip.key}
                        type="button"
                        onClick={() => setMomentFilterAngle(chip.key)}
                        className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition-all ${
                          momentFilterAngle === chip.key
                            ? "bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-sm"
                            : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                        }`}
                      >
                        {chip.label}
                      </button>
                    ))}
                  </div>

                  {/* Moments Cards Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    {(
                      campaigns.find((c) => c.id === "curious_mike")?.curated_moments || []
                    )
                      .filter((m) => {
                        if (momentFilterAngle !== "all") {
                          const angle = m.angle?.toLowerCase() || "";
                          if (!angle.includes(momentFilterAngle)) return false;
                        }
                        if (!momentSearchQuery.trim()) return true;
                        const q = momentSearchQuery.toLowerCase();
                        return (
                          m.moment_id.toLowerCase().includes(q) ||
                          m.screen_hook.toLowerCase().includes(q) ||
                          m.post_caption.toLowerCase().includes(q) ||
                          (m.broll_theme && m.broll_theme.toLowerCase().includes(q))
                        );
                      })
                      .map((m) => (
                        <div
                          key={m.moment_id}
                          className="bg-zinc-950/80 border border-zinc-800/90 hover:border-emerald-500/50 rounded-2xl p-4 space-y-2.5 transition-all group flex flex-col justify-between"
                        >
                          <div className="space-y-2">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
                                {m.moment_id}
                              </span>
                              <span className="font-mono text-[11px] text-zinc-400 flex items-center gap-1">
                                <Clock className="w-3 h-3 text-zinc-500" />
                                {m.timestamp_range} ({Math.round(m.end_time_sec - m.start_time_sec)}s)
                              </span>
                            </div>

                            <div className="text-xs font-bold text-zinc-100 group-hover:text-emerald-300 transition-colors">
                              "{m.screen_hook}"
                            </div>

                            <p className="text-[11px] text-zinc-400 italic">
                              "{m.post_caption}"
                            </p>

                            {m.broll_theme && (
                              <div className="text-[10px] text-zinc-400 bg-zinc-900/80 rounded-lg p-2 border border-zinc-800/60">
                                <span className="font-semibold text-zinc-300">Suggested B-roll:</span> {m.broll_theme}
                              </div>
                            )}

                            {m.broll_sources && m.broll_sources.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {m.broll_sources.map((s, idx) => (
                                  <span
                                    key={idx}
                                    className="text-[9px] font-medium bg-zinc-900 text-zinc-400 px-1.5 py-0.5 rounded border border-zinc-800"
                                  >
                                    {s}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>

                          <div className="pt-2 border-t border-zinc-900 flex items-center justify-between">
                            <span className="text-[10px] text-emerald-500 font-medium">
                              {m.angle ? `Angle: ${m.angle}` : "Curated Moment"}
                            </span>
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard?.writeText(
                                  `Moment ${m.moment_id} (${m.timestamp_range})\nHook: ${m.screen_hook}\nCaption: ${m.post_caption}`
                                );
                                showToast(`Selected Moment ${m.moment_id}! Hook & timestamps copied to clipboard.`);
                                setShowMomentsModal(false);
                                setShowUploadMode(true);
                              }}
                              className="bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white border border-emerald-500/40 text-[11px] font-semibold px-2.5 py-1 rounded-lg transition-all flex items-center gap-1"
                            >
                              <span>Use This Moment</span>
                              <ChevronRight className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-5 text-left max-w-4xl mx-auto">
                  {/* Payout specs table */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                      <div className="text-[10px] uppercase font-bold text-zinc-400">Payout Rate</div>
                      <div className="text-base font-extrabold text-emerald-400 mt-0.5">$1.25</div>
                      <div className="text-[10px] text-zinc-500">per 1,000 views</div>
                    </div>
                    <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                      <div className="text-[10px] uppercase font-bold text-zinc-400">Total Bounty</div>
                      <div className="text-base font-extrabold text-white mt-0.5">$7,500</div>
                      <div className="text-[10px] text-zinc-500">~6M views pool</div>
                    </div>
                    <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                      <div className="text-[10px] uppercase font-bold text-zinc-400">Cap Per Clip</div>
                      <div className="text-base font-extrabold text-white mt-0.5">$300 Max</div>
                      <div className="text-[10px] text-zinc-500">240,000 views</div>
                    </div>
                    <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                      <div className="text-[10px] uppercase font-bold text-zinc-400">Min to Qualify</div>
                      <div className="text-base font-extrabold text-amber-400 mt-0.5">2,000 Views</div>
                      <div className="text-[10px] text-zinc-500">pays $2.50+</div>
                    </div>
                  </div>

                  {/* The 6 Golden Rules */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      The 6 Rules Every Clip Must Pass
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                        <div className="text-xs font-bold text-emerald-300">Rule 1: 40%+ US, Canada, UK Geo</div>
                        <p className="text-[11px] text-zinc-400">
                          Post between 12pm-9pm Eastern. Use English text hooks and American sports context so algorithms target NBA viewers.
                        </p>
                      </div>
                      <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                        <div className="text-xs font-bold text-emerald-300">Rule 2: 1%+ Engagement (Debates)</div>
                        <p className="text-[11px] text-zinc-400">
                          Frame hot takes where viewers fight in comments. Comment fights push clips to 100k+ views.
                        </p>
                      </div>
                      <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                        <div className="text-xs font-bold text-emerald-300">Rule 3: 0% AI Video & Real B-Roll Only</div>
                        <p className="text-[11px] text-zinc-400">
                          Zero AI video or Opus clips allowed. Autopilot only uses authentic NBA/sports footage capped at 33% total duration.
                        </p>
                      </div>
                      <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                        <div className="text-xs font-bold text-emerald-300">Rule 4: Pure Dialogue (No Phonk/BGM)</div>
                        <p className="text-[11px] text-zinc-400">
                          Submissions with phonk music or loud tracks get rejected. Autopilot automatically disables background music.
                        </p>
                      </div>
                      <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                        <div className="text-xs font-bold text-emerald-300">Rule 5: Burned-in Word-by-Word Subtitles</div>
                        <p className="text-[11px] text-zinc-400">
                          High contrast, perfectly spelled, safe-zone elevated subtitles so they never obscure the platform buttons or watermark.
                        </p>
                      </div>
                      <div className="bg-zinc-950/80 border border-emerald-500/40 rounded-2xl p-3.5 space-y-1 bg-emerald-950/20">
                        <div className="text-xs font-bold text-emerald-300">Rule 6: Mandatory YT: @mpj Watermark</div>
                        <p className="text-[11px] text-zinc-400">
                          Autopilot automatically composites the official high-resolution YT: @mpj watermark across 100% of video duration.
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* The Instant Rejection List */}
                  <div className="bg-rose-950/20 border border-rose-500/30 rounded-2xl p-4 space-y-2">
                    <h4 className="text-xs font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-rose-400" />
                      Instant Rejections ("The No List")
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] text-zinc-300">
                      <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Reposting MPJ's socials</div>
                      <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Phonk or BGM music</div>
                      <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ AI video / avatars</div>
                      <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Aura / glow / skull edits</div>
                      <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Low-effort uncut clips</div>
                      <div className="bg-zinc-950/60 rounded-lg p-2 border border-rose-500/40 text-rose-300">❌ Missing @mpj watermark</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
              <span className="text-xs text-zinc-500">
                AI B-Roll Autopilot • Curious Mike Campaign Engine Active
              </span>
              <button
                onClick={() => setShowMomentsModal(false)}
                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-5 py-2 rounded-xl transition-all shadow-md shadow-emerald-600/30"
              >
                Close Hub
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SDR2HDR UPSCALER & HDR10 MODAL */}
      {showHdrModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-purple-500/40 rounded-3xl max-w-lg w-full shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/80">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 to-pink-600 text-white flex items-center justify-center shadow-lg shadow-purple-600/30">
                  <Tv className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <span>⚡ SDR2HDR Upscaler & HDR10</span>
                    <span className="text-[9px] font-bold uppercase tracking-wider bg-pink-500/20 text-pink-300 border border-pink-500/40 px-2 py-0.5 rounded-full">
                      10-bit Rec.2020
                    </span>
                  </h3>
                  <p className="text-xs text-zinc-400">
                    AI Inverse Tone Mapping (ITM) + Super-Resolution Lanczos Upscaling
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowHdrModal(false)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              {/* Output Resolution & Super-Resolution Scale */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-purple-400" />
                  Target Resolution & Upscaling
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { scale: 1.0, label: "1080x1920", sub: "1.0x Native HDR10" },
                    { scale: 1.5, label: "1620x2880", sub: "1.5x QHD+ Ultra" },
                    { scale: 2.0, label: "2160x3840", sub: "2.0x 4K UHD" },
                  ].map((item) => (
                    <button
                      key={item.scale}
                      type="button"
                      onClick={() => setHdrScale(item.scale)}
                      className={`p-2.5 rounded-xl border text-left transition-all ${
                        hdrScale === item.scale
                          ? "bg-purple-600/20 border-purple-500 text-white shadow-sm"
                          : "bg-zinc-950/70 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                      }`}
                    >
                      <div className="text-xs font-bold">{item.label}</div>
                      <div className="text-[10px] text-zinc-500">{item.sub}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Tone Mapping Style */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  Brightness & Dynamic Range Anchoring
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setHdrTone("vivid")}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      hdrTone === "vivid"
                        ? "bg-amber-500/20 border-amber-500 text-white shadow-sm"
                        : "bg-zinc-950/70 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <div className="text-xs font-bold flex items-center gap-1.5">
                      <span>🔥 Vivid (Viral Pop)</span>
                    </div>
                    <div className="text-[10px] text-zinc-400 mt-1">
                      Maps whites to peak nits. Maximum pop on OLED smartphone screens (TikTok / Reels / Shorts).
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setHdrTone("reference")}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      hdrTone === "reference"
                        ? "bg-indigo-500/20 border-indigo-500 text-white shadow-sm"
                        : "bg-zinc-950/70 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                    }`}
                  >
                    <div className="text-xs font-bold flex items-center gap-1.5">
                      <span>🎬 Reference (BT.2408)</span>
                    </div>
                    <div className="text-[10px] text-zinc-400 mt-1">
                      Standard broadcast anchoring (203 nit diffuse white) with specular headroom.
                    </div>
                  </button>
                </div>
              </div>

              {/* Fast Mode Toggle */}
              <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-3 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-zinc-200">Fast AI Mode</div>
                  <div className="text-[10px] text-zinc-500">
                    Optimized spatial masks & fast HEVC 10-bit encoding
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={hdrFastMode}
                  onChange={(e) => setHdrFastMode(e.target.checked)}
                  className="w-4 h-4 accent-purple-500 cursor-pointer"
                />
              </div>

              {/* Status / Live Progress if running */}
              {isUpscalingHdr && (
                <div className="space-y-1.5 bg-purple-950/40 border border-purple-500/30 rounded-2xl p-3">
                  <div className="flex justify-between text-xs font-semibold text-purple-200">
                    <span>Upscaling & Tone Mapping...</span>
                    <span className="font-mono text-pink-300 font-bold">{hdrProgress.toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-zinc-950 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 transition-all duration-300"
                      style={{ width: `${hdrProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
              <button
                onClick={() => setShowHdrModal(false)}
                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
              >
                Close
              </button>
              <button
                disabled={isUpscalingHdr}
                onClick={handleStartHdrUpscale}
                className="bg-gradient-to-r from-purple-600 via-pink-600 to-rose-600 hover:from-purple-500 hover:to-rose-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-purple-600/30 transition-all hover:scale-[1.02]"
              >
                <Sparkles className={`w-3.5 h-3.5 ${isUpscalingHdr ? "animate-spin" : ""}`} />
                <span>{isUpscalingHdr ? `Upscaling (${hdrProgress.toFixed(0)}%)...` : "⚡ Start SDR2HDR Upscale"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* OPENREEL EXPORT SUCCESS MODAL */}
      {openReelModalData && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-indigo-500/40 rounded-3xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <Film className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-sm text-white">OpenReel Project Exported (.oreel)</h3>
              </div>
              <button
                onClick={() => setOpenReelModalData(null)}
                className="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-zinc-300">
              <p>Your edit plan has been compiled into a native OpenReel Schema 1.2.0 non-destructive multitrack project.</p>
              
              <div className="bg-black/60 rounded-xl p-3 border border-zinc-800 space-y-1 font-mono text-[11px]">
                <div className="text-indigo-300 font-bold">Files Generated:</div>
                <div className="text-zinc-400 truncate">.oreel: {openReelModalData.files?.oreel}</div>
                <div className="text-zinc-400 truncate">Manifest: {openReelModalData.files?.manifest}</div>
                <div className="text-zinc-400 truncate">Edit Plan: {openReelModalData.files?.plan}</div>
              </div>

              <div className="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-3 text-[11px] space-y-1">
                <div className="font-bold text-indigo-200">How to open in OpenReel Editor:</div>
                <ol className="list-decimal list-inside space-y-1 text-zinc-300">
                  <li>Start OpenReel web app (<code className="text-indigo-300">pnpm --filter @openreel/web dev</code>).</li>
                  <li>In OpenReel, select <strong>File → Open Project</strong> and choose the <code className="text-indigo-300">project.oreel</code> file.</li>
                  <li>All timeline tracks (Speaker A-Roll, B-Roll cutaways, subtitles, and audio) remain 100% editable!</li>
                </ol>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setOpenReelModalData(null)}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EMBEDDED OPENREEL STUDIO MODAL */}
      {embeddedOpenReelJob && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex flex-col p-2 sm:p-4">
          <div className="bg-zinc-900 border border-emerald-500/40 rounded-2xl flex flex-col flex-1 overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950">
              <div className="flex items-center gap-2">
                <Film className="w-5 h-5 text-emerald-400" />
                <span className="font-bold text-sm text-white">OpenReel Video Editor</span>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono">
                  Schema 1.2.0 • Non-Destructive Multi-Track
                </span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={`http://localhost:5173/#/editor?loadJob=${encodeURIComponent(embeddedOpenReelJob)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all"
                  title="Open in standalone tab"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Popout Tab
                </a>
                <button
                  onClick={() => setEmbeddedOpenReelJob(null)}
                  className="text-zinc-400 hover:text-white p-1.5 rounded-lg hover:bg-zinc-800 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 w-full bg-zinc-950 relative">
              <iframe
                src={`http://localhost:5173/#/editor?loadJob=${encodeURIComponent(embeddedOpenReelJob)}`}
                className="w-full h-full border-0"
                allow="camera; microphone; display-capture; clipboard-read; clipboard-write; web-share"
                title="OpenReel Editor"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
