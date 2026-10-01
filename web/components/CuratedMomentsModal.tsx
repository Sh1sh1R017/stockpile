"use client";

import React from "react";
import {
  X,
  Sparkles,
  ShieldCheck,
  Search,
  Clock,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";
import { CampaignSummary, CuratedMoment } from "../lib/types";

interface CuratedMomentsModalProps {
  isOpen: boolean;
  onClose: () => void;
  campaigns: CampaignSummary[];
  selectedCampaignId: string;
  curatedMomentsTab: "moments" | "rules";
  setCuratedMomentsTab: (tab: "moments" | "rules") => void;
  momentSearchQuery: string;
  setMomentSearchQuery: (q: string) => void;
  momentFilterAngle: string;
  setMomentFilterAngle: (angle: string) => void;
  onSelectMoment: (moment: CuratedMoment) => void;
}

export const CuratedMomentsModal: React.FC<CuratedMomentsModalProps> = ({
  isOpen,
  onClose,
  campaigns,
  selectedCampaignId,
  curatedMomentsTab,
  setCuratedMomentsTab,
  momentSearchQuery,
  setMomentSearchQuery,
  momentFilterAngle,
  setMomentFilterAngle,
  onSelectMoment,
}) => {
  if (!isOpen) return null;

  const activeCampaign = campaigns.find((c) => c.id === selectedCampaignId);

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-emerald-500/40 rounded-3xl max-w-5xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center text-lg shadow-inner">
              🎯
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">
                  {activeCampaign?.name || "Campaign"} Hub
                </h3>
              </div>
              <p className="text-xs text-zinc-400">
                {activeCampaign?.description || "Campaign moments and rules"}
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

        {/* Inner Tabs: Moments Catalog vs Rules */}
        <div className="px-5 py-3 border-b border-zinc-800 bg-zinc-950/40 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCuratedMomentsTab("moments")}
              className={`text-xs font-bold px-3.5 py-1.5 rounded-xl flex items-center gap-2 transition-all ${
                curatedMomentsTab === "moments"
                  ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                  : "text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Curated Moments</span>
              <span className="text-[10px] bg-emerald-800/80 px-1.5 py-0.2 rounded-full font-mono">
                {activeCampaign?.curated_moments?.length || 0}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setCuratedMomentsTab("rules")}
              className={`text-xs font-bold px-3.5 py-1.5 rounded-xl flex items-center gap-2 transition-all ${
                curatedMomentsTab === "rules"
                  ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                  : "text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Campaign Rules & The No List</span>
            </button>
          </div>

          {curatedMomentsTab === "moments" && (
            <div className="relative max-w-xs w-full">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                value={momentSearchQuery}
                onChange={(e) => setMomentSearchQuery(e.target.value)}
                placeholder="Search moments (Trae, Knicks, AAU, pass)..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
              />
            </div>
          )}
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto flex-1 space-y-4">
          {curatedMomentsTab === "moments" ? (
            <div className="space-y-4">
              {/* Category Chips */}
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { key: "all", label: "All Moments" },
                  { key: "debate", label: "⚔️ Debates & Controversies" },
                  { key: "story", label: "📖 Stories & AAU Memories" },
                  { key: "technique", label: "🏀 Skills & Technique" },
                  { key: "take", label: "🔥 Hot Takes" },
                ].map((chip) => (
                  <button
                    key={chip.key}
                    type="button"
                    onClick={() => setMomentFilterAngle(chip.key)}
                    className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition-all ${
                      momentFilterAngle === chip.key
                        ? "bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-sm"
                        : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                    }`}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>

              {/* Moments Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {(activeCampaign?.curated_moments || [])
                  .filter((m) => {
                    if (momentFilterAngle !== "all") {
                      const angle = m.angle?.toLowerCase() || "";
                      if (!angle.includes(momentFilterAngle)) return false;
                    }
                    if (!momentSearchQuery.trim()) return true;
                    const q = momentSearchQuery.toLowerCase();
                    return (
                      m.moment_id.toLowerCase().includes(q) ||
                      m.screen_hook.toLowerCase().includes(q) ||
                      m.post_caption.toLowerCase().includes(q) ||
                      (m.broll_theme && m.broll_theme.toLowerCase().includes(q))
                    );
                  })
                  .map((m) => (
                    <div
                      key={m.moment_id}
                      className="bg-zinc-950/80 border border-zinc-800/90 hover:border-emerald-500/50 rounded-2xl p-4 space-y-2.5 transition-all group flex flex-col justify-between"
                    >
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-md">
                            {m.moment_id}
                          </span>
                          <span className="font-mono text-[11px] text-zinc-400 flex items-center gap-1">
                            <Clock className="w-3 h-3 text-zinc-500" />
                            {m.timestamp_range} ({Math.round(m.end_time_sec - m.start_time_sec)}s)
                          </span>
                        </div>

                        <div className="text-xs font-bold text-zinc-100 group-hover:text-emerald-300 transition-colors">
                          &quot;{m.screen_hook}&quot;
                        </div>

                        <p className="text-[11px] text-zinc-400 italic">
                          &quot;{m.post_caption}&quot;
                        </p>

                        {m.broll_theme && (
                          <div className="text-[10px] text-zinc-400 bg-zinc-900/80 rounded-lg p-2 border border-zinc-800/60">
                            <span className="font-semibold text-zinc-300">Suggested B-roll:</span> {m.broll_theme}
                          </div>
                        )}

                        {m.broll_sources && m.broll_sources.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {m.broll_sources.map((s, idx) => (
                              <span
                                key={idx}
                                className="text-[9px] font-medium bg-zinc-900 text-zinc-400 px-1.5 py-0.5 rounded border border-zinc-800"
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-zinc-900 flex items-center justify-between">
                        <span className="text-[10px] text-emerald-500 font-medium">
                          {m.angle ? `Angle: ${m.angle}` : "Curated Moment"}
                        </span>
                        <button
                          type="button"
                          onClick={() => onSelectMoment(m)}
                          className="bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white border border-emerald-500/40 text-[11px] font-semibold px-2.5 py-1 rounded-lg transition-all flex items-center gap-1"
                        >
                          <span>Use This Moment</span>
                          <ChevronRight className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          ) : (
            <div className="space-y-5 text-left max-w-4xl mx-auto">
              {/* Payout specs table */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                  <div className="text-[10px] uppercase font-bold text-zinc-400">Payout Rate</div>
                  <div className="text-base font-extrabold text-emerald-400 mt-0.5">$1.25</div>
                  <div className="text-[10px] text-zinc-500">per 1,000 views</div>
                </div>
                <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                  <div className="text-[10px] uppercase font-bold text-zinc-400">Total Bounty</div>
                  <div className="text-base font-extrabold text-white mt-0.5">$7,500</div>
                  <div className="text-[10px] text-zinc-500">~6M views pool</div>
                </div>
                <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                  <div className="text-[10px] uppercase font-bold text-zinc-400">Cap Per Clip</div>
                  <div className="text-base font-extrabold text-white mt-0.5">$300 Max</div>
                  <div className="text-[10px] text-zinc-500">240,000 views</div>
                </div>
                <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 text-center">
                  <div className="text-[10px] uppercase font-bold text-zinc-400">Min to Qualify</div>
                  <div className="text-base font-extrabold text-amber-400 mt-0.5">2,000 Views</div>
                  <div className="text-[10px] text-zinc-500">pays $2.50+</div>
                </div>
              </div>

              {/* The 6 Golden Rules */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  The 6 Rules Every Clip Must Pass
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                    <div className="text-xs font-bold text-emerald-300">Rule 1: 40%+ US, Canada, UK Geo</div>
                    <p className="text-[11px] text-zinc-400">
                      Post between 12pm-9pm Eastern. Use English text hooks and American sports context so algorithms target NBA viewers.
                    </p>
                  </div>
                  <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                    <div className="text-xs font-bold text-emerald-300">Rule 2: 1%+ Engagement (Debates)</div>
                    <p className="text-[11px] text-zinc-400">
                      Frame hot takes where viewers fight in comments. Comment fights push clips to 100k+ views.
                    </p>
                  </div>
                  <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                    <div className="text-xs font-bold text-emerald-300">Rule 3: 0% AI Video & Real B-Roll Only</div>
                    <p className="text-[11px] text-zinc-400">
                      Zero AI video or Opus clips allowed. Autopilot only uses authentic NBA/sports footage capped at 33% total duration.
                    </p>
                  </div>
                  <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                    <div className="text-xs font-bold text-emerald-300">Rule 4: Pure Dialogue (No Phonk/BGM)</div>
                    <p className="text-[11px] text-zinc-400">
                      Submissions with phonk music or loud tracks get rejected. Autopilot automatically disables background music.
                    </p>
                  </div>
                  <div className="bg-zinc-950/80 border border-zinc-800 rounded-2xl p-3.5 space-y-1">
                    <div className="text-xs font-bold text-emerald-300">Rule 5: Burned-in Word-by-Word Subtitles</div>
                    <p className="text-[11px] text-zinc-400">
                      High contrast, perfectly spelled, safe-zone elevated subtitles so they never obscure the platform buttons or watermark.
                    </p>
                  </div>
                  <div className="bg-zinc-950/80 border border-emerald-500/40 rounded-2xl p-3.5 space-y-1 bg-emerald-950/20">
                    <div className="text-xs font-bold text-emerald-300">Rule 6: Mandatory YT: @mpj Watermark</div>
                    <p className="text-[11px] text-zinc-400">
                      Autopilot automatically composites the official high-resolution YT: @mpj watermark across 100% of video duration.
                    </p>
                  </div>
                </div>
              </div>

              {/* The Instant Rejection List */}
              <div className="bg-rose-950/20 border border-rose-500/30 rounded-2xl p-4 space-y-2">
                <h4 className="text-xs font-bold text-rose-300 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  Instant Rejections (&quot;The No List&quot;)
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] text-zinc-300">
                  <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Reposting MPJ&apos;s socials</div>
                  <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Phonk or BGM music</div>
                  <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ AI video / avatars</div>
                  <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Aura / glow / skull edits</div>
                  <div className="bg-zinc-950/60 rounded-lg p-2 border border-zinc-800">❌ Low-effort uncut clips</div>
                  <div className="bg-zinc-950/60 rounded-lg p-2 border border-rose-500/40 text-rose-300">❌ Missing @mpj watermark</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
          <span className="text-xs text-zinc-500">
            AI B-Roll Autopilot • Campaign Engine Active
          </span>
          <button
            type="button"
            onClick={onClose}
            className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-5 py-2 rounded-xl transition-all shadow-md shadow-emerald-600/30"
          >
            Close Hub
          </button>
        </div>
      </div>
    </div>
  );
};
