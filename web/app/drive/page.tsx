"use client";

import React, { useState, useEffect } from "react";
import {
  Cloud,
  FolderSync,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FolderInput,
  FolderOutput,
  Download,
  Upload,
  ArrowRight,
  ExternalLink,
  ShieldAlert
} from "lucide-react";

export default function DriveHub() {
  const [driveStatus, setDriveStatus] = useState<any>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<any>(null);

  const fetchDriveStatus = async () => {
    try {
      const res = await fetch("/api/drive/status");
      if (res.ok) {
        const data = await res.json();
        setDriveStatus(data);
      }
    } catch (err) {
      console.error("Failed to load drive status:", err);
    }
  };

  useEffect(() => {
    fetchDriveStatus();
  }, []);

  const handleSyncNow = async () => {
    setIsSyncing(true);
    setSyncResult(null);
    try {
      const res = await fetch("/api/drive/sync", { method: "POST" });
      const data = await res.json();
      setSyncResult(data);
      fetchDriveStatus();
    } catch (err) {
      setSyncResult({ status: "error", message: String(err) });
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Title */}
      <div>
        <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs uppercase tracking-wider mb-1">
          <Cloud className="w-4 h-4" />
          Cloud Storage Bridge
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Google Drive Cloud Synchronization</h1>
        <p className="text-xs text-zinc-400 mt-1">
          Automate two-way ingestion and delivery between your Google Drive folders and the AI B-Roll Autopilot engine.
        </p>
      </div>

      {/* Connection Card */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Cloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">Google Drive API Connection</h2>
              <p className="text-xs text-zinc-400">OAuth 2.0 / Service Account Token status</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {driveStatus?.connected ? (
              <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-full">
                <AlertTriangle className="w-3.5 h-3.5" />
                Local Standby Mode
              </span>
            )}
          </div>
        </div>

        {/* Sync Mechanism Flow */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          {/* Inbound */}
          <div className="bg-zinc-950 border border-zinc-800/80 rounded-xl p-4 space-y-2">
            <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold">
              <FolderInput className="w-4 h-4" />
              1. Inbound Watcher
            </div>
            <p className="text-xs text-zinc-400">
              Drop raw videos into your Google Drive Input folder. Autopilot detects and downloads them automatically.
            </p>
            <div className="text-[11px] font-mono bg-zinc-900/80 px-2 py-1 rounded text-zinc-400 truncate">
              ID: {driveStatus?.input_folder_id || "Not Configured (.env)"}
            </div>
          </div>

          {/* Autopilot Engine */}
          <div className="bg-zinc-950 border border-indigo-500/30 rounded-xl p-4 space-y-2 flex flex-col justify-center text-center">
            <div className="text-xs font-semibold text-indigo-400 flex items-center justify-center gap-1.5">
              <RefreshCw className="w-4 h-4" />
              2. Autopilot Processing
            </div>
            <p className="text-xs text-zinc-400">
              Whisper $\to$ Emotional Director $\to$ Watermark-Free Footage $\to$ 9:16 Render $\to$ AI Reviewer
            </p>
          </div>

          {/* Outbound */}
          <div className="bg-zinc-950 border border-zinc-800/80 rounded-xl p-4 space-y-2">
            <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold">
              <FolderOutput className="w-4 h-4" />
              3. Outbound Delivery
            </div>
            <p className="text-xs text-zinc-400">
              Finished vertical videos, .srt subtitles, and review reports are automatically uploaded back to Drive.
            </p>
            <div className="text-[11px] font-mono bg-zinc-900/80 px-2 py-1 rounded text-zinc-400 truncate">
              ID: {driveStatus?.output_folder_id || "Not Configured (.env)"}
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-zinc-800/80">
          <p className="text-xs text-zinc-400">
            Sync pulls any newly dropped videos from your Drive folder and uploads pending deliverables.
          </p>
          <button
            onClick={handleSyncNow}
            disabled={isSyncing}
            className="w-full sm:w-auto bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold text-xs px-5 py-2.5 rounded-xl flex items-center justify-center gap-2 transition-colors shadow-lg shadow-cyan-600/20"
          >
            <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
            {isSyncing ? "Syncing Drive..." : "Sync Drive Now"}
          </button>
        </div>

        {/* Sync Result Alert */}
        {syncResult && (
          <div className={`p-4 rounded-xl text-xs border ${
            syncResult.status === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : "bg-zinc-950 border-zinc-800 text-zinc-300"
          }`}>
            <p className="font-semibold">{syncResult.status === "success" ? "Sync Completed Successfully" : "Sync Notification"}</p>
            <p className="mt-1 text-zinc-400">{syncResult.message || `Downloaded ${syncResult.downloaded_count || 0} new clips from Google Drive.`}</p>
          </div>
        )}
      </div>

      {/* Setup Guide */}
      <div className="bg-zinc-900/30 border border-zinc-800/80 rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-semibold text-zinc-200">How to Connect Your Google Drive (One-Time Setup)</h3>
        <ol className="list-decimal list-inside space-y-2 text-xs text-zinc-400">
          <li>Create a Google Cloud Project with the <strong className="text-zinc-200">Google Drive API</strong> enabled.</li>
          <li>Configure an OAuth 2.0 Desktop or Web Client ID and secret.</li>
          <li>Set <code className="bg-zinc-800 text-zinc-200 px-1 py-0.5 rounded">GOOGLE_CLIENT_ID</code>, <code className="bg-zinc-800 text-zinc-200 px-1 py-0.5 rounded">GOOGLE_CLIENT_SECRET</code>, <code className="bg-zinc-800 text-zinc-200 px-1 py-0.5 rounded">GOOGLE_DRIVE_INPUT_FOLDER_ID</code>, and <code className="bg-zinc-800 text-zinc-200 px-1 py-0.5 rounded">GOOGLE_DRIVE_OUTPUT_FOLDER_ID</code> in your <code className="bg-zinc-800 text-zinc-200 px-1 py-0.5 rounded">.env</code>.</li>
          <li>Autopilot will automatically synchronize in the background!</li>
        </ol>
      </div>
    </div>
  );
}
