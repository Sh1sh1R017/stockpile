"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import {
  CheckCircle2,
  Sparkles,
  Scissors,
  Download,
  Trash2,
  ExternalLink,
  Layers,
  ShieldCheck,
  FileCode,
  Archive,
  Type,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Film,
  Music,
  Mic,
  Flame,
  Volume2,
} from "lucide-react";
import { JobDetail, ShotDetail } from "../lib/types";

interface MasterVideoPlayerProps {
  selectedJob: JobDetail;
  totalDuration: number;
  shots: ShotDetail[];
  hdrAvailable: boolean;
  viewingHdrVideo: boolean;
  setViewingHdrVideo: (v: boolean) => void;
  isUpscalingHdr: boolean;
  hdrProgress: number;
  hdrFps: number;
  onOpenInsertCutaway: (time: number) => void;
  onDeleteJob: (job: { id: string; name: string }) => void;
  onLaunchOpenReel: (jobId: string) => void;
  videoRef: React.RefObject<HTMLVideoElement | null>;
}

export const MasterVideoPlayer: React.FC<MasterVideoPlayerProps> = ({
  selectedJob,
  totalDuration,
  shots,
  hdrAvailable,
  viewingHdrVideo,
  setViewingHdrVideo,
  isUpscalingHdr,
  hdrProgress,
  hdrFps,
  onOpenInsertCutaway,
  onDeleteJob,
  onLaunchOpenReel,
  videoRef,
}) => {
  // Localized playhead time & player state
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  // The master video already contains the rendered caption layers. A second live
  // DOM overlay must never be enabled by default or it creates duplicate captions.
  const [showLiveCaptions, setShowLiveCaptions] = useState<boolean>(false);
  const [zoomLevel, setZoomLevel] = useState<"fit" | "1.5x" | "2x">("fit");
  const [isScrubbing, setIsScrubbing] = useState<boolean>(false);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  const tracksScrollRef = useRef<HTMLDivElement>(null);
  const timelineTracksInnerRef = useRef<HTMLDivElement>(null);

  const safeDur = Math.max(1, totalDuration || 1);
  const editPlan = selectedJob.edit_plan;
  const renderSettings = editPlan?.render_settings || {};
  const subtitlesEnabled = renderSettings.subtitles_enabled !== false;
  const customColors = renderSettings.custom_colors || {};
  const mainColor = customColors.main || "#FFFFFF";
  const secondColor = customColors.second || "#FFE600";
  const thirdColor = customColors.third || "#00FF66";
  const yPercent = renderSettings.subtitle_y_percent ?? 82;

  const hookText = editPlan?.hook_text;
  const subtitles = useMemo(() => editPlan?.subtitles || [], [editPlan?.subtitles]);
  const zooms = useMemo(() => editPlan?.zooms || [], [editPlan?.zooms]);

  // Find active subtitle group
  const activeSub = useMemo(() => {
    if (!subtitlesEnabled || !showLiveCaptions) return null;
    return subtitles.find((s: any) => currentTime >= s.startTime && currentTime <= s.endTime);
  }, [subtitles, currentTime, subtitlesEnabled, showLiveCaptions]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const jumpToTime = useCallback((time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  }, [videoRef]);

  const togglePlayPause = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const jumpToPrevCut = () => {
    const sorted = [...shots].sort((a, b) => a.start_time - b.start_time);
    const prev = [...sorted].reverse().find((s) => s.start_time < currentTime - 0.25);
    jumpToTime(prev ? prev.start_time : 0);
  };

  const jumpToNextCut = () => {
    const sorted = [...shots].sort((a, b) => a.start_time - b.start_time);
    const next = sorted.find((s) => s.start_time > currentTime + 0.15);
    if (next) {
      jumpToTime(next.start_time);
    }
  };

  // Convert clientX to timeline time
  const calculateTimeFromX = useCallback(
    (clientX: number) => {
      if (!timelineTracksInnerRef.current) return 0;
      const rect = timelineTracksInnerRef.current.getBoundingClientRect();
      const relX = clientX - rect.left;
      const width = rect.width;
      if (width <= 0) return 0;
      return Math.max(0, Math.min(safeDur, (relX / width) * safeDur));
    },
    [safeDur],
  );

  const handleTimelineMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    setIsScrubbing(true);
    const target = calculateTimeFromX(e.clientX);
    jumpToTime(target);
  };

  useEffect(() => {
    if (!isScrubbing) return;
    const handleMouseMove = (e: MouseEvent) => {
      const target = calculateTimeFromX(e.clientX);
      jumpToTime(target);
    };
    const handleMouseUp = () => {
      setIsScrubbing(false);
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isScrubbing, calculateTimeFromX, jumpToTime]);

  // Formatter for MM:SS.s
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const tenths = Math.floor((seconds % 1) * 10);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}.${tenths}`;
  };

  // Time ruler tick generator
  const tickStep = safeDur <= 15 ? 1 : safeDur <= 45 ? 2 : 5;
  const rulerTicks = useMemo(() => {
    const ticks: number[] = [];
    for (let t = 0; t <= safeDur; t += tickStep) {
      ticks.push(t);
    }
    return ticks;
  }, [safeDur, tickStep]);

  // Deterministic audio waveform bars
  const speechWaveformBars = useMemo(() => {
    const count = 72;
    return Array.from({ length: count }, (_, i) => {
      const val = Math.sin(i * 0.48) * 0.38 + Math.cos(i * 0.22) * 0.28 + 0.38;
      return Math.max(0.18, Math.min(0.95, val));
    });
  }, []);

  const zoomWidthPercent = zoomLevel === "fit" ? "100%" : zoomLevel === "1.5x" ? "150%" : "200%";
  const playheadPercent = Math.max(0, Math.min(100, (currentTime / safeDur) * 100));

  return (
    <div className="bg-zinc-900/90 border border-zinc-800/90 rounded-3xl p-5 shadow-2xl space-y-4">
      {/* Video Title & Meta */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-zinc-100 truncate max-w-[280px]">
            {selectedJob.filename}
          </h2>
          <p className="text-[11px] text-zinc-400">
            Duration: {totalDuration.toFixed(1)}s • Master Edit • {shots.length} Cutaways
          </p>
        </div>
        <div className="flex items-center gap-2">
          {(renderSettings.subtitles_behind_subject ?? selectedJob.edit_plan?.subtitles_behind_subject) && (
            <span className="text-[10px] font-bold bg-purple-500/15 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
              <Sparkles className="w-3 h-3 text-purple-300" />
              Behind-Speaker Hook
            </span>
          )}
          <span className="text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Ready
          </span>
        </div>
      </div>

      {/* Master 9:16 Video Player */}
      <div className="bg-black rounded-2xl overflow-hidden border border-zinc-800 flex flex-col items-center py-2 shadow-2xl relative">
        {/* Stream Switcher & Live Caption Overlay Toggle */}
        <div className="flex items-center justify-between w-11/12 mb-2 z-10">
          {hdrAvailable ? (
            <div className="flex items-center gap-1.5">
              <button
                type="button"
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
                type="button"
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
          ) : (
            <div className="text-[10px] font-mono text-zinc-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              9:16 Vertical Master
            </div>
          )}

          <button
            type="button"
            onClick={() => setShowLiveCaptions(!showLiveCaptions)}
            className={`text-[10px] font-bold px-2.5 py-1 rounded-lg border transition-all flex items-center gap-1 ${
              showLiveCaptions
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : "bg-zinc-900 text-zinc-500 border-zinc-800 hover:text-zinc-300"
            }`}
          >
            <Type className="w-3 h-3" />
            <span>Caption Preview: {showLiveCaptions ? "ON" : "OFF"}</span>
          </button>
        </div>

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

        {/* Video Player Container with Live Caption Overlay */}
        <div className="relative inline-block max-h-[500px] w-auto aspect-[9/16] overflow-hidden rounded-xl shadow-lg">
          <video
            ref={videoRef}
            key={`${selectedJob.job_id}_${viewingHdrVideo ? "hdr" : "sdr"}`}
            controls
            playsInline
            preload="metadata"
            onTimeUpdate={handleTimeUpdate}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            className="w-full h-full object-contain rounded-xl"
            src={
              viewingHdrVideo
                ? `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/hdr-video?v=${selectedJob.edit_plan?.last_render_revision || 1}`
                : `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/video?v=${selectedJob.edit_plan?.last_render_revision || 1}`
            }
          >
            Your browser does not support the video tag.
          </video>

          {/* Live ZapCap Kinetic Caption Overlay */}
          {activeSub && (
            <div
              className="absolute left-0 right-0 px-3 text-center pointer-events-none transition-all duration-75 flex flex-col items-center z-20"
              style={{
                top: `${yPercent}%`,
                transform: "translateY(-50%)",
              }}
            >
              {activeSub.behindSubject && (
                <span className="mb-1 text-[8px] tracking-widest uppercase font-black px-1.5 py-0.5 rounded bg-purple-900/90 text-purple-200 border border-purple-400/50 shadow-sm animate-pulse">
                  BEHIND SPEAKER
                </span>
              )}
              <div className="inline-flex items-center justify-center flex-wrap gap-1 px-2.5 py-1 rounded-xl bg-black/40 backdrop-blur-[2px]">
                {activeSub.words && activeSub.words.length > 0 ? (
                  activeSub.words.map((w: any, wIdx: number) => {
                    const isActive = currentTime >= w.start && currentTime <= w.end;
                    const isMoneyOrNum = w.semantic_type === "money" || w.semantic_type === "number";
                    const wordColor = isActive ? secondColor : isMoneyOrNum ? thirdColor : mainColor;

                    return (
                      <span
                        key={wIdx}
                        className={`transition-all duration-100 inline-flex items-center gap-0.5 font-black uppercase tracking-wide ${
                          isActive
                            ? "scale-115 text-lg -translate-y-0.5 drop-shadow-[0_0_12px_rgba(255,230,0,0.95)] z-10"
                            : "scale-100 text-base opacity-95"
                        }`}
                        style={{
                          color: wordColor,
                          textShadow: "0 2px 6px rgba(0,0,0,0.95), 0 0 2px #000",
                          WebkitTextStroke: "1px #000000",
                        }}
                      >
                        {w.word}
                        {w.emoji && renderSettings.enable_emojis !== false && (
                          <span className="text-sm ml-0.5">{w.emoji}</span>
                        )}
                      </span>
                    );
                  })
                ) : (
                  <span
                    className="font-black text-base uppercase"
                    style={{
                      color: secondColor,
                      textShadow: "0 2px 6px rgba(0,0,0,0.95), 0 0 2px #000",
                      WebkitTextStroke: "1px #000000",
                    }}
                  >
                    {activeSub.text}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* PRO NLE MULTI-TRACK TIMELINE SYSTEM                                       */}
      {/* ========================================================================= */}
      <div className="space-y-2.5 pt-2 border-t border-zinc-800/90">
        {/* Timeline Header & Transport Controls */}
        <div className="flex flex-wrap items-center justify-between gap-2 bg-zinc-950/70 p-2.5 rounded-2xl border border-zinc-800">
          {/* Left: Title & Track Badges */}
          <div className="flex items-center gap-2">
            <span className="p-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Layers className="w-4 h-4" />
            </span>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-xs text-zinc-100">Pro Multi-Track Timeline</span>
                <span className="text-[9px] font-mono bg-zinc-800 text-zinc-400 px-1.5 py-0.2 rounded border border-zinc-700">
                  NLE Schema 1.2
                </span>
              </div>
              <p className="text-[10px] text-zinc-500">
                Non-destructive overlays • Word-level kinetic sync
              </p>
            </div>
          </div>

          {/* Center: Play/Pause & Cut Navigators */}
          <div className="flex items-center gap-1 bg-zinc-900 px-2 py-1 rounded-xl border border-zinc-800">
            <button
              type="button"
              onClick={jumpToPrevCut}
              title="Jump to Previous Cut (or 0s)"
              className="p-1 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded transition-colors"
            >
              <SkipBack className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={togglePlayPause}
              title={isPlaying ? "Pause playback" : "Start playback"}
              className="p-1 px-2 text-zinc-200 hover:text-white bg-zinc-800 hover:bg-zinc-700 rounded transition-colors flex items-center gap-1 text-[11px] font-bold"
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5 text-amber-400" /> : <Play className="w-3.5 h-3.5 text-emerald-400" />}
            </button>
            <button
              type="button"
              onClick={jumpToNextCut}
              title="Jump to Next Cut"
              className="p-1 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded transition-colors"
            >
              <SkipForward className="w-3.5 h-3.5" />
            </button>
            <div className="h-3 w-px bg-zinc-800 mx-1" />
            <div className="font-mono text-[11px] font-bold text-amber-300 tracking-wider">
              {formatTime(currentTime)}
              <span className="text-zinc-500 font-normal"> / {formatTime(safeDur)}</span>
            </div>
          </div>

          {/* Right: Zoom Level Controls */}
          <div className="flex items-center gap-1.5">
            <div className="flex items-center bg-zinc-900 rounded-xl border border-zinc-800 p-0.5 text-[10px] font-semibold">
              <button
                type="button"
                onClick={() => setZoomLevel("fit")}
                className={`px-2 py-0.5 rounded-lg transition-all ${
                  zoomLevel === "fit"
                    ? "bg-zinc-700 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                Fit
              </button>
              <button
                type="button"
                onClick={() => setZoomLevel("1.5x")}
                className={`px-2 py-0.5 rounded-lg transition-all ${
                  zoomLevel === "1.5x"
                    ? "bg-zinc-700 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                1.5x
              </button>
              <button
                type="button"
                onClick={() => setZoomLevel("2x")}
                className={`px-2 py-0.5 rounded-lg transition-all ${
                  zoomLevel === "2x"
                    ? "bg-zinc-700 text-white shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                2x
              </button>
            </div>

            <button
              type="button"
              onClick={() => onOpenInsertCutaway(currentTime)}
              title="Insert a B-roll or meme cutaway at current playhead"
              className="bg-indigo-600/90 hover:bg-indigo-500 text-white text-[11px] font-bold py-1.5 px-2.5 rounded-xl flex items-center gap-1 shadow-sm transition-all hover:scale-[1.02]"
            >
              <Scissors className="w-3 h-3 text-indigo-200" />
              <span>+ Cutaway</span>
            </button>
          </div>
        </div>

        {/* Scrollable Tracks Area */}
        <div
          ref={tracksScrollRef}
          className="relative w-full overflow-x-auto rounded-2xl bg-zinc-950 border border-zinc-800/90 select-none shadow-inner"
        >
          <div
            ref={timelineTracksInnerRef}
            style={{ width: zoomWidthPercent }}
            onMouseDown={handleTimelineMouseDown}
            onMouseMove={(e) => setHoverTime(calculateTimeFromX(e.clientX))}
            onMouseLeave={() => setHoverTime(null)}
            className="relative min-w-full pb-1 cursor-pointer"
          >
            {/* 1. Time Ruler Bar */}
            <div className="h-6 bg-zinc-900/90 border-b border-zinc-800 relative flex items-center px-1 text-[9px] text-zinc-400 font-mono">
              {rulerTicks.map((tickSec) => {
                const leftPos = (tickSec / safeDur) * 100;
                return (
                  <div
                    key={tickSec}
                    style={{ left: `${leftPos}%` }}
                    className="absolute top-0 bottom-0 flex flex-col justify-between items-start pointer-events-none"
                  >
                    <span className="text-[8px] pl-0.5 text-zinc-400 font-mono">
                      {formatTime(tickSec).slice(0, 5)}
                    </span>
                    <div className="w-px h-1.5 bg-zinc-700" />
                  </div>
                );
              })}

              {/* Marker: Hook Pin */}
              {hookText && (
                <div
                  style={{ left: "0%" }}
                  className="absolute top-0.5 z-20 flex items-center gap-0.5 bg-amber-500 text-black font-black text-[8px] px-1 py-0.2 rounded shadow-md pointer-events-none"
                  title={`Hook: ${hookText}`}
                >
                  <Flame className="w-2.5 h-2.5 fill-black" />
                  <span>HOOK</span>
                </div>
              )}

              {/* Marker: Cutaway Pins */}
              {shots.map((shot, idx) => {
                const pos = Math.max(0, (shot.start_time / safeDur) * 100);
                return (
                  <div
                    key={shot.shot_id || idx}
                    style={{ left: `${pos}%` }}
                    className="absolute top-0.5 z-20 flex items-center gap-0.5 bg-indigo-500 text-white font-bold text-[8px] px-1 py-0.2 rounded shadow-sm pointer-events-none"
                  >
                    <span>✂ #{idx + 1}</span>
                  </div>
                );
              })}
            </div>

            {/* 2. Track 1: Hook & Captions Track */}
            <div className="relative h-9 border-b border-zinc-800/80 bg-zinc-950/40 flex items-center px-0.5">
              <div className="absolute left-1 z-10 flex items-center gap-1 text-[9px] font-black uppercase text-amber-400/70 bg-zinc-900/80 px-1 py-0.5 rounded pointer-events-none border border-zinc-800">
                <Type className="w-2.5 h-2.5 text-amber-400" />
                <span>Captions</span>
              </div>

              {/* Hook Banner Chip */}
              {hookText && (
                <div
                  style={{
                    left: "0%",
                    width: `${Math.min(30, (3.2 / safeDur) * 100)}%`,
                  }}
                  className={`absolute top-1 bottom-1 rounded-md px-1.5 flex items-center justify-between text-[9px] font-black uppercase tracking-wider transition-all z-10 border ${
                    currentTime <= 3.2
                      ? "bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-500 text-black border-amber-300 shadow-md shadow-amber-500/30 animate-pulse"
                      : "bg-amber-950/60 text-amber-200 border-amber-500/40 opacity-80"
                  }`}
                  title={`Hook: ${hookText} (${selectedJob.edit_plan?.subtitles_behind_subject ? "Behind Speaker" : "Above Speaker"})`}
                >
                  <span className="truncate flex items-center gap-1">
                    <Flame className="w-3 h-3 shrink-0" />
                    <span>HOOK: {hookText}</span>
                  </span>
                  {selectedJob.edit_plan?.subtitles_behind_subject && (
                    <span className="text-[7px] bg-purple-900 text-purple-200 px-1 rounded ml-1 shrink-0">
                      BEHIND
                    </span>
                  )}
                </div>
              )}

              {/* Kinetic Subtitle Chips */}
              {subtitles.map((sub: any, idx: number) => {
                const subLeft = Math.max(0, (sub.startTime / safeDur) * 100);
                const subWidth = Math.max(0.6, ((sub.endTime - sub.startTime) / safeDur) * 100);
                const isSubActive = currentTime >= sub.startTime && currentTime <= sub.endTime;

                return (
                  <div
                    key={sub.id || idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      jumpToTime(sub.startTime);
                    }}
                    style={{
                      left: `${subLeft}%`,
                      width: `${subWidth}%`,
                    }}
                    title={`Subtitle: "${sub.text}" (${sub.startTime.toFixed(1)}s - ${sub.endTime.toFixed(1)}s)`}
                    className={`absolute top-1 bottom-1 rounded-md px-1 flex items-center justify-center text-[8px] font-bold uppercase truncate transition-all z-10 border ${
                      isSubActive
                        ? "bg-amber-400 text-black font-black border-amber-200 shadow-md shadow-amber-400/40 scale-y-105 z-20"
                        : "bg-zinc-800/80 hover:bg-zinc-700 text-zinc-300 border-zinc-700/60 hover:text-white"
                    }`}
                  >
                    <span className="truncate">{sub.text}</span>
                  </div>
                );
              })}
            </div>

            {/* 3. Track 2: B-Roll Cutaways Track */}
            <div className="relative h-13 border-b border-zinc-800/80 bg-zinc-950/60 flex items-center px-0.5">
              <div className="absolute left-1 z-10 flex items-center gap-1 text-[9px] font-black uppercase text-indigo-400/70 bg-zinc-900/80 px-1 py-0.5 rounded pointer-events-none border border-zinc-800">
                <Film className="w-2.5 h-2.5 text-indigo-400" />
                <span>B-Roll ({shots.length})</span>
              </div>

              {shots.map((shot, idx) => {
                const shotLeft = Math.max(0, (shot.start_time / safeDur) * 100);
                const shotWidth = Math.min(
                  100 - shotLeft,
                  Math.max(1.5, ((shot.end_time - shot.start_time) / safeDur) * 100),
                );
                const isShotActive = currentTime >= shot.start_time && currentTime <= shot.end_time;
                const queryText = shot.search_query || shot.category || `Cut ${idx + 1}`;
                const thumbUrl = `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/assets/sfx_frame_shot_${idx + 1}.jpg`;

                return (
                  <div
                    key={shot.shot_id || idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      jumpToTime(shot.start_time);
                    }}
                    style={{
                      left: `${shotLeft}%`,
                      width: `${shotWidth}%`,
                    }}
                    title={`Click to jump: Cut ${idx + 1}: ${queryText} (${shot.start_time.toFixed(1)}s - ${shot.end_time.toFixed(1)}s)`}
                    className={`absolute top-1 bottom-1 rounded-lg overflow-hidden border transition-all flex items-center gap-1.5 px-1.5 cursor-pointer z-10 ${
                      isShotActive
                        ? "bg-amber-500/25 border-2 border-amber-400 text-amber-200 shadow-[0_0_15px_rgba(251,191,36,0.6)] z-20 scale-y-[1.02]"
                        : "bg-indigo-950/70 hover:bg-indigo-900/80 border-indigo-500/40 text-indigo-200"
                    }`}
                  >
                    {/* Thumbnail preview */}
                    <img
                      src={thumbUrl}
                      alt=""
                      onError={(e) => {
                        (e.currentTarget as HTMLElement).style.display = "none";
                      }}
                      className="w-8 h-8 object-cover rounded bg-black/50 shrink-0 border border-black/40"
                    />

                    <div className="flex flex-col min-w-0 truncate">
                      <div className="flex items-center gap-1 text-[9px] font-black truncate">
                        <span className="text-amber-300">#{idx + 1}</span>
                        <span className="truncate">{queryText}</span>
                      </div>
                      <span className="text-[8px] font-mono opacity-80">
                        {(shot.duration ?? (shot.end_time - shot.start_time)).toFixed(1)}s {shot.transition ? `• ${shot.transition}` : ""}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 4. Track 3: Speaker / A-Roll Dialogue Track */}
            <div className="relative h-8 border-b border-zinc-800/80 bg-zinc-950/50 flex items-center px-0.5 overflow-hidden">
              <div className="absolute left-1 z-10 flex items-center gap-1 text-[9px] font-black uppercase text-cyan-400/70 bg-zinc-900/80 px-1 py-0.5 rounded pointer-events-none border border-zinc-800">
                <Mic className="w-2.5 h-2.5 text-cyan-400" />
                <span>Speaker</span>
              </div>

              {/* Continuous Dialogue Waveform Track */}
              <div className="w-full h-full flex items-center gap-0.5 px-20 opacity-60">
                {speechWaveformBars.map((heightMultiplier, bIdx) => (
                  <div
                    key={bIdx}
                    style={{ height: `${heightMultiplier * 85}%` }}
                    className="flex-1 bg-cyan-500/50 rounded-full"
                  />
                ))}
              </div>

              {/* Zoom Punch-In Indicators */}
              {zooms.map((zoom: any, zIdx: number) => {
                const zTime = Number(zoom.time || 0);
                const zLeft = (zTime / safeDur) * 100;
                return (
                  <div
                    key={zIdx}
                    style={{ left: `${zLeft}%` }}
                    className="absolute top-1 bottom-1 flex items-center gap-0.5 bg-sky-500 text-white font-black text-[7px] px-1 rounded z-10 pointer-events-none shadow"
                    title={`Punch Zoom: ${zoom.scale || 1.1}x (${zoom.easing || "snappy"})`}
                  >
                    <span>🔍 {zoom.scale || 1.1}x</span>
                  </div>
                );
              })}
            </div>

            {/* 5. Track 4: Audio / BGM & SFX Track */}
            <div className="relative h-7 bg-zinc-950/60 flex items-center px-0.5 overflow-hidden">
              <div className="absolute left-1 z-10 flex items-center gap-1 text-[9px] font-black uppercase text-violet-400/70 bg-zinc-900/80 px-1 py-0.5 rounded pointer-events-none border border-zinc-800">
                <Music className="w-2.5 h-2.5 text-violet-400" />
                <span>Audio / BGM</span>
              </div>

              <div className="w-full h-full flex items-center gap-1 px-20 opacity-40">
                {Array.from({ length: 48 }).map((_, aIdx) => (
                  <div
                    key={aIdx}
                    style={{ height: `${20 + (aIdx % 5) * 15}%` }}
                    className="flex-1 bg-violet-400/60 rounded-full"
                  />
                ))}
              </div>
            </div>

            {/* 6. Vertical Playhead Scrubbing Needle */}
            <div
              style={{ left: `${playheadPercent}%` }}
              className="absolute top-0 bottom-0 w-0.5 bg-gradient-to-b from-amber-300 via-amber-400 to-amber-500 z-30 pointer-events-none shadow-[0_0_10px_rgba(251,191,36,0.9)]"
            >
              {/* Playhead Top Cap */}
              <div className="absolute -top-1 -translate-x-1/2 bg-amber-400 text-black font-mono font-black text-[8px] px-1 py-0.2 rounded-sm shadow-md flex items-center justify-center">
                {currentTime.toFixed(1)}s
              </div>
            </div>

            {/* Hover Cursor Line */}
            {hoverTime !== null && !isScrubbing && (
              <div
                style={{ left: `${(hoverTime / safeDur) * 100}%` }}
                className="absolute top-0 bottom-0 w-px bg-white/40 z-25 pointer-events-none"
              >
                <div className="absolute -top-4 -translate-x-1/2 bg-zinc-800 text-white font-mono text-[8px] px-1 rounded shadow">
                  {hoverTime.toFixed(1)}s
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Inserter Action Bar */}
        <div className="flex items-center justify-between text-[11px] text-zinc-400 px-1">
          <p className="flex items-center gap-1">
            <span className="text-amber-400">💡 Tip:</span> Click anywhere on the timeline to scrub in real-time, or click any Cutaway / Caption chip to seek directly.
          </p>
          <button
            type="button"
            onClick={() => onOpenInsertCutaway(currentTime)}
            className="text-indigo-400 hover:text-indigo-300 font-bold flex items-center gap-1 underline underline-offset-2"
          >
            <Scissors className="w-3 h-3" />
            <span>Split & Add Footage at {currentTime.toFixed(1)}s</span>
          </button>
        </div>
      </div>

      {/* Action Buttons: Download + Delete Button */}
      <div className="flex items-center gap-2 pt-1">
        {selectedJob.status === "COMPLETED" && selectedJob.output_video_path ? (
          <a
            href={`/api/jobs/${encodeURIComponent(selectedJob.job_id)}/video`}
            download={`final_${selectedJob.filename}`}
            className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition-colors border border-zinc-700/60"
          >
            <Download className="w-3.5 h-3.5 text-indigo-400" />
            Download 9:16 Video
          </a>
        ) : (
          <button
            type="button"
            disabled
            title="Video is still processing or failed to render"
            className="flex-1 bg-zinc-850 text-zinc-500 text-xs font-semibold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 cursor-not-allowed border border-zinc-800/80 opacity-60"
          >
            <Download className="w-3.5 h-3.5 text-zinc-600" />
            <span>Download Unavailable</span>
          </button>
        )}

        {/* Prominent Delete Button under Video Player */}
        <button
          type="button"
          onClick={() => onDeleteJob({ id: selectedJob.job_id, name: selectedJob.filename })}
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
        {selectedJob?.edit_plan?.openreel_custom_edited && (
          <div className="flex items-center justify-between px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-[11px]">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="font-semibold">Timeline Synced</span>
            </div>
            <span className="text-[10px] text-zinc-400 font-mono">
              {selectedJob.edit_plan.last_openreel_sync
                ? new Date(selectedJob.edit_plan.last_openreel_sync).toLocaleTimeString()
                : "Active"}
            </span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onLaunchOpenReel(selectedJob.job_id)}
            title="Launch the editable timeline inside this dashboard"
            className="flex-1 bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 hover:from-emerald-500 hover:via-teal-500 hover:to-cyan-500 text-white text-[12px] font-bold py-2.5 px-3 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-950/30 hover:scale-[1.01]"
          >
            <Sparkles className="w-4 h-4 text-emerald-200 animate-pulse" />
            <span>Launch Timeline Editor</span>
          </button>
          <a
            href={`http://localhost:5173/#/editor?loadJob=${encodeURIComponent(selectedJob.job_id)}`}
            target="_blank"
            rel="noopener noreferrer"
            title="Open the Timeline Editor in a dedicated browser tab"
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
            title="Download the editable project file"
            className="flex-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-semibold py-2 px-2.5 rounded-xl flex items-center justify-center gap-1.5 transition-colors"
          >
            <Layers className="w-3.5 h-3.5 text-emerald-400" />
            Editable Project
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

      {/* NLE & ZIP Export Action Row */}
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
  );
};
