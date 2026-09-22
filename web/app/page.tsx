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
  Type
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
  const [insertCutawayDur, setInsertCutawayDur] = useState<number>(2.5);
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

  // Fetch Meme templates, SFX catalog, and BGM tracks
  const fetchResources = async () => {
    try {
      const [tRes, sfxRes, bgmRes] = await Promise.all([
        fetch("/api/memes/templates?limit=120"),
        fetch("/api/sfx-catalog"),
        fetch("/api/bgm/tracks")
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
    } catch (e) {
      console.error("Failed to load studio resources:", e);
    }
  };

  useEffect(() => {
    fetchResources();
  }, []);

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
            duration: 2.8
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
            duration: memeTargetShot.duration || 2.8
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
        body: JSON.stringify({ url: youtubeUrl.trim() }),
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
    setIsUploading(true);
    setUploadProgress(20);

    const formData = new FormData();
    formData.append("file", file);

    try {
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
        alert("Upload failed. Please ensure the file is an MP4, MOV, or MKV.");
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
              One video at a time • Emotional metaphors • Stockpile footage • 9:16 vertical render
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2.5">
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

          {/* Meme Studio Standalone Button */}
          <button
            onClick={openStandaloneMemeStudio}
            className="bg-fuchsia-600 hover:bg-fuchsia-500 text-white text-xs font-semibold px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-md shadow-fuchsia-600/20 transition-all hover:scale-[1.02]"
            title="Browse all 1,036 HD Meme Templates and generate standalone vertical cutaways"
          >
            <Sparkles className="w-3.5 h-3.5 text-fuchsia-200" />
            <span>🎭 Meme Studio</span>
          </button>

          {/* New Clip Button */}
          <button
            onClick={() => {
              setShowUploadMode(true);
              setShowProjectPicker(false);
            }}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-md shadow-indigo-600/20 transition-all hover:scale-[1.02]"
          >
            <Plus className="w-3.5 h-3.5" />
            Process New Clip
          </button>

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

          {/* Tab Selector: Upload File vs Import YouTube */}
          <div className="flex items-center justify-center gap-2 max-w-md mx-auto bg-zinc-950 p-1.5 rounded-2xl border border-zinc-800">
            <button
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
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]);
              }}
              onClick={() => fileInputRef.current?.click()}
              className="max-w-2xl mx-auto border-2 border-dashed border-indigo-500/40 hover:border-indigo-400 bg-indigo-500/5 hover:bg-indigo-500/10 rounded-3xl p-12 text-center cursor-pointer transition-all group shadow-inner"
            >
              <input
                type="file"
                ref={fileInputRef}
                accept="video/mp4,video/quicktime,video/x-matroska"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
                }}
              />
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform shadow-lg">
                <Upload className="w-8 h-8" />
              </div>
              <h3 className="font-bold text-base text-zinc-100">Drop your raw MP4 or MOV here</h3>
              <p className="text-xs text-zinc-400 mt-1.5">Single-clip pipeline • Up to 500MB • Zero watermarks guarantee</p>

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
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <span>Clipper Video Studio</span>
                    <span className="text-[9px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full">
                      Viral Ready
                    </span>
                  </h3>
                  <p className="text-[11px] text-zinc-400">
                    Alex Hormozi kinetic word-highlights • Royalty-Free BGM library • Voice sidechain auto-ducking
                  </p>
                </div>
              </div>

              {/* Re-render Master Button */}
              <button
                onClick={handleRerenderMaster}
                disabled={isRerenderingMaster}
                className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 disabled:opacity-50 text-black text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02]"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRerenderingMaster ? "animate-spin" : ""}`} />
                <span>{isRerenderingMaster ? "Burning Subtitles & BGM..." : "⚡ Re-render Master Edit"}</span>
              </button>
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
              <div className="bg-black rounded-2xl overflow-hidden border border-zinc-800 flex justify-center py-2 shadow-2xl relative">
                <video
                  ref={masterVideoRef}
                  key={selectedJob.job_id}
                  controls
                  playsInline
                  onTimeUpdate={handleTimeUpdate}
                  className="max-h-[500px] w-auto rounded-xl shadow-lg aspect-[9/16]"
                  src={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/video`}
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
                        {shot.style === "meme" && (
                          <span className="text-[10px] font-bold bg-fuchsia-500/15 text-fuchsia-400 border border-fuchsia-500/30 px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                            🎭 Meme Cutaway
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

                        {/* Convert to Meme / Edit Meme Button */}
                        <button
                          onClick={() => openMemeCustomizerForShot(shot)}
                          className="text-[11px] font-semibold text-fuchsia-300 hover:text-white bg-fuchsia-500/15 hover:bg-fuchsia-600/30 border border-fuchsia-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
                          title="Transform or customize this cutaway with any of 1,036 HD Meme templates"
                        >
                          <Sparkles className="w-3 h-3 text-fuchsia-400" />
                          <span>{shot.style === "meme" ? "Edit Meme" : "Make Meme Cutaway"}</span>
                        </button>

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
                  className="text-[11px] font-semibold text-indigo-300 hover:text-white bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/30 px-2.5 py-1 rounded-lg shrink-0 transition-all"
                >
                  📋 Use as Caption
                </button>
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
                      accept="video/mp4,video/quicktime,video/x-matroska"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files?.[0]) handleCustomVideoUpload(e.target.files[0]);
                      }}
                    />
                    <Upload className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
                    <h4 className="text-sm font-bold text-zinc-100">Upload custom video for this shot</h4>
                    <p className="text-xs text-zinc-400 mt-1">
                      Supports MP4, MOV. Will be automatically formatted to 1080x1920 9:16 vertical.
                    </p>
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
    </div>
  );
}
