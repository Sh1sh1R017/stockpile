"use client";

import React, { useRef } from "react";
import {
  RefreshCw,
  X,
  Search,
  Upload,
  Clock,
  CheckCircle2,
} from "lucide-react";
import { ShotDetail, StockVideoCandidate } from "../lib/types";

interface BrollSwapModalProps {
  isOpen: boolean;
  onClose: () => void;
  swapTargetShot: ShotDetail | null;
  swapTab: "search" | "upload";
  setSwapTab: (tab: "search" | "upload") => void;
  swapSearchQuery: string;
  setSwapSearchQuery: (q: string) => void;
  stockCandidates: StockVideoCandidate[];
  isSearchingStock: boolean;
  isSwappingStock: boolean;
  handleSearchStock: (q: string) => void;
  handleSelectStockCandidate: (cand: StockVideoCandidate) => void;
  isUploadingCustom: boolean;
  handleCustomVideoUpload: (file: File) => void;
}

export const BrollSwapModal: React.FC<BrollSwapModalProps> = ({
  isOpen,
  onClose,
  swapTargetShot,
  swapTab,
  setSwapTab,
  swapSearchQuery,
  setSwapSearchQuery,
  stockCandidates,
  isSearchingStock,
  isSwappingStock,
  handleSearchStock,
  handleSelectStockCandidate,
  isUploadingCustom,
  handleCustomVideoUpload,
}) => {
  const customVideoInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen || !swapTargetShot) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 flex items-center justify-center shadow-inner">
              <RefreshCw className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Swap Footage: Cutaway {swapTargetShot.shot_id}
              </h3>
              <p className="text-xs text-zinc-400">
                Replace existing footage with 4K royalty-free Pexels video or upload your own file.
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

        {/* Tab Selector: Pexels Search vs Custom Upload */}
        <div className="px-6 pt-4 pb-2 border-b border-zinc-800/80 flex items-center gap-3 bg-zinc-950/40">
          <button
            type="button"
            onClick={() => setSwapTab("search")}
            className={`text-xs font-semibold px-4 py-2 rounded-xl transition-all flex items-center gap-2 ${
              swapTab === "search"
                ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/20"
                : "text-zinc-400 hover:text-zinc-200 bg-zinc-900/60"
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            Pexels Stock Search
          </button>
          <button
            type="button"
            onClick={() => setSwapTab("upload")}
            className={`text-xs font-semibold px-4 py-2 rounded-xl transition-all flex items-center gap-2 ${
              swapTab === "upload"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                : "text-zinc-400 hover:text-zinc-200 bg-zinc-900/60"
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            Upload Custom Video
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {swapTab === "search" ? (
            <div className="space-y-4">
              {/* Search Query Input */}
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={swapSearchQuery}
                    onChange={(e) => setSwapSearchQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSearchStock(swapSearchQuery);
                    }}
                    placeholder="Search visual topic (e.g. luxury watch, coding laptop, handshake)..."
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-10 pr-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleSearchStock(swapSearchQuery)}
                  disabled={isSearchingStock}
                  className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-colors shadow-sm disabled:opacity-50"
                >
                  <Search className={`w-3.5 h-3.5 ${isSearchingStock ? "animate-spin" : ""}`} />
                  <span>{isSearchingStock ? "Searching..." : "Search"}</span>
                </button>
              </div>

              {/* Quick Pill Suggestions */}
              <div className="flex flex-wrap gap-1.5">
                {[
                  "luxury watch",
                  "focus typing laptop",
                  "business handshake",
                  "cash counting money",
                  "frustrated stress",
                  "confident smile",
                  "city drone aerial",
                ].map((pill) => (
                  <button
                    type="button"
                    key={pill}
                    onClick={() => {
                      setSwapSearchQuery(pill);
                      handleSearchStock(pill);
                    }}
                    className="text-[10px] bg-zinc-800/80 hover:bg-zinc-700/80 text-zinc-300 border border-zinc-700/60 px-2.5 py-1 rounded-lg transition-colors"
                  >
                    {pill}
                  </button>
                ))}
              </div>

              {/* Candidate Results Grid */}
              <div className="space-y-2 pt-2">
                <div className="flex items-center justify-between text-xs text-zinc-400">
                  <span>Available Clips ({stockCandidates.length})</span>
                  <span className="text-[10px] text-zinc-500">9:16 Vertical HD • 0 Watermarks</span>
                </div>

                {isSearchingStock ? (
                  <div className="p-12 text-center text-xs text-zinc-400 space-y-2">
                    <Clock className="w-6 h-6 animate-spin text-cyan-400 mx-auto" />
                    <p>Querying Pexels HD video catalog...</p>
                  </div>
                ) : stockCandidates.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-[380px] overflow-y-auto pr-1">
                    {stockCandidates.map((cand) => (
                      <div
                        key={cand.id}
                        className="bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800 hover:border-cyan-500/60 transition-all flex flex-col group"
                      >
                        <div className="relative aspect-[9/16] max-h-[180px] overflow-hidden bg-black flex items-center justify-center">
                          <img
                            src={cand.thumbnail}
                            alt="Candidate"
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                            loading="lazy"
                          />
                          <span className="absolute bottom-1.5 right-1.5 bg-black/80 text-[10px] text-zinc-200 px-1.5 py-0.5 rounded font-mono">
                            {cand.duration}s
                          </span>
                        </div>

                        <div className="p-2.5 space-y-2 flex-1 flex flex-col justify-between">
                          <div className="text-[11px] text-zinc-300 truncate font-medium">
                            Clip #{cand.id}
                          </div>
                          <button
                            type="button"
                            disabled={isSwappingStock}
                            onClick={() => handleSelectStockCandidate(cand)}
                            className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-[11px] font-bold py-1.5 rounded-lg flex items-center justify-center gap-1 transition-colors shadow-sm"
                          >
                            <CheckCircle2 className="w-3 h-3" />
                            <span>{isSwappingStock ? "Downloading..." : "Use This Clip"}</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center border border-dashed border-zinc-800 rounded-2xl text-xs text-zinc-500">
                    Search any topic above to preview available footage.
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Custom File Upload Tab */
            <div className="space-y-4 py-4">
              <div
                onClick={() => customVideoInputRef.current?.click()}
                className="border-2 border-dashed border-indigo-500/40 hover:border-indigo-400 bg-indigo-500/5 hover:bg-indigo-500/10 rounded-2xl p-10 text-center cursor-pointer transition-all"
              >
                <input
                  type="file"
                  ref={customVideoInputRef}
                  accept="video/*,.mp4,.mov,.mkv,.webm,.avi"
                  className="hidden"
                  onClick={(e) => {
                    e.stopPropagation();
                    (e.target as HTMLInputElement).value = "";
                  }}
                  onChange={(e) => {
                    if (e.target.files?.[0]) handleCustomVideoUpload(e.target.files[0]);
                  }}
                />
                <Upload className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
                <h4 className="text-sm font-bold text-zinc-100">Upload custom video for this shot</h4>
                <p className="text-xs text-zinc-400 mt-1">
                  Supports MP4, MOV. Will be automatically formatted to 1080x1920 9:16 vertical.
                </p>
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      customVideoInputRef.current?.click();
                    }}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all shadow-md shadow-indigo-600/20 inline-flex items-center gap-1.5"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Choose Video File
                  </button>
                </div>
                {isUploadingCustom && (
                  <p className="text-xs text-indigo-400 mt-3 animate-pulse">
                    Uploading and formatting video clip with FFmpeg...
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
          <span className="text-[11px] text-zinc-500 font-mono">
            Duration: {((swapTargetShot.end_time - swapTargetShot.start_time) || 2.5).toFixed(1)}s
          </span>
          <button
            type="button"
            onClick={onClose}
            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
