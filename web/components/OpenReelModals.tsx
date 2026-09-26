"use client";

import React from "react";
import { Film, X, ExternalLink } from "lucide-react";

interface OpenReelExportModalProps {
  openReelModalData: any;
  onClose: () => void;
  onLaunchEmbedded: (id: string) => void;
  selectedJobId?: string;
}

export const OpenReelExportModal: React.FC<OpenReelExportModalProps> = ({
  openReelModalData,
  onClose,
  onLaunchEmbedded,
  selectedJobId,
}) => {
  if (!openReelModalData) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-indigo-500/40 rounded-3xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
          <div className="flex items-center gap-2">
            <Film className="w-5 h-5 text-indigo-400" />
            <h3 className="font-bold text-sm text-white">OpenReel Project Exported (.oreel)</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-lg hover:bg-zinc-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-xs text-zinc-300">
          <p>Your edit plan has been compiled into a native OpenReel Schema 1.2.0 non-destructive multitrack project.</p>

          <div className="bg-black/60 rounded-xl p-3 border border-zinc-800 space-y-1 font-mono text-[11px]">
            <div className="text-indigo-300 font-bold">Files Generated:</div>
            <div className="text-zinc-400 truncate">.oreel: {openReelModalData.files?.oreel}</div>
            <div className="text-zinc-400 truncate">Manifest: {openReelModalData.files?.manifest}</div>
            <div className="text-zinc-400 truncate">Edit Plan: {openReelModalData.files?.plan}</div>
          </div>

          <div className="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-3 text-[11px] space-y-1">
            <div className="font-bold text-indigo-200">How to open in OpenReel Editor:</div>
            <ol className="list-decimal list-inside space-y-1 text-zinc-300">
              <li>Start OpenReel web app (<code className="text-indigo-300">pnpm --filter @openreel/web dev</code>).</li>
              <li>In OpenReel, select <strong>File → Open Project</strong> and choose the <code className="text-indigo-300">project.oreel</code> file.</li>
              <li>All timeline tracks (Speaker A-Roll, B-Roll cutaways, subtitles, and audio) remain 100% editable!</li>
            </ol>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-bold text-xs px-4 py-2 rounded-xl transition-all"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => {
              const id =
                openReelModalData.project_id?.replace(/^proj_/, "") || selectedJobId;
              onClose();
              if (id) onLaunchEmbedded(id);
            }}
            className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all flex items-center gap-1.5 shadow-md shadow-emerald-950/40"
          >
            <Film className="w-3.5 h-3.5" />
            <span>Launch in OpenReel Studio</span>
          </button>
        </div>
      </div>
    </div>
  );
};

interface EmbeddedOpenReelModalProps {
  embeddedOpenReelJob: string | null;
  onClose: () => void;
}

export const EmbeddedOpenReelModal: React.FC<EmbeddedOpenReelModalProps> = ({
  embeddedOpenReelJob,
  onClose,
}) => {
  if (!embeddedOpenReelJob) return null;

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex flex-col p-2 sm:p-4">
      <div className="bg-zinc-900 border border-emerald-500/40 rounded-2xl flex flex-col flex-1 overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950">
          <div className="flex items-center gap-2">
            <Film className="w-5 h-5 text-emerald-400" />
            <span className="font-bold text-sm text-white">OpenReel Video Editor</span>
            <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono">
              Schema 1.2.0 • Non-Destructive Multi-Track
            </span>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={`http://localhost:5173/#/editor?loadJob=${encodeURIComponent(embeddedOpenReelJob)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all"
              title="Open in standalone tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Popout Tab
            </a>
            <button
              type="button"
              onClick={onClose}
              className="text-zinc-400 hover:text-white p-1.5 rounded-lg hover:bg-zinc-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div className="flex-1 w-full bg-zinc-950 relative">
          <iframe
            src={`http://localhost:5173/#/editor?loadJob=${encodeURIComponent(embeddedOpenReelJob)}`}
            className="w-full h-full border-0"
            allow="camera; microphone; display-capture; clipboard-read; clipboard-write; web-share"
            title="OpenReel Editor"
          />
        </div>
      </div>
    </div>
  );
};
