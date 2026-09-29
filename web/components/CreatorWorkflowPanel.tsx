"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Sparkles,
  Scissors,
  Wand2,
  Loader2,
  CheckCircle2,
  Circle,
  Type,
  Film,
  SlidersHorizontal,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

type Mode = "home" | "edit" | "shorts" | "captions";

interface Candidate {
  index: number;
  title?: string;
  start?: number | string;
  end?: number | string;
  video_url?: string;
  download_url?: string;
  youtube_title?: string;
}

interface ChildEdit {
  job_id: string;
  title: string;
  status: string;
  progress: number;
  output_video_path?: string | null;
  source: string;
  start: number;
  end: number;
  batch_id?: string | null;
  drive_file_url?: string | null;
}

interface CreatorWorkflowPanelProps {
  jobId: string;
  totalDuration: number;
  onOpenOpenReel?: (jobId: string) => void;
}

const CAPTION_PRESETS = [
  { id: "razor_pop", label: "Razor Pop", sample: "MOST PEOPLE" },
  { id: "razor_neon", label: "Razor Neon", sample: "THE BIG IDEA" },
  { id: "razor_badge", label: "Razor Badge", sample: "$10 MILLION" },
  { id: "hormozi", label: "Hormozi Punch", sample: "THE TRUTH" },
  { id: "beast", label: "Neon Green", sample: "DON'T MISS THIS" },
  { id: "clean", label: "Clean", sample: "simple & clear" },
];

const clampTime = (value: number, max: number) =>
  Math.max(0, Math.min(Number.isFinite(value) ? value : 0, Math.max(0, max)));

const candidateTime = (value: number | string | undefined, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const CreatorWorkflowPanel: React.FC<CreatorWorkflowPanelProps> = ({
  jobId,
  totalDuration,
  onOpenOpenReel,
}) => {
  const [mode, setMode] = useState<Mode>("home");
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(Math.min(60, totalDuration || 60));
  const [editTitle, setEditTitle] = useState("Edited Short");
  const [targetClips, setTargetClips] = useState(5);
  const [minSeconds, setMinSeconds] = useState(15);
  const [maxSeconds, setMaxSeconds] = useState(60);
  const [rightsConfirmed, setRightsConfirmed] = useState(false);
  const [openShortsJobId, setOpenShortsJobId] = useState<string | null>(null);
  const [openShortsStatus, setOpenShortsStatus] = useState("idle");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidates, setSelectedCandidates] = useState<number[]>([]);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [childEdits, setChildEdits] = useState<ChildEdit[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [captionPreset, setCaptionPreset] = useState("razor_pop");
  const [captionMotion, setCaptionMotion] = useState("word-pop");
  const [behindSubject, setBehindSubject] = useState(true);
  const [captionDraftSaved, setCaptionDraftSaved] = useState(false);

  useEffect(() => {
    const nextEnd = Math.min(60, totalDuration || 60);
    setEndTime((current) => clampTime(current || nextEnd, totalDuration || nextEnd));
  }, [totalDuration]);

  useEffect(() => {
    let cancelled = false;
    const loadCachedShorts = async () => {
      try {
        const response = await fetch(
          `/api/jobs/${encodeURIComponent(jobId)}/openshorts/candidates`
        );
        if (!response.ok) return;
        const data = await response.json();
        if (cancelled || !data.clips?.length) return;
        setCandidates(data.clips);
        setOpenShortsJobId(data.openshorts_job_id || null);
        setOpenShortsStatus(data.status || "completed");
        setSelectedCandidates(
          data.clips
            .slice(0, Math.min(targetClips, data.clips.length))
            .map((candidate: Candidate) => candidate.index)
        );
      } catch {
        // Cached discovery is optional; never block the editor.
      }
    };
    loadCachedShorts();
    return () => {
      cancelled = true;
    };
  }, [jobId]);
 
  useEffect(() => {
    if (!openShortsJobId) return;
    let cancelled = false;
    let timer: number | null = null;

    const poll = async () => {
      try {
        const response = await fetch(
          `/api/jobs/${encodeURIComponent(jobId)}/openshorts/${encodeURIComponent(openShortsJobId)}`
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "OpenShorts status failed");
        if (!cancelled) {
          setOpenShortsStatus(data.status || "processing");
          const nextCandidates = Array.isArray(data.clips) ? data.clips : [];
          if (nextCandidates.length) {
            setCandidates(nextCandidates);
            if (selectedCandidates.length === 0) {
              setSelectedCandidates(nextCandidates.slice(0, Math.min(targetClips, nextCandidates.length)).map((c: Candidate) => c.index));
            }
          }
          if (data.status === "completed" || data.status === "failed") return;
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "OpenShorts status failed");
      }
      if (!cancelled) timer = window.setTimeout(poll, 3000);
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [jobId, openShortsJobId, targetClips, selectedCandidates.length]);

  useEffect(() => {
    if (!batchId) return;
    let cancelled = false;
    let timer: number | null = null;

    const poll = async () => {
      try {
        const response = await fetch(
          `/api/jobs/${encodeURIComponent(jobId)}/shorts?batch_id=${encodeURIComponent(batchId)}`
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Short batch status failed");
        if (!cancelled) {
          setChildEdits(Array.isArray(data.edits) ? data.edits : []);
          const active = (data.edits || []).some((e: ChildEdit) =>
            !["COMPLETED", "FAILED", "CANCELLED"].includes((e.status || "").toUpperCase())
          );
          if (active) timer = window.setTimeout(poll, 2500);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Batch status failed");
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [jobId, batchId]);

  const selected = useMemo(
    () => candidates.filter((candidate) => selectedCandidates.includes(candidate.index)),
    [candidates, selectedCandidates]
  );

  const editThis = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/shorts/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start: clampTime(startTime, totalDuration),
          end: clampTime(endTime, totalDuration),
          title: editTitle || "Edited Short",
          caption_style: captionPreset,
          caption_motion: captionMotion,
          subtitles_behind_subject: behindSubject,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not create edit");
      setBatchId(data.batch_id || null);
      setMode("home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create edit");
    } finally {
      setBusy(false);
    }
  };

  const findShorts = async () => {
    if (!rightsConfirmed) {
      setError("Confirm that you own the video or have permission to process it.");
      return;
    }
    setBusy(true);
    setError(null);
    setCandidates([]);
    setSelectedCandidates([]);
    setChildEdits([]);
    try {
      const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/openshorts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_clips: targetClips,
          clip_min_seconds: minSeconds,
          clip_max_seconds: maxSeconds,
          captions: false,
          auto_hook: true,
          confirm_rights: true,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "OpenShorts failed");
      setOpenShortsJobId(data.openshorts_job_id);
      setOpenShortsStatus(data.status || "queued");
    } catch (e) {
      setError(e instanceof Error ? e.message : "OpenShorts failed");
    } finally {
      setBusy(false);
    }
  };

  const generateSelected = async () => {
    if (!selected.length) {
      setError("Select at least one short.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/jobs/${encodeURIComponent(jobId)}/openshorts/edits`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            batch_id: batchId,
            candidates: selected.map((candidate) => ({
              id: `openshorts_${candidate.index}`,
              title: candidate.title || `Short ${candidate.index + 1}`,
              start: candidate.start,
              end: candidate.end,
            })),
            caption_style: captionPreset,
            caption_motion: captionMotion,
            subtitles_behind_subject: behindSubject,
          }),
        }
      );
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not queue edited shorts");
      setBatchId(data.batch_id);
      setChildEdits(data.edits || []);
      setMode("home");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not queue edited shorts");
    } finally {
      setBusy(false);
    }
  };

  const saveCaptionStyle = async () => {
    setCaptionDraftSaved(false);
    setError(null);
    try {
      const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subtitles_enabled: true,
          subtitle_style: captionPreset,
          subtitle_position: "bottom",
          subtitles_behind_subject: behindSubject,
          caption_motion: captionMotion,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Could not save caption style");
      }
      setCaptionDraftSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save caption style");
    }
  };

  const home = (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/95 p-4 shadow-xl">
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">Create from this video</p>
          <h3 className="mt-1 text-base font-bold text-white">What do you want to make?</h3>
          <p className="mt-1 text-xs text-zinc-500">One selected edit, or multiple shorts discovered by OpenShorts.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => setMode("edit")}
            className="group rounded-2xl border border-zinc-800 bg-zinc-900 p-4 text-left transition hover:border-indigo-500/50 hover:bg-zinc-900/90"
          >
            <div className="flex items-center justify-between">
              <div className="rounded-xl bg-indigo-500/10 p-2 text-indigo-300"><Scissors className="h-5 w-5" /></div>
              <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-indigo-300" />
            </div>
            <p className="mt-4 text-sm font-bold text-white">Edit This</p>
            <p className="mt-1 text-xs leading-5 text-zinc-500">Turn one chosen section into a finished Stockpile short.</p>
          </button>

          <button
            type="button"
            onClick={() => setMode("shorts")}
            className="group rounded-2xl border border-zinc-800 bg-zinc-900 p-4 text-left transition hover:border-cyan-500/50 hover:bg-zinc-900/90"
          >
            <div className="flex items-center justify-between">
              <div className="rounded-xl bg-cyan-500/10 p-2 text-cyan-300"><Sparkles className="h-5 w-5" /></div>
              <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-cyan-300" />
            </div>
            <p className="mt-4 text-sm font-bold text-white">Make Edited Clips</p>
            <p className="mt-1 text-xs leading-5 text-zinc-500">Use OpenShorts to find moments, then fully edit the selected shorts in Stockpile.</p>
          </button>
        </div>

        <div className="grid gap-2 sm:grid-cols-4">
          <button type="button" onClick={() => setMode("captions")} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-left text-xs text-zinc-300 hover:border-zinc-700">
            <Type className="mb-1 h-4 w-4 text-amber-300" /> Captions
          </button>
          <button type="button" onClick={() => setMode("shorts")} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-left text-xs text-zinc-300 hover:border-zinc-700">
            <Film className="mb-1 h-4 w-4 text-cyan-300" /> Find Shorts
          </button>
          <button type="button" onClick={() => onOpenOpenReel?.(jobId)} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-left text-xs text-zinc-300 hover:border-zinc-700">
            <ExternalLink className="mb-1 h-4 w-4 text-emerald-300" /> OpenReel
          </button>
          <button type="button" onClick={() => setMode("captions")} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-left text-xs text-zinc-300 hover:border-zinc-700">
            <SlidersHorizontal className="mb-1 h-4 w-4 text-violet-300" /> Style
          </button>
        </div>

        {batchId && childEdits.length > 0 && (
          <div className="border-t border-zinc-800 pt-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-semibold text-white">Edited Shorts</p>
              <span className="text-[10px] font-mono text-zinc-500">{childEdits.length} in batch</span>
            </div>
            <div className="space-y-2">
              {childEdits.map((edit) => (
                <div key={edit.job_id} className="rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-white">{edit.title}</p>
                      <p className="text-[10px] text-zinc-500">{edit.start.toFixed(1)}s – {edit.end.toFixed(1)}s</p>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-400">{edit.status}</span>
                  </div>
                  <div className="mt-2 flex gap-2">
                    {edit.status === "COMPLETED" && (
                      <button type="button" onClick={() => onOpenOpenReel?.(edit.job_id)} className="flex-1 rounded-lg bg-emerald-500/10 px-2 py-1.5 text-[10px] font-semibold text-emerald-300 hover:bg-emerald-500/20">
                        Open in OpenReel
                      </button>
                    )}
                    {edit.output_video_path && (
                      <a href={`/api/jobs/${encodeURIComponent(edit.job_id)}/video`} target="_blank" rel="noreferrer" className="rounded-lg bg-zinc-800 px-2 py-1.5 text-[10px] font-semibold text-zinc-200">
                        Preview
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {error && <p className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs text-rose-300">{error}</p>}
      </div>
    </div>
  );

  const editView = (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/95 p-4 shadow-xl">
      <div className="flex items-center gap-2">
        <button type="button" onClick={() => setMode("home")} className="rounded-lg p-1 text-zinc-500 hover:bg-zinc-900 hover:text-white"><ChevronLeft className="h-4 w-4" /></button>
        <div><p className="text-sm font-bold text-white">Edit This</p><p className="text-[10px] text-zinc-500">Create one finished short from a known section.</p></div>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="text-[10px] text-zinc-400">Start
          <input type="number" min={0} max={totalDuration} step={0.1} value={startTime} onChange={(e) => setStartTime(clampTime(Number(e.target.value), totalDuration))} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-white" />
        </label>
        <label className="text-[10px] text-zinc-400">End
          <input type="number" min={0} max={totalDuration} step={0.1} value={endTime} onChange={(e) => setEndTime(clampTime(Number(e.target.value), totalDuration))} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-white" />
        </label>
      </div>
      <label className="mt-3 block text-[10px] text-zinc-400">Title
        <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-white" />
      </label>
      <div className="mt-4 rounded-xl border border-zinc-800 bg-zinc-900/70 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">Caption stack</p>
        <p className="mt-1 text-xs text-zinc-300">Razor captions + semantic emphasis + subject-aware hooks.</p>
      </div>
      <button type="button" disabled={busy || endTime <= startTime} onClick={editThis} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 py-2.5 text-xs font-bold text-white hover:bg-indigo-500 disabled:opacity-40">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
        Make This Short
      </button>
      {error && <p className="mt-3 text-xs text-rose-300">{error}</p>}
    </div>
  );

  const shortsView = (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/95 p-4 shadow-xl">
      <div className="flex items-center gap-2">
        <button type="button" onClick={() => setMode("home")} className="rounded-lg p-1 text-zinc-500 hover:bg-zinc-900 hover:text-white"><ChevronLeft className="h-4 w-4" /></button>
        <div><p className="text-sm font-bold text-white">Make Edited Clips</p><p className="text-[10px] text-zinc-500">OpenShorts finds the moments. Stockpile edits them.</p></div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <label className="text-[10px] text-zinc-400">Clips
          <input type="number" min={1} max={15} value={targetClips} onChange={(e) => setTargetClips(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-2 text-xs text-white" />
        </label>
        <label className="text-[10px] text-zinc-400">Min sec
          <input type="number" min={5} max={175} value={minSeconds} onChange={(e) => setMinSeconds(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-2 text-xs text-white" />
        </label>
        <label className="text-[10px] text-zinc-400">Max sec
          <input type="number" min={10} max={180} value={maxSeconds} onChange={(e) => setMaxSeconds(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-2 text-xs text-white" />
        </label>
      </div>

      <div className="mt-3 flex items-start gap-2 rounded-xl border border-zinc-800 bg-zinc-900/60 p-3">
        <input type="checkbox" checked={rightsConfirmed} onChange={(e) => setRightsConfirmed(e.target.checked)} className="mt-0.5" />
        <p className="text-[10px] leading-4 text-zinc-400">I own this video or have permission to process it.</p>
      </div>

      {!candidates.length && (
        <button type="button" disabled={busy || !rightsConfirmed} onClick={findShorts} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-600 px-3 py-2.5 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-40">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Find Shorts with OpenShorts
        </button>
      )}

      {openShortsStatus !== "idle" && !candidates.length && (
        <div className="mt-3 flex items-center gap-2 rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-3 py-2 text-xs text-cyan-200">
          <Loader2 className="h-4 w-4 animate-spin" /> Finding strong moments… {openShortsStatus}
        </div>
      )}

      {candidates.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-white">Found {candidates.length} shorts</p>
            <button type="button" onClick={() => setSelectedCandidates(selectedCandidates.length ? [] : candidates.map((c) => c.index))} className="text-[10px] text-cyan-300 hover:text-cyan-200">
              {selectedCandidates.length ? "Clear" : "Select all"}
            </button>
          </div>

          <div className="max-h-64 space-y-2 overflow-auto pr-1">
            {candidates.map((candidate) => {
              const checked = selectedCandidates.includes(candidate.index);
              const start = candidateTime(candidate.start, 0);
              const end = candidateTime(candidate.end, start + 30);
              return (
                <button
                  key={candidate.index}
                  type="button"
                  onClick={() =>
                    setSelectedCandidates((current) =>
                      current.includes(candidate.index)
                        ? current.filter((id) => id !== candidate.index)
                        : [...current, candidate.index]
                    )
                  }
                  className={`w-full rounded-xl border px-3 py-2.5 text-left transition ${
                    checked ? "border-cyan-500/50 bg-cyan-500/5" : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {checked ? <CheckCircle2 className="h-4 w-4 text-cyan-300" /> : <Circle className="h-4 w-4 text-zinc-600" />}
                    <span className="truncate text-xs font-semibold text-white">{candidate.title || `Short ${candidate.index + 1}`}</span>
                    <span className="ml-auto shrink-0 text-[10px] font-mono text-zinc-500">{start.toFixed(1)}–{end.toFixed(1)}s</span>
                  </div>
                </button>
              );
            })}
          </div>

          <button type="button" disabled={busy || !selected.length} onClick={generateSelected} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-3 py-2.5 text-xs font-bold text-white hover:bg-indigo-500 disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
            Edit {selected.length} Selected
          </button>
        </div>
      )}
      {error && <p className="mt-3 text-xs text-rose-300">{error}</p>}
    </div>
  );

  const captionsView = (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/95 p-4 shadow-xl">
      <div className="flex items-center gap-2">
        <button type="button" onClick={() => setMode("home")} className="rounded-lg p-1 text-zinc-500 hover:bg-zinc-900 hover:text-white"><ChevronLeft className="h-4 w-4" /></button>
        <div><p className="text-sm font-bold text-white">Caption Studio</p><p className="text-[10px] text-zinc-500">ZapCap-inspired word-level creator presets, powered by Razor.</p></div>
      </div>

      <div className="mt-4 grid max-h-56 grid-cols-2 gap-2 overflow-auto sm:grid-cols-3">
        {CAPTION_PRESETS.map((preset) => (
          <button
            type="button"
            key={preset.id}
            onClick={() => setCaptionPreset(preset.id)}
            className={`rounded-xl border p-2.5 text-left transition ${
              captionPreset === preset.id ? "border-amber-400/60 bg-amber-400/5" : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
            }`}
          >
            <span className="text-[10px] text-zinc-500">{preset.label}</span>
            <span className="mt-1 block truncate text-sm font-black text-white">{preset.sample}</span>
          </button>
        ))}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="text-[10px] text-zinc-400">Motion
          <select value={captionMotion} onChange={(e) => setCaptionMotion(e.target.value)} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-white">
            <option value="word-pop">Word Pop</option>
            <option value="bounce">Bounce</option>
            <option value="focus">Focus</option>
            <option value="slide-up">Slide Up</option>
            <option value="typewriter">Typewriter</option>
            <option value="scramble">Scramble</option>
          </select>
        </label>
        <label className="flex items-center gap-2 self-end rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-300">
          <input type="checkbox" checked={behindSubject} onChange={(e) => setBehindSubject(e.target.checked)} />
          Subject-aware hooks
        </label>
      </div>

      <button type="button" onClick={saveCaptionStyle} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-amber-400/30 bg-amber-400/10 px-3 py-2.5 text-xs font-bold text-amber-200 hover:bg-amber-400/15">
        <Type className="h-4 w-4" />
        {captionDraftSaved ? "Caption Style Saved" : "Use This Caption Style"}
      </button>
      {error && <p className="mt-3 text-xs text-rose-300">{error}</p>}
    </div>
  );

  if (mode === "edit") return editView;
  if (mode === "shorts") return shortsView;
  if (mode === "captions") return captionsView;
  return home;
};
