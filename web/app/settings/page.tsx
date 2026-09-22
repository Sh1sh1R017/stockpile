"use client";

import React, { useState, useEffect } from "react";
import {
  Settings,
  Brain,
  Cloud,
  Cpu,
  Database,
  CheckCircle2,
  Sliders,
  Layers,
  Sparkles,
  Terminal,
  ShieldCheck
} from "lucide-react";

export default function SettingsHub() {
  const [health, setHealth] = useState<any>(null);
  const [learningRules, setLearningRules] = useState<any[]>([]);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const [hRes, lRes] = await Promise.all([
          fetch("/api/health"),
          fetch("/api/learning")
        ]);
        if (hRes.ok) setHealth(await hRes.json());
        if (lRes.ok) setLearningRules(await lRes.json());
      } catch (err) {
        console.error("Failed to load settings:", err);
      }
    };
    fetchSettings();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Title */}
      <div>
        <div className="flex items-center gap-2 text-violet-400 font-semibold text-xs uppercase tracking-wider mb-1">
          <Settings className="w-4 h-4" />
          System & Cloud Engine
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Cloud Configuration & Diagnostics</h1>
        <p className="text-xs text-zinc-400 mt-1">
          Manage Azure cloud container settings, AI director models, and persistent emotional learning rules.
        </p>
      </div>

      {/* Azure Cloud Architecture Overview */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <Cloud className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">Azure Container Apps Architecture</h2>
            <p className="text-xs text-zinc-400">Serverless container deployment with auto-scale & HTTPS ingress</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-1">
            <span className="text-[11px] font-semibold text-blue-400 uppercase">Compute</span>
            <p className="text-xs font-medium text-zinc-200">Azure Container Apps</p>
            <p className="text-[11px] text-zinc-500">FastAPI Backend + Next.js Web Frontend</p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-1">
            <span className="text-[11px] font-semibold text-cyan-400 uppercase">Cloud Storage</span>
            <p className="text-xs font-medium text-zinc-200">Google Drive & Azure Blob</p>
            <p className="text-[11px] text-zinc-500">Persistent storage for raw clips & final renders</p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-1">
            <span className="text-[11px] font-semibold text-emerald-400 uppercase">AI Pipeline</span>
            <p className="text-xs font-medium text-zinc-200">Whisper + Gemini 3.5/2.5</p>
            <p className="text-[11px] text-zinc-500">Director, Reviewer & Zero-Tolerance Watermark Scanner</p>
          </div>
        </div>
      </div>

      {/* Persistent Learned Rules Card */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <Brain className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">Persistent Emotional Learning Rules</h2>
              <p className="text-xs text-zinc-400">Rules active in SQLite database steering future B-roll selections</p>
            </div>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
            {learningRules.length} Active Rules
          </span>
        </div>

        <div className="space-y-2.5 pt-2">
          {learningRules.length === 0 ? (
            <div className="text-center py-6 text-xs text-zinc-500">No custom rules yet. Rate clips in Studio to train autopilot!</div>
          ) : (
            learningRules.map((rule, idx) => (
              <div key={idx} className="bg-zinc-950 border border-zinc-800/80 rounded-xl p-3.5 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-zinc-200">{rule.thematic_category}</span>
                  <span className="text-[10px] text-zinc-500">Confidence: {rule.confidence || "High"}</span>
                </div>
                {rule.preferred_metaphors && (
                  <p className="text-xs text-emerald-400">
                    <strong className="text-zinc-400 font-normal">Preferred: </strong> {rule.preferred_metaphors}
                  </p>
                )}
                {rule.avoided_metaphors && (
                  <p className="text-xs text-rose-400">
                    <strong className="text-zinc-400 font-normal">Strictly Avoided: </strong> {rule.avoided_metaphors}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Engine Diagnostics */}
      {health && (
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-zinc-400" />
            Engine Diagnostics & Environment
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800">
              <span className="text-zinc-500">Whisper Engine</span>
              <p className="font-semibold text-zinc-200 mt-0.5">{health.whisper_model}</p>
            </div>
            <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800">
              <span className="text-zinc-500">AI Director Model</span>
              <p className="font-semibold text-zinc-200 mt-0.5 truncate">{health.gemini_model}</p>
            </div>
            <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800">
              <span className="text-zinc-500">Database Engine</span>
              <p className="font-semibold text-zinc-200 mt-0.5">SQLite (autopilot.db)</p>
            </div>
            <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800">
              <span className="text-zinc-500">YouTube Importer</span>
              <p className="font-semibold text-emerald-400 mt-0.5">Active (yt-dlp)</p>
            </div>
          </div>

          {/* Pexels Integration Status */}
          <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="text-xs font-bold text-zinc-200">Pexels 1080x1920 Stock Video API</span>
              <p className="text-[11px] text-zinc-400">
                Watermark-free, royalty-free vertical footage provider inspired by AI-B-roll.
              </p>
            </div>
            <span
              className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border ${
                health.pexels_available
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-amber-500/10 text-amber-400 border-amber-500/20"
              }`}
            >
              {health.pexels_available ? "Active" : "Optional (Set PEXELS_API_KEY in .env)"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
