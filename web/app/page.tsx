"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
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
import {
  BGMTrackOption,
  StockVideoCandidate,
  MemeTemplateOption,
  CuratedMoment,
  CampaignSummary,
  JobSummary,
  ShotDetail,
  JobDetail,
} from "../lib/types";
import { MasterVideoPlayer } from "../components/MasterVideoPlayer";
import { ShotCard } from "../components/ShotCard";
import { OpenShortsPanel } from "../components/OpenShortsPanel";

// Code-split heavy modals to minimize initial bundle size and hydration cost
const MemeStudioModal = dynamic(
  () => import("../components/MemeStudioModal").then((m) => m.MemeStudioModal),
  { ssr: false }
);
const BrollSwapModal = dynamic(
  () => import("../components/BrollSwapModal").then((m) => m.BrollSwapModal),
  { ssr: false }
);
const InsertCutawayModal = dynamic(
  () => import("../components/InsertCutawayModal").then((m) => m.InsertCutawayModal),
  { ssr: false }
);
const CuratedMomentsModal = dynamic(
  () => import("../components/CuratedMomentsModal").then((m) => m.CuratedMomentsModal),
  { ssr: false }
);
const HdrUpscaleModal = dynamic(
  () => import("../components/HdrUpscaleModal").then((m) => m.HdrUpscaleModal),
  { ssr: false }
);
const OpenReelExportModal = dynamic(
  () => import("../components/OpenReelModals").then((m) => m.OpenReelExportModal),
  { ssr: false }
);
const EmbeddedOpenReelModal = dynamic(
  () => import("../components/OpenReelModals").then((m) => m.EmbeddedOpenReelModal),
  { ssr: false }
);
const DiffusionStudioModal = dynamic(
  () => import("../components/DiffusionStudioModal").then((m) => m.DiffusionStudioModal),
  { ssr: false }
);

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
  const jobDetailsCache = useRef<Record<string, JobDetail>>({});
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
  const [subtitlesBehindSubject, setSubtitlesBehindSubject] = useState<boolean>(false);
  const [subtitleMotion, setSubtitleMotion] = useState<string>("word-pop");
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

  // OpenReel & Diffusion Studio Integration State
  const [isOpenReelExporting, setIsOpenReelExporting] = useState<boolean>(false);
  const [openReelModalData, setOpenReelModalData] = useState<any>(null);
  const [embeddedOpenReelJob, setEmbeddedOpenReelJob] = useState<string | null>(null);
  const [embeddedOpenReelEngine, setEmbeddedOpenReelEngine] = useState<string | undefined>(undefined);
  const [embeddedDiffusionJob, setEmbeddedDiffusionJob] = useState<string | null>(null);

  // Campaigns & Curated Moments State
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("default");
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

  // Fetch essential studio resources on mount (BGM and Campaigns)
  const fetchEssentialResources = async () => {
    try {
      const [bgmRes, campRes] = await Promise.all([
        fetch("/api/bgm/tracks"),
        fetch("/api/campaigns"),
      ]);
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

  // Heavy catalogs (Meme templates ~60KB, SFX ~62KB) are loaded lazily on demand
  const loadMemeTemplatesOnDemand = async () => {
    if (memeTemplates.length > 0) return;
    try {
      const res = await fetch("/api/memes/templates?limit=120");
      if (res.ok) {
        const data = await res.json();
        setMemeTemplates(data);
      }
    } catch (e) {
      console.error("Failed to load meme templates:", e);
    }
  };

  const loadSfxCatalogOnDemand = async () => {
    if (sfxCatalog.length > 0) return;
    try {
      const res = await fetch("/api/sfx-catalog");
      if (res.ok) {
        const data = await res.json();
        setSfxCatalog(data);
      }
    } catch (e) {
      console.error("Failed to load SFX catalog:", e);
    }
  };

  useEffect(() => {
    fetchEssentialResources();
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

  const handleAutoGenerateMeme = useCallback(async (shotId: string) => {
    const currentId = selectedJobIdRef.current;
    if (!currentId) return;
    setIsAutoGeneratingMeme((prev) => ({ ...prev, [shotId]: true }));
    try {
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(currentId)}/shots/${encodeURIComponent(shotId)}/auto-meme`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        showToast(`AI generated unique meme: ${data.shot?.meme_template || "Meme"}!`);
        const jres = await fetch(`/api/jobs/${encodeURIComponent(currentId)}`);
        if (jres.ok) {
          const updated = await jres.json();
          setSelectedJob(updated);
          if (jobDetailsCache.current) {
            jobDetailsCache.current[currentId] = updated;
          }
        }
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Auto-meme generation failed: ${err.detail || "Server error"}`);
      }
    } catch (e) {
      alert("Error auto-generating meme: " + e);
    } finally {
      setIsAutoGeneratingMeme((prev) => ({ ...prev, [shotId]: false }));
    }
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

    loadMemeTemplatesOnDemand();
    loadSfxCatalogOnDemand();
    setShowMemeModal(true);
  };

  const openStandaloneMemeStudio = () => {
    loadMemeTemplatesOnDemand();
    loadSfxCatalogOnDemand();
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
          subtitles_behind_subject: subtitlesBehindSubject,
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
      alert("No active edit plan to export to the Timeline Editor.");
      return;
    }
    setIsOpenReelExporting(true);
    showToast("Exporting non-destructive editable project...");
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
        showToast("🎬 Editable project exported successfully!");
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Export failed: ${err.detail || "Server error"}`);
      }
    } catch (e) {
      alert("Error exporting editable project: " + e);
    } finally {
      setIsOpenReelExporting(false);
    }
  };

  const handleUpdateSettings = async (partial: {
    subtitles_enabled?: boolean;
    subtitle_style?: string;
    subtitle_position?: string;
    subtitles_behind_subject?: boolean;
    caption_motion?: string;
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

  const handleTrimShot = useCallback(async (shotId: string, newStart: number, newEnd: number) => {
    const currentId = selectedJobIdRef.current;
    if (!currentId) return;
    const clampedStart = Math.max(0, Math.round(newStart * 10) / 10);
    const clampedEnd = Math.max(clampedStart + 0.3, Math.round(newEnd * 10) / 10);

    setIsTrimming((prev) => ({ ...prev, [shotId]: true }));
    try {
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(currentId)}/shots/${encodeURIComponent(shotId)}`,
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
        setSelectedJob((prev) => {
          if (!prev || !prev.edit_plan) return prev;
          const updated = {
            ...prev,
            edit_plan: {
              ...prev.edit_plan,
              shots: data.shots,
            },
          };
          if (jobDetailsCache.current) {
            jobDetailsCache.current[currentId] = updated;
          }
          return updated;
        });
        await handleRerenderMaster();
      } else {
        const err = await res.json().catch(() => ({}));
        showToast(`Trim failed: ${err.detail || "Invalid timestamp"}`);
      }
    } catch (err) {
      console.error("Error trimming shot:", err);
    } finally {
      setIsTrimming((prev) => ({ ...prev, [shotId]: false }));
    }
  }, []);

  const handleDeleteShot = useCallback(async (shotId: string) => {
    const currentId = selectedJobIdRef.current;
    if (!currentId) return;
    if (!confirm(`Are you sure you want to remove Cutaway ${shotId}?`)) return;

    try {
      const res = await fetch(
        `/api/jobs/${encodeURIComponent(currentId)}/shots/${encodeURIComponent(shotId)}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        showToast(`Removed Cutaway ${shotId} — re-rendering exact EditPlan...`);
        setSelectedJob((prev) => {
          if (!prev || !prev.edit_plan) return prev;
          const updated = {
            ...prev,
            edit_plan: {
              ...prev.edit_plan,
              shots: prev.edit_plan.shots.filter((s) => s.shot_id !== shotId),
            },
          };
          if (jobDetailsCache.current) {
            jobDetailsCache.current[currentId] = updated;
          }
          return updated;
        });
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to delete cutaway: ${err.detail || "Server error"}`);
      }
    } catch (err) {
      alert("Error deleting cutaway: " + err);
    }
  }, []);

  const openInsertCutawayAtTime = (targetTime?: number) => {
    const time = targetTime !== undefined ? targetTime : (masterVideoRef.current?.currentTime || 0);
    setInsertCutawayTime(Math.round(time * 10) / 10);
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

  const handleSearchStock = useCallback(async (query: string) => {
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
  }, []);

  const openSwapModalForShot = useCallback((shot: ShotDetail) => {
    setSwapTargetShot(shot);
    setSwapTab("search");
    const initQuery = shot.asset_title || shot.dialogue_quote || "focused professional";
    setSwapSearchQuery(initQuery);
    setShowSwapModal(true);
    handleSearchStock(initQuery);
  }, [handleSearchStock]);

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

  // Instant job selection with in-memory detail cache
  const handleSelectJob = (jobId: string) => {
    setSelectedJobId(jobId);
    setShowUploadMode(false);
    setShowProjectPicker(false);
    if (jobDetailsCache.current[jobId]) {
      setSelectedJob(jobDetailsCache.current[jobId]);
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
          handleSelectJob(preferred.job_id);
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
    const interval = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      fetchData();
    }, 5000);
    const handleVis = () => {
      if (!document.hidden) fetchData();
    };
    document.addEventListener("visibilitychange", handleVis);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVis);
    };
  }, []);

  // Fetch selected job detail with in-memory caching and AbortController
  useEffect(() => {
    if (!selectedJobId) return;
    let isMounted = true;
    const abortController = new AbortController();

    const fetchDetail = async () => {
      try {
        const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJobId)}`, {
          signal: abortController.signal,
        });
        if (res.ok && isMounted) {
          const detail = await res.json();
          jobDetailsCache.current[detail.job_id] = detail;
          setSelectedJob(detail);
          setFeedbackSubmitted(false);
          if (detail.edit_plan?.render_settings) {
            const rs = detail.edit_plan.render_settings;
            if (rs.subtitles_enabled !== undefined) setSubtitlesEnabled(rs.subtitles_enabled);
            if (rs.subtitle_style) setSubtitleStyle(rs.subtitle_style);
            if (rs.subtitle_position) setSubtitlePosition(rs.subtitle_position);
            if (rs.subtitles_behind_subject !== undefined) setSubtitlesBehindSubject(rs.subtitles_behind_subject);
            if (rs.caption_motion) setSubtitleMotion(rs.caption_motion);
            if (rs.bgm_track_id !== undefined) setSelectedBgmId(rs.bgm_track_id || "none");
            if (rs.bgm_volume !== undefined) setBgmVolume(rs.bgm_volume);
            if (rs.bgm_ducking !== undefined) setBgmDucking(rs.bgm_ducking);
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          console.error("Failed to fetch job detail:", err);
        }
      }
    };

    fetchDetail();

    // Only poll detail when job is actively processing (not terminal)
    let detailInterval: NodeJS.Timeout | null = null;
    const status = selectedJob?.status;
    if (status && status !== "COMPLETED" && status !== "FAILED") {
      detailInterval = setInterval(() => {
        if (typeof document !== "undefined" && document.hidden) return;
        fetchDetail();
      }, 3000);
    }

    return () => {
      isMounted = false;
      abortController.abort();
      if (detailInterval) clearInterval(detailInterval);
    };
  }, [selectedJobId, selectedJob?.status]);

  // Jump to specific cutaway in master video
  const jumpToCutaway = useCallback((startTime: number) => {
    if (masterVideoRef.current) {
      masterVideoRef.current.currentTime = startTime;
      masterVideoRef.current.play().catch(() => {});
    }
  }, []);

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
                    {c.name}
                  </option>
                ))}
                {campaigns.length === 0 && (
                  <option value="default">⚡ Default Viral Shorts</option>
                )}
              </select>
            </div>
            {(campaigns.find((c) => c.id === selectedCampaignId)?.curated_moments?.length ?? 0) > 0 && (
              <button
                type="button"
                onClick={() => setShowMomentsModal(true)}
                className="bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all"
                title="Browse curated moments and campaign rules"
              >
                <Sparkles className="w-3 h-3 text-emerald-400" />
                <span>Moments & Rules</span>
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

                  <div className="max-h-60 overflow-y-auto space-y-1 pr-1 overscroll-contain">
                    {jobs.map((j) => (
                      <div
                        key={j.job_id}
                        className={`p-2 rounded-xl text-xs flex items-center justify-between transition-colors group content-auto ${
                          j.job_id === selectedJobId
                            ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                            : "hover:bg-zinc-800/90 text-zinc-300 border border-transparent"
                        }`}
                      >
                        <div
                          onClick={() => {
                            handleSelectJob(j.job_id);
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
          {(() => {
            const activeCampaign = campaigns.find((c) => c.id === selectedCampaignId);
            return (
              <div className="max-w-2xl mx-auto bg-zinc-950/70 border border-zinc-800 rounded-2xl p-3.5 text-left flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">⚡</span>
                  <div>
                    <h4 className="text-xs font-bold text-zinc-200">{activeCampaign?.name || "Default Viral Short-Form Preset"}</h4>
                    <p className="text-[11px] text-zinc-400">
                      {activeCampaign?.description || "High-velocity meme hooks, phonk BGM with voice ducking, Hormozi kinetic captions."}
                    </p>
                  </div>
                </div>
                {(activeCampaign?.curated_moments?.length ?? 0) > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowMomentsModal(true)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3.5 py-2 rounded-xl shadow-md shadow-emerald-600/25 transition-all flex items-center gap-1.5"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Curated Moments & Rules</span>
                  </button>
                )}
              </div>
            );
          })()}

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
                    <span className="text-[9px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full">
                      {selectedJob.campaign_id || "Default"}
                    </span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    AI-directed B-roll cuts • Kinetic captions • Campaign-optimized edit
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

                {/* Open in Timeline Editor */}
                <button
                  onClick={() => selectedJob && setEmbeddedOpenReelJob(selectedJob.job_id)}
                  className="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 hover:from-blue-500 hover:to-violet-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
                  title="Launch the editable timeline inside this dashboard"
                >
                  <Film className="w-3.5 h-3.5 text-indigo-200" />
                  <span>🎬 Open Timeline Editor</span>
                </button>

                {/* Open in Diffusion Studio Button */}
                <button
                  onClick={() => selectedJob && setEmbeddedDiffusionJob(selectedJob.job_id)}
                  className="bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-purple-600/30 transition-all hover:scale-[1.02]"
                  title="Launch Diffusion Studio WebCodecs composition player & inspector"
                >
                  <Sparkles className="w-3.5 h-3.5 text-purple-200" />
                  <span>✨ Diffusion Studio</span>
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

                    {/* Caption Motion */}
                    <div className="space-y-1 pt-1">
                      <label className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">
                        Caption Motion
                      </label>
                      <select
                        value={subtitleMotion}
                        onChange={async (e) => {
                          const profile = e.target.value;
                          setSubtitleMotion(profile);
                          try {
                            const res = await fetch(
                              `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/caption-motion`,
                              {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ profile }),
                              }
                            );
                            if (!res.ok) throw new Error("Motion update failed");
                            showToast(`Caption motion: ${profile}`);
                          } catch (err) {
                            console.error("Failed to update caption motion:", err);
                          }
                        }}
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-xl text-xs text-zinc-200 px-3 py-2 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="word-pop">Word Pop</option>
                        <option value="bounce">Bounce</option>
                        <option value="typewriter">Typewriter</option>
                        <option value="focus">True Focus</option>
                        <option value="scramble">Text Scramble</option>
                        <option value="slide-up">Slide Up</option>
                      </select>
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

                    {/* Behind Subject */}
                    <div className="flex items-center justify-between pt-1">
                      <div>
                        <span className="text-[11px] text-zinc-400">Behind Subject:</span>
                        <p className="text-[9px] text-zinc-600">Put captions behind the detected speaker when possible.</p>
                      </div>
                      <label className="flex items-center gap-2 cursor-pointer text-xs">
                        <span className="text-[10px] text-zinc-500">{subtitlesBehindSubject ? "On" : "Off"}</span>
                        <input
                          type="checkbox"
                          checked={subtitlesBehindSubject}
                          onChange={(e) => {
                            const enabled = e.target.checked;
                            setSubtitlesBehindSubject(enabled);
                            handleUpdateSettings({ subtitles_behind_subject: enabled });
                          }}
                          className="w-4 h-4 accent-amber-500 rounded cursor-pointer"
                        />
                      </label>
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
            <MasterVideoPlayer
              selectedJob={selectedJob}
              totalDuration={totalDuration}
              shots={shots}
              hdrAvailable={hdrAvailable}
              viewingHdrVideo={viewingHdrVideo}
              setViewingHdrVideo={setViewingHdrVideo}
              isUpscalingHdr={isUpscalingHdr}
              hdrProgress={hdrProgress}
              hdrFps={hdrFps}
              onOpenInsertCutaway={(time) => openInsertCutawayAtTime(time)}
              onDeleteJob={(job) => setJobToDelete(job)}
              onLaunchOpenReel={(id) => setEmbeddedOpenReelJob(id)}
              videoRef={masterVideoRef}
            />
            <OpenShortsPanel jobId={selectedJob.job_id} />
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
                  <ShotCard
                    key={shot.shot_id || idx}
                    shot={shot}
                    idx={idx}
                    isAutoGeneratingMeme={Boolean(isAutoGeneratingMeme[shot.shot_id])}
                    isTrimming={Boolean(isTrimming[shot.shot_id])}
                    onOpenSwapModal={openSwapModalForShot}
                    onAutoGenerateMeme={handleAutoGenerateMeme}
                    onJumpToCutaway={jumpToCutaway}
                    onDeleteShot={handleDeleteShot}
                    onTrimShot={handleTrimShot}
                  />
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

      {/* MODALS: Dynamically imported and rendered on demand */}
      <MemeStudioModal
        isOpen={showMemeModal}
        onClose={() => setShowMemeModal(false)}
        isStandaloneMode={isStandaloneMode}
        memeTargetShot={memeTargetShot}
        memeTemplates={memeTemplates}
        selectedTemplateKey={selectedTemplateKey}
        setSelectedTemplateKey={setSelectedTemplateKey}
        memeCaptions={memeCaptions}
        setMemeCaptions={setMemeCaptions}
        selectedSfxFile={selectedSfxFile}
        setSelectedSfxFile={setSelectedSfxFile}
        sfxCatalog={sfxCatalog}
        memeSearchQuery={memeSearchQuery}
        setMemeSearchQuery={setMemeSearchQuery}
        isGeneratingMeme={isGeneratingMeme}
        isAutoGeneratingMeme={isAutoGeneratingMeme}
        handleAutoGenerateMeme={handleAutoGenerateMeme}
        handleGenerateMeme={handleGenerateMeme}
        handleSelectTemplate={handleSelectTemplate}
        standaloneMemeResult={standaloneMemeResult}
      />

      <BrollSwapModal
        isOpen={showSwapModal}
        onClose={() => setShowSwapModal(false)}
        swapTargetShot={swapTargetShot}
        swapTab={swapTab}
        setSwapTab={setSwapTab}
        swapSearchQuery={swapSearchQuery}
        setSwapSearchQuery={setSwapSearchQuery}
        stockCandidates={stockCandidates}
        isSearchingStock={isSearchingStock}
        isSwappingStock={isSwappingStock}
        handleSearchStock={handleSearchStock}
        handleSelectStockCandidate={handleSelectStockCandidate}
        isUploadingCustom={isUploadingCustom}
        handleCustomVideoUpload={handleCustomVideoUpload}
      />

      <InsertCutawayModal
        isOpen={showInsertCutawayModal}
        onClose={() => setShowInsertCutawayModal(false)}
        insertCutawayTime={insertCutawayTime}
        setInsertCutawayTime={setInsertCutawayTime}
        insertCutawayDur={insertCutawayDur}
        setInsertCutawayDur={setInsertCutawayDur}
        insertCutawayStyle={insertCutawayStyle}
        setInsertCutawayStyle={setInsertCutawayStyle}
        insertCutawayPrompt={insertCutawayPrompt}
        setInsertCutawayPrompt={setInsertCutawayPrompt}
        insertCutawayMemeTemplate={insertCutawayMemeTemplate}
        setInsertCutawayMemeTemplate={setInsertCutawayMemeTemplate}
        isInsertingCutaway={isInsertingCutaway}
        handleConfirmInsertCutaway={handleConfirmInsertCutaway}
      />

      <CuratedMomentsModal
        isOpen={showMomentsModal}
        onClose={() => setShowMomentsModal(false)}
        campaigns={campaigns}
        selectedCampaignId={selectedCampaignId}
        curatedMomentsTab={curatedMomentsTab}
        setCuratedMomentsTab={setCuratedMomentsTab}
        momentSearchQuery={momentSearchQuery}
        setMomentSearchQuery={setMomentSearchQuery}
        momentFilterAngle={momentFilterAngle}
        setMomentFilterAngle={setMomentFilterAngle}
        onSelectMoment={(m) => {
          navigator.clipboard?.writeText(
            `Moment ${m.moment_id} (${m.timestamp_range})\nHook: ${m.screen_hook}\nCaption: ${m.post_caption}`
          );
          showToast(`Selected Moment ${m.moment_id}! Hook & timestamps copied to clipboard.`);
          setShowMomentsModal(false);
          setShowUploadMode(true);
        }}
      />

      <HdrUpscaleModal
        isOpen={showHdrModal}
        onClose={() => setShowHdrModal(false)}
        hdrScale={hdrScale}
        setHdrScale={setHdrScale}
        hdrTone={hdrTone}
        setHdrTone={setHdrTone}
        hdrFastMode={hdrFastMode}
        setHdrFastMode={setHdrFastMode}
        isUpscalingHdr={isUpscalingHdr}
        hdrProgress={hdrProgress}
        handleStartHdrUpscale={handleStartHdrUpscale}
      />

      <OpenReelExportModal
        openReelModalData={openReelModalData}
        onClose={() => setOpenReelModalData(null)}
        onLaunchEmbedded={(id) => setEmbeddedOpenReelJob(id)}
        selectedJobId={selectedJob?.job_id}
      />

      <EmbeddedOpenReelModal
        embeddedOpenReelJob={embeddedOpenReelJob}
        engine={embeddedOpenReelEngine}
        onClose={() => {
          setEmbeddedOpenReelJob(null);
          setEmbeddedOpenReelEngine(undefined);
        }}
      />

      {embeddedDiffusionJob && (
        <DiffusionStudioModal
          jobId={embeddedDiffusionJob}
          onClose={() => setEmbeddedDiffusionJob(null)}
          onHandoffToOpenReel={(id, engine) => {
            setEmbeddedDiffusionJob(null);
            setEmbeddedOpenReelEngine(engine || "diffusion");
            setEmbeddedOpenReelJob(id);
          }}
        />
      )}
    </div>
  );
}
