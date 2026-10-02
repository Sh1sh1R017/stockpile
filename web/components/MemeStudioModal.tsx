"use client";

import React from "react";
import {
  X,
  Sparkles,
  Search,
  CheckCircle2,
  Volume2,
  Download,
} from "lucide-react";
import { MemeTemplateOption, ShotDetail } from "../lib/types";

interface MemeStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  isStandaloneMode: boolean;
  memeTargetShot: ShotDetail | null;
  memeTemplates: MemeTemplateOption[];
  selectedTemplateKey: string;
  setSelectedTemplateKey: (key: string) => void;
  memeCaptions: Record<string, string>;
  setMemeCaptions: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  selectedSfxFile: string;
  setSelectedSfxFile: (file: string) => void;
  sfxCatalog: any[];
  memeSearchQuery: string;
  setMemeSearchQuery: (q: string) => void;
  isGeneratingMeme: boolean;
  isAutoGeneratingMeme: Record<string, boolean>;
  handleAutoGenerateMeme: (shotId: string) => Promise<void>;
  handleGenerateMeme: () => void;
  handleSelectTemplate: (key: string) => void;
  standaloneMemeResult: { video_url?: string; image_url?: string; shot_id?: string } | null;
}

export const MemeStudioModal: React.FC<MemeStudioModalProps> = ({
  isOpen,
  onClose,
  isStandaloneMode,
  memeTargetShot,
  memeTemplates,
  selectedTemplateKey,
  memeCaptions,
  setMemeCaptions,
  selectedSfxFile,
  setSelectedSfxFile,
  sfxCatalog,
  memeSearchQuery,
  setMemeSearchQuery,
  isGeneratingMeme,
  isAutoGeneratingMeme,
  handleAutoGenerateMeme,
  handleGenerateMeme,
  handleSelectTemplate,
  standaloneMemeResult,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-zinc-900 border border-zinc-800 rounded-3xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-fuchsia-600/20 border border-fuchsia-500/30 text-fuchsia-400 flex items-center justify-center text-lg shadow-inner">
              🎭
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                {isStandaloneMode
                  ? "Meme Studio — 1,036 HD Meme Templates"
                  : `Meme Cutaway Customizer (Cutaway ${memeTargetShot?.shot_id})`}
              </h3>
              <p className="text-xs text-zinc-400">
                {isStandaloneMode
                  ? "Create standalone 9:16 vertical video meme cutaways with punchline SFX."
                  : "Transform this dialogue moment into an editorial meme cutaway with custom captions."}
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

        {/* Spoken Quote Banner (if editing a shot) */}
        {memeTargetShot?.dialogue_quote && (
          <div className="bg-indigo-950/40 border-b border-indigo-500/20 px-6 py-2.5 flex items-center justify-between">
            <div className="text-xs text-indigo-200 truncate mr-3">
              <span className="font-semibold text-indigo-400">Spoken Quote:</span> "{memeTargetShot.dialogue_quote}"
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                disabled={isAutoGeneratingMeme[memeTargetShot.shot_id]}
                onClick={async () => {
                  await handleAutoGenerateMeme(memeTargetShot.shot_id);
                  onClose();
                }}
                className="text-[11px] font-semibold text-white bg-gradient-to-r from-fuchsia-600 to-indigo-600 hover:from-fuchsia-500 hover:to-indigo-500 px-3 py-1 rounded-lg transition-all shadow-md flex items-center gap-1.5 disabled:opacity-50"
              >
                <Sparkles className={`w-3.5 h-3.5 ${isAutoGeneratingMeme[memeTargetShot.shot_id] ? "animate-spin" : ""}`} />
                <span>{isAutoGeneratingMeme[memeTargetShot.shot_id] ? "Writing Meme..." : "🤖 Auto AI Meme"}</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  const q = memeTargetShot.dialogue_quote || "";
                  if (selectedTemplateKey === "stepped_in_shit") {
                    setMemeCaptions({ shoe_text: q });
                  } else if (selectedTemplateKey === "drake") {
                    setMemeCaptions({ top_text: "Making Excuses", bottom_text: q });
                  } else {
                    setMemeCaptions({ caption: q });
                  }
                }}
                className="text-[11px] font-semibold text-indigo-300 hover:text-white bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/30 px-2.5 py-1 rounded-lg transition-all"
              >
                📋 Use as Caption
              </button>
            </div>
          </div>
        )}

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* LEFT: Template Picker & Search (5 cols) */}
            <div className="md:col-span-5 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-zinc-300 uppercase tracking-wider">
                  Select Template ({memeTemplates.length})
                </label>
              </div>

              {/* Search bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={memeSearchQuery}
                  onChange={(e) => setMemeSearchQuery(e.target.value)}
                  placeholder="Search templates (e.g. stepped, drake, clown)..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl pl-9 pr-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
                />
              </div>

              {/* Popular Archetype Pills */}
              <div className="flex flex-wrap gap-1.5 pt-1">
                {[
                  { key: "ishowspeed_shock", label: "⚡ Speed Shock" },
                  { key: "moms_kinda_homeless", label: "🥺 Mom's Kinda Homeless" },
                  { key: "not_your_personal_pornstar", label: "🤬 Not Your Personal Pornstar" },
                  { key: "caseoh_rage", label: "🎙️ CaseOh Rage" },
                  { key: "jynxzi_freakout", label: "🎮 Jynxzi Freakout" },
                  { key: "the_trusted_doctor", label: "👨‍⚕️ The Specialist (IYKYK)" },
                  { key: "gigachad", label: "🗿 Gigachad" },
                  { key: "hide_the_pain_harold", label: "👴 Harold" },
                  { key: "stepped_in_shit", label: "👞 Stepped in Shit" },
                  { key: "drake", label: "🙅‍♂️ Drake" },
                  { key: "clown", label: "🤡 Clown" },
                  { key: "same_picture", label: "🏢 Same Picture" },
                  { key: "batman_slap", label: "👋 Batman Slap" },
                  { key: "blinking_guy", label: "😳 Blinking Guy" },
                  { key: "gta_ah_shit", label: "🚶‍♂️ GTA Ah Shit" },
                ].map((p) => (
                  <button
                    type="button"
                    key={p.key}
                    onClick={() => handleSelectTemplate(p.key)}
                    className={`text-[10px] font-semibold px-2 py-1 rounded-lg border transition-all ${
                      selectedTemplateKey === p.key
                        ? "bg-fuchsia-600 text-white border-fuchsia-500 shadow-sm"
                        : "bg-zinc-800/80 hover:bg-zinc-700/80 text-zinc-300 border-zinc-700/60"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              {/* Scrollable Template Card List */}
              <div className="max-h-[340px] overflow-y-auto space-y-1.5 pr-1 border border-zinc-800/80 rounded-2xl p-2 bg-zinc-950/60">
                {memeTemplates
                  .filter((t) => {
                    if (!memeSearchQuery.trim()) return true;
                    const q = memeSearchQuery.toLowerCase();
                    return (
                      t.name.toLowerCase().includes(q) ||
                      t.key.toLowerCase().includes(q) ||
                      t.category.toLowerCase().includes(q)
                    );
                  })
                  .map((t) => {
                    const isSelected = selectedTemplateKey === t.key;
                    return (
                      <div
                        key={t.key}
                        onClick={() => handleSelectTemplate(t.key)}
                        className={`p-2.5 rounded-xl text-xs flex items-center gap-3 cursor-pointer transition-all border ${
                          isSelected
                            ? "bg-fuchsia-600/20 border-fuchsia-500/60 text-white shadow-md"
                            : "hover:bg-zinc-900 border-transparent text-zinc-300"
                        }`}
                      >
                        <img
                          src={t.preview_url}
                          alt={t.name}
                          className="w-12 h-12 rounded-lg object-cover bg-black border border-zinc-800 shrink-0"
                          loading="lazy"
                        />
                        <div className="truncate flex-1">
                          <p className="font-bold truncate text-xs">{t.name}</p>
                          <p className="text-[10px] text-zinc-400 truncate mt-0.5">{t.category}</p>
                        </div>
                        {isSelected && (
                          <CheckCircle2 className="w-4 h-4 text-fuchsia-400 shrink-0" />
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* RIGHT: Live Preview, Captions, SFX & Generation (7 cols) */}
            <div className="md:col-span-7 space-y-4">
              {(() => {
                const tmpl =
                  memeTemplates.find((t) => t.key === selectedTemplateKey) || memeTemplates[0];
                return (
                  <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-fuchsia-400 flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" />
                        Template: {tmpl?.name || selectedTemplateKey}
                      </span>
                      <span className="text-[10px] font-mono text-zinc-400 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
                        {tmpl?.category}
                      </span>
                    </div>

                    {tmpl?.description && (
                      <p className="text-[11px] text-zinc-400 italic">{tmpl.description}</p>
                    )}

                    {/* Image Preview */}
                    <div className="rounded-xl overflow-hidden border border-zinc-800/80 bg-black/60 max-h-[160px] flex items-center justify-center">
                      <img
                        src={tmpl?.preview_url || `/api/memes/templates/${selectedTemplateKey}/preview`}
                        alt={tmpl?.name}
                        className="max-h-[160px] w-auto max-w-full object-contain mx-auto"
                      />
                    </div>

                    {/* Dynamic Caption Input Fields */}
                    <div className="space-y-2.5 pt-1">
                      <label className="text-xs font-bold text-zinc-300 uppercase tracking-wider block">
                        Meme Captions
                      </label>

                      {tmpl?.fields && tmpl.fields.length > 0 ? (
                        tmpl.fields.map((f: any) => (
                          <div key={f.name} className="space-y-1">
                            <label className="text-[11px] font-semibold text-zinc-400">
                              {f.label}:
                            </label>
                            <input
                              type="text"
                              value={memeCaptions[f.name] || ""}
                              onChange={(e) =>
                                setMemeCaptions({ ...memeCaptions, [f.name]: e.target.value })
                              }
                              placeholder={f.placeholder}
                              className="w-full bg-zinc-900 border border-zinc-700/80 rounded-xl px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
                            />
                          </div>
                        ))
                      ) : (
                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-zinc-400">Caption:</label>
                          <input
                            type="text"
                            value={memeCaptions.caption || memeCaptions.shoe_text || memeCaptions.text || ""}
                            onChange={(e) =>
                              setMemeCaptions({ ...memeCaptions, caption: e.target.value })
                            }
                            placeholder="Enter punchline or caption text..."
                            className="w-full bg-zinc-900 border border-zinc-700/80 rounded-xl px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-fuchsia-500"
                          />
                        </div>
                      )}
                    </div>

                    {/* Punchline SFX Selector */}
                    <div className="space-y-1.5 pt-1">
                      <label className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                        <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                        Punchline Sound Effect (SFX Library)
                      </label>

                      <div className="flex items-center gap-2">
                        <select
                          value={selectedSfxFile}
                          onChange={(e) => setSelectedSfxFile(e.target.value)}
                          className="flex-1 bg-zinc-900 border border-zinc-700/80 rounded-xl px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
                        >
                          <option value="81_vine_boom.mp3">💥 Vine Boom (Dramatic Meme Punchline)</option>
                          <option value="59_cartoon_slip_whoosh.mp3">💨 Cartoon Slip Whoosh</option>
                          <option value="01_bonk_impact.mp3">🔨 Bonk Impact</option>
                          <option value="11_bruh.mp3">😐 Bruh Sound Effect</option>
                          <option value="60_sad_violin.mp3">🎻 Sad Violin (Tragic Humor)</option>
                          <option value="55_subtle_bass_drop.mp3">🔊 Subtle Bass Drop</option>
                          <option value="04_camera_shutter.mp3">📸 Camera Shutter Flash</option>
                          <option value="28_bell_ding.mp3">🔔 Bell Ding</option>
                          {sfxCatalog
                            .filter(
                              (s) =>
                                ![
                                  "81_vine_boom.mp3",
                                  "59_cartoon_slip_whoosh.mp3",
                                  "01_bonk_impact.mp3",
                                  "11_bruh.mp3",
                                  "60_sad_violin.mp3",
                                  "55_subtle_bass_drop.mp3",
                                  "04_camera_shutter.mp3",
                                  "28_bell_ding.mp3",
                                ].includes(s.file)
                            )
                            .slice(0, 30)
                            .map((s) => (
                              <option key={s.file} value={s.file}>
                                {s.name || s.file}
                              </option>
                            ))}
                        </select>

                        <audio
                          controls
                          preload="none"
                          className="h-7 w-28 shrink-0 opacity-90 hover:opacity-100"
                          src={`/api/sfx/${selectedSfxFile}`}
                        />
                      </div>
                    </div>

                    {/* Standalone Result Preview */}
                    {standaloneMemeResult?.video_url && (
                      <div className="bg-zinc-900 border border-fuchsia-500/40 rounded-xl p-3 space-y-2 pt-2">
                        <div className="flex items-center justify-between text-xs text-fuchsia-300 font-bold">
                          <span>✓ Generated 9:16 Vertical Video:</span>
                          <a
                            href={standaloneMemeResult.video_url}
                            download="meme_cutaway.mp4"
                            className="text-[11px] text-white bg-fuchsia-600 hover:bg-fuchsia-500 px-2.5 py-1 rounded-lg flex items-center gap-1 transition-colors"
                          >
                            <Download className="w-3 h-3" />
                            Download MP4
                          </a>
                        </div>
                        <video
                          controls
                          autoPlay
                          preload="metadata"
                          className="max-h-[220px] w-auto max-w-full mx-auto rounded-lg border border-zinc-800"
                          src={standaloneMemeResult.video_url}
                        />
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 flex items-center justify-between">
          <span className="text-[11px] text-zinc-500 font-mono">
            Renders 1080x1920 9:16 vertical video cutaway with Ken Burns motion & punchline SFX
          </span>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleGenerateMeme}
              disabled={isGeneratingMeme}
              className="bg-fuchsia-600 hover:bg-fuchsia-500 disabled:opacity-50 text-white text-xs font-semibold px-5 py-2 rounded-xl flex items-center gap-2 shadow-lg shadow-fuchsia-600/30 transition-all hover:scale-[1.02]"
            >
              <Sparkles className={`w-3.5 h-3.5 ${isGeneratingMeme ? "animate-spin" : ""}`} />
              <span>
                {isGeneratingMeme
                  ? "Rendering Meme Video (FFmpeg)..."
                  : isStandaloneMode
                  ? "Generate 9:16 Meme Video"
                  : `Apply Meme to Shot ${memeTargetShot?.shot_id || ""}`}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
