"use client";

import React, { useState } from "react";
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
  // Localized playhead time - updates here NEVER re-render parent dashboard!
  const [currentTime, setCurrentTime] = useState<number>(0);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const jumpToCutaway = (startTime: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = startTime;
      videoRef.current.play().catch(() => {});
    }
  };

  return (
    <div className="bg-zinc-900/80 border border-zinc-800/90 rounded-3xl p-5 shadow-2xl space-y-4">
      {/* Video Title & Meta */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-zinc-100 truncate max-w-[240px]">
            {selectedJob.filename}
          </h2>
          <p className="text-[11px] text-zinc-400">
            Duration: {totalDuration.toFixed(1)}s • Master Edit
          </p>
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
          ref={videoRef}
          key={`${selectedJob.job_id}_${viewingHdrVideo ? "hdr" : "sdr"}`}
          controls
          playsInline
          preload="metadata"
          onTimeUpdate={handleTimeUpdate}
          className="max-h-[500px] w-auto rounded-xl shadow-lg aspect-[9/16]"
          src={
            viewingHdrVideo
              ? `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/hdr-video?v=${selectedJob.edit_plan?.last_render_revision || 1}`
              : `/api/jobs/${encodeURIComponent(selectedJob.job_id)}/video?v=${selectedJob.edit_plan?.last_render_revision || 1}`
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
              const safeDur = totalDuration > 0 ? totalDuration : 1;
              const leftPct = Math.max(0, (shot.start_time / safeDur) * 100);
              const widthPct = Math.min(
                100 - leftPct,
                ((shot.end_time - shot.start_time) / safeDur) * 100
              );
              const isCurrent = currentTime >= shot.start_time && currentTime <= shot.end_time;

              return (
                <button
                  type="button"
                  key={shot.shot_id || idx}
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
              type="button"
              onClick={() => onOpenInsertCutaway(currentTime)}
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
