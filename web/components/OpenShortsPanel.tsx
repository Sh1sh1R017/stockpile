"use client";

import React, { useEffect, useState } from "react";
import { Film, Loader2, Play, CheckCircle2, AlertCircle } from "lucide-react";

interface OpenShortsPanelProps {
  jobId: string;
}

interface Clip {
  index: number;
  title?: string;
  video_url?: string;
  download_url?: string;
}

export const OpenShortsPanel: React.FC<OpenShortsPanelProps> = ({ jobId }) => {
  const [targetClips, setTargetClips] = useState(5);
  const [minSeconds, setMinSeconds] = useState(15);
  const [maxSeconds, setMaxSeconds] = useState(60);
  const [confirmRights, setConfirmRights] = useState(false);
  const [externalJobId, setExternalJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [clips, setClips] = useState<Clip[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!confirmRights) {
      setError("Confirm that you own the video or have permission to process it.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(\`/api/jobs/\${encodeURIComponent(jobId)}/openshorts\`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_clips: targetClips,
          clip_min_seconds: minSeconds,
          clip_max_seconds: maxSeconds,
          captions: true,
          auto_hook: true,
          confirm_rights: true,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Clip generation failed");
      setExternalJobId(data.openshorts_job_id);
      setStatus("queued");
      setClips([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Clip generation failed");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!externalJobId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const response = await fetch(
          \`/api/jobs/\${encodeURIComponent(jobId)}/openshorts/\${encodeURIComponent(externalJobId)}\`
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Status request failed");
        if (!cancelled) {
          setStatus(data.status || "processing");
          setClips(data.clips || []);
          if (data.status === "completed" || data.status === "failed") return;
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Status request failed");
      }
      if (!cancelled) window.setTimeout(poll, 5000);
    };

    poll();
    return () => {
      cancelled = true;
    };
  }, [jobId, externalJobId]);

  return (
    <div className="bg-zinc-900/80 border border-zinc-800/90 rounded-2xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-bold text-zinc-100">
            <Film className="w-4 h-4 text-cyan-400" />
            AI Clip Generator
          </div>
          <p className="text-[10px] text-zinc-500 mt-0.5">
            Turn a long video into multiple ready-to-edit vertical clips.
          </p>
        </div>
        {status !== "idle" && (
          <span className="text-[10px] font-mono text-cyan-300 flex items-center gap-1">
            {status === "processing" || status === "queued" ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : status === "completed" ? (
              <CheckCircle2 className="w-3 h-3" />
            ) : (
              <AlertCircle className="w-3 h-3" />
            )}
            {status}
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2">
        <label className="text-[10px] text-zinc-400">
          Target clips
          <input
            type="number"
            min={1}
            max={15}
            value={targetClips}
            onChange={(e) => setTargetClips(Number(e.target.value))}
            className="mt-1 w-full bg-zinc-950 border border-zinc-700 rounded-lg px-2 py-1.5 text-xs text-white"
          />
        </label>
        <label className="text-[10px] text-zinc-400">
          Min seconds
          <input
            type="number"
            min={5}
            max={175}
            value={minSeconds}
            onChange={(e) => setMinSeconds(Number(e.target.value))}
            className="mt-1 w-full bg-zinc-950 border border-zinc-700 rounded-lg px-2 py-1.5 text-xs text-white"
          />
        </label>
        <label className="text-[10px] text-zinc-400">
          Max seconds
          <input
            type="number"
            min={10}
            max={180}
            value={maxSeconds}
            onChange={(e) => setMaxSeconds(Number(e.target.value))}
            className="mt-1 w-full bg-zinc-950 border border-zinc-700 rounded-lg px-2 py-1.5 text-xs text-white"
          />
        </label>
      </div>

      <label className="flex items-start gap-2 text-[10px] text-zinc-400">
        <input
          type="checkbox"
          checked={confirmRights}
          onChange={(e) => setConfirmRights(e.target.checked)}
          className="mt-0.5"
        />
        <span>I own this video or have permission to process it.</span>
      </label>

      <button
        type="button"
        onClick={submit}
        disabled={busy || !confirmRights || maxSeconds < minSeconds + 5}
        className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold py-2.5 rounded-xl flex items-center justify-center gap-2"
      >
        {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
        Generate {targetClips} Shorts
      </button>

      {error && <p className="text-[10px] text-rose-400">{error}</p>}

      {clips.length > 0 && (
        <div className="space-y-1.5 border-t border-zinc-800 pt-2">
          <p className="text-[10px] font-semibold text-zinc-300">
            {clips.length} clips returned
          </p>
          {clips.map((clip) => (
            <div key={clip.index} className="flex items-center justify-between gap-2 bg-zinc-950 rounded-lg px-2.5 py-2">
              <span className="text-[10px] text-zinc-300 truncate">
                {clip.index + 1}. {clip.title || "Generated short"}
              </span>
              {(clip.download_url || clip.video_url) && (
                <a
                  href={clip.download_url || clip.video_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[10px] text-cyan-300 hover:text-cyan-200 shrink-0"
                >
                  Open
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
