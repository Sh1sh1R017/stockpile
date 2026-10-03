"use client";

import React from "react";
import { Scissors, X } from "lucide-react";

interface InsertCutawayModalProps {
  isOpen: boolean;
  onClose: () => void;
  insertCutawayTime: number;
  setInsertCutawayTime: (t: number) => void;
  insertCutawayDur: number;
  setInsertCutawayDur: (d: number) => void;
  insertCutawayStyle: "stockpile" | "meme";
  setInsertCutawayStyle: (s: "stockpile" | "meme") => void;
  insertCutawayPrompt: string;
  setInsertCutawayPrompt: (p: string) => void;
  insertCutawayMemeTemplate: string;
  setInsertCutawayMemeTemplate: (t: string) => void;
  isInsertingCutaway: boolean;
  handleConfirmInsertCutaway: () => void;
  userTopicContext?: string | null;
}

export const InsertCutawayModal: React.FC<InsertCutawayModalProps> = ({
  isOpen,
  onClose,
  insertCutawayTime,
  setInsertCutawayTime,
  insertCutawayDur,
  setInsertCutawayDur,
  insertCutawayStyle,
  setInsertCutawayStyle,
  insertCutawayPrompt,
  setInsertCutawayPrompt,
  insertCutawayMemeTemplate,
  setInsertCutawayMemeTemplate,
  isInsertingCutaway,
  handleConfirmInsertCutaway,
  userTopicContext,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl max-w-lg w-full shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-violet-600/20 border border-violet-500/30 text-violet-400 flex items-center justify-center shadow-inner">
              <Scissors className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Insert Cutaway at {insertCutawayTime.toFixed(1)}s
              </h3>
              <p className="text-xs text-zinc-400">
                Split dialogue and insert visual B-roll or meme at current playhead.
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
          {/* Timing Controls */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">Start Time (s)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={insertCutawayTime}
                onChange={(e) => setInsertCutawayTime(parseFloat(e.target.value) || 0)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">Duration (s)</label>
              <input
                type="number"
                step="0.5"
                min="1.0"
                max="10.0"
                value={insertCutawayDur}
                onChange={(e) => setInsertCutawayDur(parseFloat(e.target.value) || 2.5)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-100 font-mono"
              />
            </div>
          </div>

          {/* Cutaway Type: Stock Footage vs Meme */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">Cutaway Style</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setInsertCutawayStyle("stockpile")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  insertCutawayStyle === "stockpile"
                    ? "bg-indigo-600/20 border-indigo-500 text-white shadow-sm"
                    : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <div className="text-xs font-bold">🎬 Stock Footage</div>
                <div className="text-[10px] text-zinc-500">Pexels 4K vertical B-roll</div>
              </button>

              <button
                type="button"
                onClick={() => setInsertCutawayStyle("meme")}
                className={`p-3 rounded-xl border text-left transition-all ${
                  insertCutawayStyle === "meme"
                    ? "bg-fuchsia-600/20 border-fuchsia-500 text-white shadow-sm"
                    : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <div className="text-xs font-bold">🎭 Meme Cutaway</div>
                <div className="text-[10px] text-zinc-500">Editorial meme + punchline SFX</div>
              </button>
            </div>
          </div>

          {/* Search prompt / meme fields */}
          {insertCutawayStyle === "stockpile" ? (
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
                  Visual Search Prompt
                </label>
                {userTopicContext && (
                  <button
                    type="button"
                    onClick={() => setInsertCutawayPrompt(userTopicContext)}
                    className="text-[10px] text-indigo-300 hover:text-indigo-200 underline font-mono truncate max-w-[200px]"
                    title={`Use clip topic: ${userTopicContext}`}
                  >
                    🎯 Use: {userTopicContext}
                  </button>
                )}
              </div>
              <input
                type="text"
                value={insertCutawayPrompt}
                onChange={(e) => setInsertCutawayPrompt(e.target.value)}
                placeholder="e.g. luxury watches, money finance, laptop coding..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          ) : (
            <div className="space-y-3">
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
                  Meme Template
                </label>
                <select
                  value={insertCutawayMemeTemplate}
                  onChange={(e) => setInsertCutawayMemeTemplate(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-fuchsia-500"
                >
                  <option value="ishowspeed_shock">⚡ IShowSpeed (Screaming Shock)</option>
                  <option value="moms_kinda_homeless">🥺 My Mom's Kinda Homeless (Speed Fortnite)</option>
                  <option value="not_your_personal_pornstar">🤬 Not Your Personal Pornstar! (Meltdown)</option>
                  <option value="caseoh_rage">🎙️ CaseOh (Headset Mic Rage)</option>
                  <option value="jynxzi_freakout">🎮 Jynxzi (Controller Disbelief)</option>
                  <option value="the_trusted_doctor">👨‍⚕️ The Specialist (IYKYK)</option>
                  <option value="gigachad">🗿 Gigachad</option>
                  <option value="hide_the_pain_harold">👴 Harold</option>
                  <option value="stepped_in_shit">👞 Stepped in Shit</option>
                  <option value="drake">🙅‍♂️ Drake Yes/No</option>
                  <option value="clown">🤡 Clown Makeup</option>
                  <option value="same_picture">🏢 Corporate Needs You</option>
                  <option value="batman_slap">👋 Batman Slap</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider">
                  Caption / Point of Emphasis
                </label>
                <input
                  type="text"
                  value={insertCutawayPrompt}
                  onChange={(e) => setInsertCutawayPrompt(e.target.value)}
                  placeholder="Point of humor or emphasis..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
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
            Cancel
          </button>
          <button
            type="button"
            disabled={isInsertingCutaway}
            onClick={handleConfirmInsertCutaway}
            className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2 rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02]"
          >
            <Scissors className={`w-3.5 h-3.5 ${isInsertingCutaway ? "animate-spin" : ""}`} />
            <span>{isInsertingCutaway ? "Inserting Cutaway..." : "Insert Cutaway"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
