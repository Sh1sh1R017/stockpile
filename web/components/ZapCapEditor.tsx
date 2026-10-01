"use client";

import React, { useState, useEffect } from "react";
import {
  Type,
  Sliders,
  Film,
  Sparkles,
  Download,
  ExternalLink,
  CheckCircle2,
  Palette,
  MoveVertical,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Scissors,
  Layers,
  ShieldCheck,
  RefreshCw,
  Smile,
  Flame,
  FileCode,
} from "lucide-react";
import { JobDetail, ShotDetail, BGMTrackOption } from "../lib/types";

export interface ZapCapPresetMeta {
  key: string;
  name: string;
  category: string;
  font_family: string;
  font_weight: string;
  font_size: number;
  uppercase: boolean;
  fill_color: string;
  highlight_color: string;
  secondary_color: string;
  stroke_color: string;
  stroke_width: number;
  shadow_color: string;
  shadow_blur: number;
  letter_spacing: number;
  line_spacing: number;
  default_animation: string;
  description: string;
}

export interface ZapCapSettings {
  preset: string;
  wordsPerBeat: number;
  animation: string;
  mainColor: string;
  secondColor: string;
  thirdColor: string;
  yPercent: number;
  enableEmojis: boolean;
  behindSubject: boolean;
}

interface ZapCapEditorProps {
  selectedJob: JobDetail;
  shots: ShotDetail[];
  bgmTracks: BGMTrackOption[];
  currentTime: number;
  onJumpToTime: (time: number) => void;
  onOpenInsertCutaway: (time: number) => void;
  onOpenSwapBroll: (shot: ShotDetail) => void;
  onLaunchOpenReel: (jobId: string) => void;
  onRerenderMaster: () => Promise<void>;
  isRerendering: boolean;
  onSettingsUpdated?: (newSettings: any) => void;
}

const DEFAULT_PRESETS: ZapCapPresetMeta[] = [
  {
    key: "hormozi",
    name: "Hormozi",
    category: "Impactful",
    font_family: "Montserrat, Impact, sans-serif",
    font_weight: "Black",
    font_size: 64,
    uppercase: true,
    fill_color: "#FFFFFF",
    highlight_color: "#FFE600",
    secondary_color: "#00FF66",
    stroke_color: "#000000",
    stroke_width: 8,
    shadow_color: "rgba(0, 0, 0, 0.9)",
    shadow_blur: 10,
    letter_spacing: 0.04,
    line_spacing: 1.1,
    default_animation: "pop",
    description: "Bold yellow punch with heavy black outline. High-converting creator classic.",
  },
  {
    key: "beast",
    name: "Beast",
    category: "Impactful",
    font_family: "Komika Axis, Arial Black, sans-serif",
    font_weight: "Black",
    font_size: 68,
    uppercase: true,
    fill_color: "#FFFFFF",
    highlight_color: "#00E5FF",
    secondary_color: "#FF0055",
    stroke_color: "#000000",
    stroke_width: 10,
    shadow_color: "rgba(0, 0, 0, 0.95)",
    shadow_blur: 12,
    letter_spacing: 0.03,
    line_spacing: 1.1,
    default_animation: "bounce",
    description: "High-energy cyan and punch magenta outline. Beast style retention hook.",
  },
  {
    key: "clean",
    name: "Clean",
    category: "Minimal",
    font_family: "Inter, -apple-system, sans-serif",
    font_weight: "Bold",
    font_size: 52,
    uppercase: false,
    fill_color: "#FFFFFF",
    highlight_color: "#38BDF8",
    secondary_color: "#A78BFA",
    stroke_color: "rgba(0, 0, 0, 0.6)",
    stroke_width: 3,
    shadow_color: "rgba(0, 0, 0, 0.5)",
    shadow_blur: 6,
    letter_spacing: 0.0,
    line_spacing: 1.2,
    default_animation: "fade",
    description: "Ultra-sleek tech/business aesthetic with subtle atmospheric glow.",
  },
  {
    key: "gstaad",
    name: "Gstaad",
    category: "Editorial",
    font_family: "Playfair Display, Georgia, serif",
    font_weight: "Bold",
    font_size: 58,
    uppercase: true,
    fill_color: "#F8F6F0",
    highlight_color: "#D4AF37",
    secondary_color: "#E2D4B7",
    stroke_color: "#1A1A1A",
    stroke_width: 4,
    shadow_color: "rgba(0, 0, 0, 0.8)",
    shadow_blur: 8,
    letter_spacing: 0.08,
    line_spacing: 1.25,
    default_animation: "scale",
    description: "Old money luxury serif with warm gold highlights for high-status content.",
  },
  {
    key: "neon",
    name: "Neon",
    category: "Cyber",
    font_family: "Orbitron, Montserrat, sans-serif",
    font_weight: "Black",
    font_size: 60,
    uppercase: true,
    fill_color: "#FFFFFF",
    highlight_color: "#00F0FF",
    secondary_color: "#FF0077",
    stroke_color: "#050510",
    stroke_width: 6,
    shadow_color: "rgba(0, 240, 255, 0.8)",
    shadow_blur: 14,
    letter_spacing: 0.05,
    line_spacing: 1.15,
    default_animation: "pop",
    description: "Cyberpunk synthwave glow with electric cyan and hot magenta aura.",
  },
  {
    key: "ember",
    name: "Ember",
    category: "Playful",
    font_family: "Montserrat, Arial Black, sans-serif",
    font_weight: "Black",
    font_size: 64,
    uppercase: true,
    fill_color: "#FFFFFF",
    highlight_color: "#FF5500",
    secondary_color: "#FFCC00",
    stroke_color: "#1F0800",
    stroke_width: 8,
    shadow_color: "rgba(255, 85, 0, 0.6)",
    shadow_blur: 12,
    letter_spacing: 0.03,
    line_spacing: 1.1,
    default_animation: "bounce",
    description: "Fiery orange and ember gold punch for high-octane motivational speeches.",
  },
];

export const ZapCapEditor: React.FC<ZapCapEditorProps> = ({
  selectedJob,
  shots,
  bgmTracks,
  currentTime,
  onJumpToTime,
  onOpenInsertCutaway,
  onOpenSwapBroll,
  onLaunchOpenReel,
  onRerenderMaster,
  isRerendering,
  onSettingsUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<"font" | "caption" | "brolls" | "effects" | "publish">("font");
  const [presets, setPresets] = useState<ZapCapPresetMeta[]>(DEFAULT_PRESETS);
  const [selectedPresetKey, setSelectedPresetKey] = useState<string>("hormozi");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  // Caption Settings State
  const [wordsPerBeat, setWordsPerBeat] = useState<number>(3);
  const [animation, setAnimation] = useState<string>("pop");
  const [mainColor, setMainColor] = useState<string>("#FFFFFF");
  const [secondColor, setSecondColor] = useState<string>("#FFE600");
  const [thirdColor, setThirdColor] = useState<string>("#00FF66");
  const [yPercent, setYPercent] = useState<number>(84);
  const [enableEmojis, setEnableEmojis] = useState<boolean>(true);
  const [behindSubject, setBehindSubject] = useState<boolean>(true);
  const [subtitlesEnabled, setSubtitlesEnabled] = useState<boolean>(true);

  // Audio / BGM State
  const [selectedBgmId, setSelectedBgmId] = useState<string>("chill_lofi");
  const [bgmVolume, setBgmVolume] = useState<number>(0.16);
  const [bgmDucking, setBgmDucking] = useState<boolean>(true);
  const [isPlayingBgmPreview, setIsPlayingBgmPreview] = useState<string | null>(null);
  const bgmAudioRef = React.useRef<HTMLAudioElement | null>(null);

  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  // Initialize settings from selectedJob
  useEffect(() => {
    if (!selectedJob) return;
    const settings = selectedJob.edit_plan?.render_settings || {};
    const initPreset = settings.preset || settings.subtitle_style || "hormozi";
    setSelectedPresetKey(initPreset);
    setSubtitlesEnabled(settings.subtitles_enabled !== false);
    setWordsPerBeat(Number(settings.words_per_beat) || 3);
    setAnimation(settings.caption_motion || "pop");
    setBehindSubject(
      settings.subtitles_behind_subject === undefined
        ? true
        : Boolean(settings.subtitles_behind_subject)
    );
    setEnableEmojis(settings.enable_emojis !== false);
    if (settings.subtitle_y_percent !== undefined) {
      setYPercent(Number(settings.subtitle_y_percent));
    }
    if (settings.custom_colors) {
      if (settings.custom_colors.main) setMainColor(settings.custom_colors.main);
      if (settings.custom_colors.second) setSecondColor(settings.custom_colors.second);
      if (settings.custom_colors.third) setThirdColor(settings.custom_colors.third);
    }
    if (settings.bgm_track_id) setSelectedBgmId(settings.bgm_track_id);
    if (settings.bgm_volume !== undefined) setBgmVolume(Number(settings.bgm_volume));
    if (settings.bgm_ducking !== undefined) setBgmDucking(Boolean(settings.bgm_ducking));
  }, [selectedJob]);

  // Fetch full 21 presets from backend
  useEffect(() => {
    fetch("/api/caption-presets")
      .then((res) => res.json())
      .then((data) => {
        if (data.presets && Array.isArray(data.presets) && data.presets.length > 0) {
          setPresets(data.presets);
        }
      })
      .catch(() => {
        // Fallback to default presets
      });
  }, []);

  const handleSelectPreset = (p: ZapCapPresetMeta) => {
    setSelectedPresetKey(p.key);
    setMainColor(p.fill_color);
    setSecondColor(p.highlight_color);
    setThirdColor(p.secondary_color);
    setAnimation(p.default_animation);
    saveSettings({
      preset: p.key,
      custom_colors: { main: p.fill_color, second: p.highlight_color, third: p.secondary_color },
      caption_motion: p.default_animation,
    });
  };

  const saveSettings = async (patch: Record<string, any>) => {
    if (!selectedJob) return;
    setIsSaving(true);
    try {
      const payload = {
        subtitles_enabled: subtitlesEnabled,
        preset: selectedPresetKey,
        subtitle_style: selectedPresetKey,
        words_per_beat: wordsPerBeat,
        caption_motion: animation,
        custom_colors: { main: mainColor, second: secondColor, third: thirdColor },
        subtitle_y_percent: yPercent,
        enable_emojis: enableEmojis,
        subtitles_behind_subject: behindSubject,
        bgm_track_id: selectedBgmId,
        bgm_volume: bgmVolume,
        bgm_ducking: bgmDucking,
        ...patch,
      };

      const res = await fetch(`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let message = "Failed to save";
        try {
          const body = await res.json();
          if (body?.detail) message = String(body.detail);
        } catch {
          // Keep the generic failure message when the backend did not return JSON.
        }
        setSaveStatus(message);
        return;
      }

      const data = await res.json();
      setSaveStatus("Saved");
      setTimeout(() => setSaveStatus(null), 2000);
      if (onSettingsUpdated) {
        onSettingsUpdated(data.render_settings);
      }
    } catch {
      setSaveStatus("Failed to save");
    } finally {
      setIsSaving(false);
    }
  };

  const toggleBgmPreview = (trackId: string) => {
    if (isPlayingBgmPreview === trackId) {
      if (bgmAudioRef.current) {
        bgmAudioRef.current.pause();
      }
      setIsPlayingBgmPreview(null);
    } else {
      if (!bgmAudioRef.current) {
        bgmAudioRef.current = new Audio();
      }
      bgmAudioRef.current.src = `/api/bgm/${encodeURIComponent(trackId)}/audio`;
      bgmAudioRef.current.volume = Math.min(1.0, bgmVolume * 3);
      bgmAudioRef.current.play().catch(() => {});
      setIsPlayingBgmPreview(trackId);
      bgmAudioRef.current.onended = () => setIsPlayingBgmPreview(null);
    }
  };

  const categories = ["All", "Impactful", "Minimal", "Playful", "Editorial", "Cyber", "Retro"];
  const filteredPresets = selectedCategory === "All"
    ? presets
    : presets.filter((p) => p.category.toLowerCase() === selectedCategory.toLowerCase());

  return (
    <div className="bg-zinc-900/90 border border-zinc-800 rounded-3xl p-5 shadow-2xl space-y-5">
      {/* Top Header & Navigation Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h2 className="text-base font-black text-zinc-100 uppercase tracking-wider">
              ZapCap Creator Studio
            </h2>
            <span className="text-[10px] bg-amber-400/20 text-amber-300 font-bold px-2 py-0.5 rounded-full border border-amber-400/30">
              V3 KINETIC
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Short-form rhythmic captions, 21 viral font presets, and YOLO behind-speaker layering.
          </p>
        </div>

        {/* 5 Creator Tabs */}
        <div className="flex items-center bg-zinc-950 p-1 rounded-2xl border border-zinc-800 self-start sm:self-auto">
          {[
            { id: "font", label: "Font", icon: Type },
            { id: "caption", label: "Caption", icon: Sliders },
            { id: "brolls", label: "B-Rolls", icon: Film },
            { id: "effects", label: "Effects", icon: Sparkles },
            { id: "publish", label: "Publish", icon: Download },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  isActive
                    ? "bg-gradient-to-r from-amber-500 to-yellow-500 text-black shadow-md shadow-amber-500/20"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Save indicator toast */}
      {saveStatus && (
        <div className="text-[11px] text-amber-300 bg-amber-950/60 border border-amber-500/40 px-3 py-1 rounded-xl flex items-center justify-between animate-fadeIn">
          <span>{saveStatus === "Saved" ? "✓ Changes auto-saved to EditPlan" : saveStatus}</span>
          {isSaving && <RefreshCw className="w-3 h-3 animate-spin text-amber-400" />}
        </div>
      )}

      {/* TAB 1: FONT PRESETS */}
      {activeTab === "font" && (
        <div className="space-y-4">
          {/* Category Filter Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-full font-bold whitespace-nowrap transition-all ${
                  selectedCategory === cat
                    ? "bg-zinc-100 text-black"
                    : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* 21 Preset Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[460px] overflow-y-auto pr-1">
            {filteredPresets.map((p) => {
              const isSelected = selectedPresetKey === p.key;
              return (
                <div
                  key={p.key}
                  onClick={() => handleSelectPreset(p)}
                  className={`cursor-pointer rounded-2xl p-3.5 border transition-all relative flex flex-col justify-between group ${
                    isSelected
                      ? "bg-gradient-to-b from-zinc-800 to-zinc-900 border-amber-400/90 shadow-lg shadow-amber-400/10 ring-1 ring-amber-400"
                      : "bg-zinc-950/70 border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/60"
                  }`}
                >
                  {/* Top Bar: Name & Category */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-black text-zinc-200 uppercase tracking-wide">
                      {p.name}
                    </span>
                    <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
                      {p.category}
                    </span>
                  </div>

                  {/* Typography Live Visual Preview */}
                  <div className="my-2 py-3 px-2 bg-black/60 rounded-xl border border-zinc-900 flex flex-col items-center justify-center min-h-[64px] text-center overflow-hidden">
                    <div
                      style={{
                        fontFamily: p.font_family,
                        fontWeight: p.font_weight.toLowerCase() === "black" ? 900 : 700,
                        textTransform: p.uppercase ? "uppercase" : "none",
                        letterSpacing: `${p.letter_spacing * 2}px`,
                      }}
                      className="text-base tracking-wide flex items-center gap-1.5 flex-wrap justify-center drop-shadow-md"
                    >
                      <span style={{ color: p.fill_color }}>SCALE</span>
                      <span
                        style={{
                          color: p.highlight_color,
                          textShadow: `0 0 10px ${p.highlight_color}66`,
                        }}
                        className="scale-105 inline-block"
                      >
                        $10M
                      </span>
                      <span style={{ color: p.fill_color }}>FAST</span>
                      <span className="text-sm">🔥</span>
                    </div>
                  </div>

                  {/* Description & Palette Dots */}
                  <div className="flex items-center justify-between pt-2 border-t border-zinc-900 text-[10px] text-zinc-400">
                    <span className="truncate max-w-[160px]">{p.description}</span>
                    <div className="flex items-center gap-1">
                      <span
                        className="w-2.5 h-2.5 rounded-full border border-black/40"
                        style={{ backgroundColor: p.fill_color }}
                      />
                      <span
                        className="w-2.5 h-2.5 rounded-full border border-black/40"
                        style={{ backgroundColor: p.highlight_color }}
                      />
                      <span
                        className="w-2.5 h-2.5 rounded-full border border-black/40"
                        style={{ backgroundColor: p.secondary_color }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: CAPTION CONTROLS */}
      {activeTab === "caption" && (
        <div className="space-y-5">
          {/* Top Master Toggle */}
          <div className="flex items-center justify-between p-3.5 bg-zinc-950 rounded-2xl border border-zinc-800">
            <div>
              <span className="text-xs font-bold text-zinc-100 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Kinetic Subtitles Enabled
              </span>
              <p className="text-[11px] text-zinc-400 mt-0.5">
                Renders animated ZapCap typography on master video and export timeline.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                const next = !subtitlesEnabled;
                setSubtitlesEnabled(next);
                saveSettings({ subtitles_enabled: next });
              }}
              className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors ${
                subtitlesEnabled ? "bg-amber-400 justify-end" : "bg-zinc-800 justify-start"
              }`}
            >
              <div
                className={`bg-black w-4 h-4 rounded-full shadow-md transform transition-transform ${
                  subtitlesEnabled ? "translate-x-0" : "translate-x-0"
                }`}
              />
            </button>
          </div>

          {/* Rhythmic Words Per Beat Slider */}
          <div className="p-4 bg-zinc-950 rounded-2xl border border-zinc-800 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-amber-400" />
                  Words Per Visible Beat
                </span>
                <p className="text-[10px] text-zinc-400">
                  Controls fast creator rhythm (1 to 4 words visible simultaneously).
                </p>
              </div>
              <span className="text-xs font-black px-2.5 py-1 bg-amber-400/20 text-amber-300 rounded-lg border border-amber-400/30">
                {wordsPerBeat} {wordsPerBeat === 1 ? "Word" : "Words"}
              </span>
            </div>

            <div className="space-y-1.5">
              <input
                type="range"
                min={1}
                max={4}
                step={1}
                value={wordsPerBeat}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setWordsPerBeat(val);
                  saveSettings({ words_per_beat: val });
                }}
                className="w-full accent-amber-400 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-bold text-zinc-500">
                <span>1 (Hyper-Punchy)</span>
                <span>2 (Snappy Flow)</span>
                <span>3 (Balanced / Default)</span>
                <span>4 (Smooth Sentence)</span>
              </div>
            </div>
          </div>

          {/* Active Word Animation & Emojis */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Active Word Highlight Motion */}
            <div className="p-3.5 bg-zinc-950 rounded-2xl border border-zinc-800 space-y-2">
              <span className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-yellow-400" />
                Active Word Animation
              </span>
              <select
                value={animation}
                onChange={(e) => {
                  const anim = e.target.value;
                  setAnimation(anim);
                  saveSettings({ caption_motion: anim });
                }}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 text-xs font-bold text-zinc-200 focus:outline-none focus:border-amber-400"
              >
                <option value="pop">Scale Pop (1.15x Pop)</option>
                <option value="bounce">Bounce & Jiggle</option>
                <option value="scale">Smooth Scale</option>
                <option value="fade">Color Fade</option>
                <option value="snap">Snap / Rapid</option>
              </select>
            </div>

            {/* Contextual Emojis Toggle */}
            <div className="p-3.5 bg-zinc-950 rounded-2xl border border-zinc-800 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
                  <Smile className="w-3.5 h-3.5 text-pink-400" />
                  Contextual Emojis
                </span>
                <p className="text-[10px] text-zinc-400">
                  Adds 💰, 🎰, ❌, 🧠, 🔥 to semantic keywords.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  const next = !enableEmojis;
                  setEnableEmojis(next);
                  saveSettings({ enable_emojis: next });
                }}
                className={`w-10 h-5 flex items-center rounded-full p-0.5 transition-colors ${
                  enableEmojis ? "bg-pink-500 justify-end" : "bg-zinc-800 justify-start"
                }`}
              >
                <div className="bg-black w-4 h-4 rounded-full shadow-md" />
              </button>
            </div>
          </div>

          {/* 3-Color Palette Controls */}
          <div className="p-4 bg-zinc-950 rounded-2xl border border-zinc-800 space-y-3">
            <span className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
              <Palette className="w-3.5 h-3.5 text-amber-400" />
              ZapCap 3-Color Palette
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Main Color */}
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-400">Main Text Fill</label>
                <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 p-1.5 rounded-xl">
                  <input
                    type="color"
                    value={mainColor}
                    onChange={(e) => {
                      setMainColor(e.target.value);
                      saveSettings({
                        custom_colors: { main: e.target.value, second: secondColor, third: thirdColor },
                      });
                    }}
                    className="w-7 h-7 rounded border-none bg-transparent cursor-pointer"
                  />
                  <input
                    type="text"
                    value={mainColor}
                    onChange={(e) => {
                      setMainColor(e.target.value);
                      saveSettings({
                        custom_colors: { main: e.target.value, second: secondColor, third: thirdColor },
                      });
                    }}
                    className="w-full bg-transparent text-xs font-mono font-bold text-zinc-200 uppercase focus:outline-none"
                  />
                </div>
              </div>

              {/* Second Color (Active / Highlight) */}
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-400">Active / Highlight</label>
                <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 p-1.5 rounded-xl">
                  <input
                    type="color"
                    value={secondColor}
                    onChange={(e) => {
                      setSecondColor(e.target.value);
                      saveSettings({
                        custom_colors: { main: mainColor, second: e.target.value, third: thirdColor },
                      });
                    }}
                    className="w-7 h-7 rounded border-none bg-transparent cursor-pointer"
                  />
                  <input
                    type="text"
                    value={secondColor}
                    onChange={(e) => {
                      setSecondColor(e.target.value);
                      saveSettings({
                        custom_colors: { main: mainColor, second: e.target.value, third: thirdColor },
                      });
                    }}
                    className="w-full bg-transparent text-xs font-mono font-bold text-zinc-200 uppercase focus:outline-none"
                  />
                </div>
              </div>

              {/* Third Color (Secondary / Money) */}
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-400">Cash / Numbers</label>
                <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 p-1.5 rounded-xl">
                  <input
                    type="color"
                    value={thirdColor}
                    onChange={(e) => {
                      setThirdColor(e.target.value);
                      saveSettings({
                        custom_colors: { main: mainColor, second: secondColor, third: e.target.value },
                      });
                    }}
                    className="w-7 h-7 rounded border-none bg-transparent cursor-pointer"
                  />
                  <input
                    type="text"
                    value={thirdColor}
                    onChange={(e) => {
                      setThirdColor(e.target.value);
                      saveSettings({
                        custom_colors: { main: mainColor, second: secondColor, third: e.target.value },
                      });
                    }}
                    className="w-full bg-transparent text-xs font-mono font-bold text-zinc-200 uppercase focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Positioning & Safe-Zone Awareness */}
          <div className="p-4 bg-zinc-950 rounded-2xl border border-zinc-800 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
                  <MoveVertical className="w-3.5 h-3.5 text-blue-400" />
                  Vertical Position & Safe Zones
                </span>
                <p className="text-[10px] text-zinc-400">
                  Keeps text clear of TikTok captions (bottom) and profile handles (top).
                </p>
              </div>
              <span className="text-xs font-mono font-bold text-blue-300">
                {yPercent}% (Y-Offset)
              </span>
            </div>

            <input
              type="range"
              min={15}
              max={90}
              step={1}
              value={yPercent}
              onChange={(e) => {
                const val = Number(e.target.value);
                setYPercent(val);
                saveSettings({ subtitle_y_percent: val });
              }}
              className="w-full accent-blue-400 cursor-pointer"
            />

            {/* Quick Positions */}
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => {
                  setYPercent(25);
                  saveSettings({ subtitle_y_percent: 25, subtitle_position: "top" });
                }}
                className={`px-3 py-1 rounded-lg text-xs font-bold border transition-all ${
                  yPercent <= 35
                    ? "bg-blue-600 text-white border-blue-400"
                    : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200"
                }`}
              >
                Top Safe (25%)
              </button>
              <button
                type="button"
                onClick={() => {
                  setYPercent(50);
                  saveSettings({ subtitle_y_percent: 50, subtitle_position: "center" });
                }}
                className={`px-3 py-1 rounded-lg text-xs font-bold border transition-all ${
                  yPercent > 35 && yPercent < 70
                    ? "bg-blue-600 text-white border-blue-400"
                    : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200"
                }`}
              >
                Center Hook (50%)
              </button>
              <button
                type="button"
                onClick={() => {
                  setYPercent(84);
                  saveSettings({ subtitle_y_percent: 84, subtitle_position: "bottom" });
                }}
                className={`px-3 py-1 rounded-lg text-xs font-bold border transition-all ${
                  yPercent >= 70
                    ? "bg-blue-600 text-white border-blue-400"
                    : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200"
                }`}
              >
                Bottom Safe (84%)
              </button>
            </div>
          </div>

          {/* Subject-Aware Captions (Behind Speaker) */}
          <div className="p-4 bg-gradient-to-r from-purple-950/40 to-indigo-950/40 rounded-2xl border border-purple-500/30 flex items-center justify-between">
            <div className="space-y-0.5 max-w-[80%]">
              <span className="text-xs font-bold text-purple-200 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-purple-400" />
                Render Hook Words Behind Speaker
                <span className="text-[9px] bg-purple-500/20 text-purple-300 px-1.5 py-0.5 rounded border border-purple-500/30">
                  YOLO11n-seg
                </span>
              </span>
              <p className="text-[10px] text-purple-300/80">
                Large emphasis punchlines appear physically behind the speaker&apos;s torso while the foreground subject stays in front.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                const next = !behindSubject;
                setBehindSubject(next);
                saveSettings({ subtitles_behind_subject: next });
              }}
              className={`w-12 h-6 flex items-center rounded-full p-1 transition-colors ${
                behindSubject ? "bg-purple-500 justify-end" : "bg-zinc-800 justify-start"
              }`}
            >
              <div className="bg-black w-4 h-4 rounded-full shadow-md" />
            </button>
          </div>
        </div>
      )}

      {/* TAB 3: B-ROLLS */}
      {activeTab === "brolls" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
                <Film className="w-3.5 h-3.5 text-amber-400" />
                Cutaways & Visual Storytelling ({shots.length})
              </span>
              <p className="text-[10px] text-zinc-400">
                Pexels stock B-roll and viral HD reaction memes matched to transcript quotes.
              </p>
            </div>
            <button
              type="button"
              onClick={() => onOpenInsertCutaway(currentTime)}
              className="bg-amber-400 hover:bg-amber-300 text-black text-xs font-bold px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-all shadow-md shadow-amber-400/20"
            >
              <Scissors className="w-3.5 h-3.5" />
              <span>+ Cutaway at {currentTime.toFixed(1)}s</span>
            </button>
          </div>

          {/* Shot Cards List */}
          <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
            {shots.map((shot, idx) => (
              <div
                key={shot.shot_id || idx}
                className="bg-zinc-950 p-3 rounded-2xl border border-zinc-800/80 flex items-center justify-between gap-3 hover:border-zinc-700 transition-all"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono font-bold text-zinc-500 w-6">
                    #{idx + 1}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-zinc-200">
                        {shot.style === "meme" ? "🎭 Reaction Meme" : "🎬 Stock B-Roll"}
                      </span>
                      <span className="text-[10px] font-mono text-zinc-400">
                        {shot.start_time.toFixed(1)}s – {shot.end_time.toFixed(1)}s ({(shot.duration ?? (shot.end_time - shot.start_time)).toFixed(1)}s)
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 truncate max-w-[280px]">
                      {shot.dialogue_quote ? `"${shot.dialogue_quote}"` : shot.search_prompt}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onJumpToTime(shot.start_time)}
                    className="p-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300"
                    title="Jump player to shot"
                  >
                    <Play className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onOpenSwapBroll(shot)}
                    className="px-2.5 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold"
                  >
                    Swap
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: EFFECTS & AUDIO */}
      {activeTab === "effects" && (
        <div className="space-y-4">
          {/* BGM Track Picker */}
          <div className="p-4 bg-zinc-950 rounded-2xl border border-zinc-800 space-y-3">
            <span className="text-xs font-bold text-zinc-100 flex items-center gap-1.5">
              <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
              Background Music Track
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => {
                  setSelectedBgmId("none");
                  saveSettings({ bgm_track_id: "none" });
                }}
                className={`p-2.5 rounded-xl border text-left text-xs font-bold transition-all ${
                  selectedBgmId === "none"
                    ? "bg-zinc-800 text-white border-zinc-600"
                    : "bg-zinc-900/60 text-zinc-400 border-zinc-800 hover:text-zinc-200"
                }`}
              >
                🔇 No Background Music (Mute)
              </button>
              {bgmTracks.map((trk) => {
                const isSelected = selectedBgmId === trk.id;
                const isPlaying = isPlayingBgmPreview === trk.id;
                return (
                  <div
                    key={trk.id}
                    className={`p-2.5 rounded-xl border flex items-center justify-between text-xs transition-all ${
                      isSelected
                        ? "bg-emerald-950/30 text-emerald-300 border-emerald-500/50"
                        : "bg-zinc-900/60 text-zinc-300 border-zinc-800"
                    }`}
                  >
                    <div
                      onClick={() => {
                        setSelectedBgmId(trk.id);
                        saveSettings({ bgm_track_id: trk.id });
                      }}
                      className="cursor-pointer flex-1"
                    >
                      <span className="font-bold">{trk.name}</span>
                      <p className="text-[10px] text-zinc-500">{trk.genre || "Background Music"}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleBgmPreview(trk.id)}
                      className="p-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                      title={isPlaying ? "Stop Preview" : "Play Preview"}
                    >
                      {isPlaying ? <Pause className="w-3 h-3 text-emerald-400" /> : <Play className="w-3 h-3" />}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Volume & Ducking */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3.5 bg-zinc-950 rounded-2xl border border-zinc-800 space-y-2">
              <div className="flex items-center justify-between text-xs font-bold text-zinc-300">
                <span>BGM Volume</span>
                <span className="font-mono text-zinc-400">{(bgmVolume * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min={0.02}
                max={0.5}
                step={0.01}
                value={bgmVolume}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setBgmVolume(val);
                  saveSettings({ bgm_volume: val });
                }}
                className="w-full accent-emerald-400 cursor-pointer"
              />
            </div>

            <div className="p-3.5 bg-zinc-950 rounded-2xl border border-zinc-800 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-zinc-100">Voice Auto-Ducking</span>
                <p className="text-[10px] text-zinc-400">Automatically lowers BGM volume during speech.</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  const next = !bgmDucking;
                  setBgmDucking(next);
                  saveSettings({ bgm_ducking: next });
                }}
                className={`w-10 h-5 flex items-center rounded-full p-0.5 transition-colors ${
                  bgmDucking ? "bg-emerald-500 justify-end" : "bg-zinc-800 justify-start"
                }`}
              >
                <div className="bg-black w-4 h-4 rounded-full shadow-md" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: PUBLISH & EXPORT */}
      {activeTab === "publish" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Re-render Master Button */}
            <div className="p-4 bg-zinc-950 rounded-2xl border border-zinc-800 flex flex-col justify-between space-y-3">
              <div>
                <span className="text-xs font-black text-zinc-100 uppercase tracking-wide flex items-center gap-1.5">
                  <RefreshCw className="w-4 h-4 text-amber-400" />
                  Render Master Video
                </span>
                <p className="text-[11px] text-zinc-400 mt-1">
                  Bakes kinetic ASS subtitles, YOLO behind-speaker matte, and multitrack audio into a 9:16 master MP4.
                </p>
              </div>
              <button
                type="button"
                disabled={isRerendering}
                onClick={onRerenderMaster}
                className="w-full bg-gradient-to-r from-amber-500 to-yellow-500 hover:from-amber-400 hover:to-yellow-400 text-black text-xs font-black py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 transition-all disabled:opacity-50"
              >
                {isRerendering ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Rendering 9:16 Master...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Re-render Master Video</span>
                  </>
                )}
              </button>
            </div>

            {/* Launch OpenReel Button */}
            <div className="p-4 bg-zinc-950 rounded-2xl border border-zinc-800 flex flex-col justify-between space-y-3">
              <div>
                <span className="text-xs font-black text-zinc-100 uppercase tracking-wide flex items-center gap-1.5">
                  <ExternalLink className="w-4 h-4 text-indigo-400" />
                  OpenReel Multitrack Studio
                </span>
                <p className="text-[11px] text-zinc-400 mt-1">
                  Launch full browser non-destructive editor with separate tracks for A-roll, B-roll, kinetic words, and SFX.
                </p>
              </div>
              <button
                type="button"
                onClick={() => onLaunchOpenReel(selectedJob.job_id)}
                className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-black py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all"
              >
                <span>Launch in OpenReel Studio</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Direct Downloads */}
          <div className="p-4 bg-zinc-950 rounded-2xl border border-zinc-800 space-y-2">
            <span className="text-xs font-bold text-zinc-200">Delivery Downloads</span>
            <div className="flex items-center gap-2 flex-wrap">
              <a
                href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/video`}
                download={`master_${selectedJob.filename}`}
                className="px-3 py-1.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-200 text-xs font-semibold flex items-center gap-1.5 border border-zinc-800"
              >
                <Download className="w-3.5 h-3.5 text-emerald-400" />
                <span>Download Master MP4</span>
              </a>
              <a
                href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/export/openreel`}
                download={`${selectedJob.filename}.oreel`}
                className="px-3 py-1.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-200 text-xs font-semibold flex items-center gap-1.5 border border-zinc-800"
              >
                <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                <span>Export .oreel Project</span>
              </a>
              <a
                href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/subtitles/ass`}
                download={`${selectedJob.filename}.ass`}
                className="px-3 py-1.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-200 text-xs font-semibold flex items-center gap-1.5 border border-zinc-800"
              >
                <Type className="w-3.5 h-3.5 text-amber-400" />
                <span>Download ASS Subtitles</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
