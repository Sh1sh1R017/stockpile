"use client";

import React from "react";
import {
  Tv,
  X,
  Sliders,
  Zap,
  Sparkles,
} from "lucide-react";

interface HdrUpscaleModalProps {
  isOpen: boolean;
  onClose: () => void;
  hdrScale: number;
  setHdrScale: (scale: number) => void;
  hdrTone: string;
  setHdrTone: (tone: string) => void;
  hdrFastMode: boolean;
  setHdrFastMode: (fast: boolean) => void;
  isUpscalingHdr: boolean;
  hdrProgress: number;
  handleStartHdrUpscale: () => void;
}

export const HdrUpscaleModal: React.FC<HdrUpscaleModalProps> = ({
  isOpen,
  onClose,
  hdrScale,
  setHdrScale,
  hdrTone,
  setHdrTone,
  hdrFastMode,
  setHdrFastMode,
  isUpscalingHdr,
  hdrProgress,
  handleStartHdrUpscale,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-purple-500/40 rounded-3xl max-w-lg w-full shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 to-pink-600 text-white flex items-center justify-center shadow-lg shadow-purple-600/30">
              <Tv className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <span>⚡ SDR2HDR Upscaler & HDR10</span>
                <span className="text-[9px] font-bold uppercase tracking-wider bg-pink-500/20 text-pink-300 border border-pink-500/40 px-2 py-0.5 rounded-full">
                  10-bit Rec.2020
                </span>
              </h3>
              <p className="text-xs text-zinc-400">
                AI Inverse Tone Mapping (ITM) + Super-Resolution Lanczos Upscaling
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          {/* Output Resolution & Super-Resolution Scale */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-purple-400" />
              Target Resolution & Upscaling
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { scale: 1.0, label: "1080x1920", sub: "1.0x Native HDR10" },
                { scale: 1.5, label: "1620x2880", sub: "1.5x QHD+ Ultra" },
                { scale: 2.0, label: "2160x3840", sub: "2.0x 4K UHD" },
              ].map((item) => (
                <button
                  key={item.scale}
                  type="button"
                  onClick={() => setHdrScale(item.scale)}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    hdrScale === item.scale
                      ? "bg-purple-600/20 border-purple-500 text-white shadow-sm"
                      : "bg-zinc-950/70 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <div className="text-xs font-bold">{item.label}</div>
                  <div className="text-[10px] text-zinc-500">{item.sub}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Tone Mapping Style */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Brightness & Dynamic Range Anchoring
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setHdrTone("vivid")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  hdrTone === "vivid"
                    ? "bg-amber-500/20 border-amber-500 text-white shadow-sm"
                    : "bg-zinc-950/70 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                }`}
              >
                <div className="text-xs font-bold flex items-center gap-1.5">
                  <span>🔥 Vivid (Viral Pop)</span>
                </div>
                <div className="text-[10px] text-zinc-400 mt-1">
                  Maps whites to peak nits. Maximum pop on OLED smartphone screens (TikTok / Reels / Shorts).
                </div>
              </button>
              <button
                type="button"
                onClick={() => setHdrTone("reference")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  hdrTone === "reference"
                    ? "bg-indigo-500/20 border-indigo-500 text-white shadow-sm"
                    : "bg-zinc-950/70 border-zinc-800 text-zinc-400 hover:border-zinc-700"
                }`}
              >
                <div className="text-xs font-bold flex items-center gap-1.5">
                  <span>🎬 Reference (BT.2408)</span>
                </div>
                <div className="text-[10px] text-zinc-400 mt-1">
                  Standard broadcast anchoring (203 nit diffuse white) with specular headroom.
                </div>
              </button>
            </div>
          </div>

          {/* Fast Mode Toggle */}
          <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-3 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold text-zinc-200">Fast AI Mode</div>
              <div className="text-[10px] text-zinc-500">
                Optimized spatial masks & fast HEVC 10-bit encoding
              </div>
            </div>
            <input
              type="checkbox"
              checked={hdrFastMode}
              onChange={(e) => setHdrFastMode(e.target.checked)}
              className="w-4 h-4 accent-purple-500 cursor-pointer"
            />
          </div>

          {/* Status / Live Progress if running */}
          {isUpscalingHdr && (
            <div className="space-y-1.5 bg-purple-950/40 border border-purple-500/30 rounded-2xl p-3">
              <div className="flex justify-between text-xs font-semibold text-purple-200">
                <span>Upscaling & Tone Mapping...</span>
                <span className="font-mono text-pink-300 font-bold">{hdrProgress.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-zinc-950 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 transition-all duration-300"
                  style={{ width: `${hdrProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            disabled={isUpscalingHdr}
            onClick={handleStartHdrUpscale}
            className="bg-gradient-to-r from-purple-600 via-pink-600 to-rose-600 hover:from-purple-500 hover:to-rose-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-purple-600/30 transition-all hover:scale-[1.02]"
          >
            <Sparkles className={`w-3.5 h-3.5 ${isUpscalingHdr ? "animate-spin" : ""}`} />
            <span>{isUpscalingHdr ? `Upscaling (${hdrProgress.toFixed(0)}%)...` : "⚡ Start SDR2HDR Upscale"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
