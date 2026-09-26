"use client";

import React from "react";
import {
  RefreshCw,
  Sparkles,
  Play,
  Trash2,
  Clock,
  Zap,
  Volume2,
  Eye,
} from "lucide-react";
import { ShotDetail } from "../lib/types";

interface ShotCardProps {
  shot: ShotDetail;
  idx: number;
  isAutoGeneratingMeme: boolean;
  isTrimming: boolean;
  onOpenSwapModal: (shot: ShotDetail) => void;
  onAutoGenerateMeme: (shotId: string) => void;
  onJumpToCutaway: (startTime: number) => void;
  onDeleteShot: (shotId: string) => void;
  onTrimShot: (shotId: string, startTime: number, endTime: number) => void;
}

export const ShotCard: React.FC<ShotCardProps> = React.memo(
  ({
    shot,
    idx,
    isAutoGeneratingMeme,
    isTrimming,
    onOpenSwapModal,
    onAutoGenerateMeme,
    onJumpToCutaway,
    onDeleteShot,
    onTrimShot,
  }) => {
    const duration = (shot.end_time - shot.start_time) || 2.5;

    return (
      <div className="bg-zinc-900/80 border border-zinc-800/90 hover:border-zinc-700/80 rounded-2xl p-5 space-y-3.5 shadow-xl transition-all content-auto">
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
              ({duration.toFixed(1)}s duration)
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
              type="button"
              onClick={() => onOpenSwapModal(shot)}
              className="text-[11px] font-semibold text-cyan-300 hover:text-white bg-cyan-500/15 hover:bg-cyan-600/30 border border-cyan-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
              title="Swap footage with high-quality Pexels stock video or custom upload"
            >
              <RefreshCw className="w-3 h-3 text-cyan-400" />
              <span>Swap Footage</span>
            </button>

            {/* Autonomous AI Meme Button / Regenerate */}
            {shot.style === "meme" ? (
              <button
                type="button"
                disabled={isAutoGeneratingMeme}
                onClick={() => onAutoGenerateMeme(shot.shot_id)}
                className="text-[11px] font-semibold text-fuchsia-200 hover:text-white bg-fuchsia-600/25 hover:bg-fuchsia-600/40 border border-fuchsia-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                title="Regenerate another unique AI meme tailored specifically to this dialogue quote"
              >
                <Sparkles className={`w-3 h-3 text-fuchsia-300 ${isAutoGeneratingMeme ? "animate-spin" : ""}`} />
                <span>{isAutoGeneratingMeme ? "Generating..." : "⚡ AI Regenerate Meme"}</span>
              </button>
            ) : (
              <button
                type="button"
                disabled={isAutoGeneratingMeme}
                onClick={() => onAutoGenerateMeme(shot.shot_id)}
                className="text-[11px] font-semibold text-fuchsia-300 hover:text-white bg-fuchsia-500/15 hover:bg-fuchsia-600/30 border border-fuchsia-500/40 px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all shadow-sm disabled:opacity-50"
                title="Autonomously create a unique meme cutaway tailored to this dialogue quote"
              >
                <Sparkles className={`w-3 h-3 text-fuchsia-400 ${isAutoGeneratingMeme ? "animate-spin" : ""}`} />
                <span>{isAutoGeneratingMeme ? "Creating Meme..." : "⚡ Auto AI Meme"}</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => onJumpToCutaway(shot.start_time)}
              className="text-[11px] font-semibold text-amber-400 hover:text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all"
            >
              <Play className="w-3 h-3 fill-amber-400" />
              Jump
            </button>

            {/* Delete Cutaway Button */}
            <button
              type="button"
              onClick={() => onDeleteShot(shot.shot_id)}
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
                type="button"
                disabled={isTrimming || shot.start_time <= 0}
                onClick={() => onTrimShot(shot.shot_id, shot.start_time - 0.1, shot.end_time)}
                className="text-[10px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-1.5 py-0.5 rounded transition-colors"
                title="Nudge start back 0.1s"
              >
                -0.1s
              </button>
              <span className="text-zinc-100 font-bold px-1">{shot.start_time.toFixed(1)}s</span>
              <button
                type="button"
                disabled={isTrimming || shot.start_time >= shot.end_time - 0.3}
                onClick={() => onTrimShot(shot.shot_id, shot.start_time + 0.1, shot.end_time)}
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
                type="button"
                disabled={isTrimming || shot.end_time <= shot.start_time + 0.3}
                onClick={() => onTrimShot(shot.shot_id, shot.start_time, shot.end_time - 0.1)}
                className="text-[10px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-1.5 py-0.5 rounded transition-colors"
                title="Nudge end back 0.1s"
              >
                -0.1s
              </button>
              <span className="text-zinc-100 font-bold px-1">{shot.end_time.toFixed(1)}s</span>
              <button
                type="button"
                disabled={isTrimming}
                onClick={() => onTrimShot(shot.shot_id, shot.start_time, shot.end_time + 0.1)}
                className="text-[10px] bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30 text-zinc-300 px-1.5 py-0.5 rounded transition-colors"
                title="Nudge end forward 0.1s"
              >
                +0.1s
              </button>
            </div>

            {/* Duration Display */}
            <span className="text-[10px] text-zinc-400 font-sans">
              Duration: <strong className="text-zinc-200">{duration.toFixed(1)}s</strong>
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
                        preload="none"
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
                      preload="none"
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
    );
  }
);

ShotCard.displayName = "ShotCard";
