import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  if (!seconds || isNaN(seconds)) return "00:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export function getStatusColor(status: string): string {
  switch (status.toUpperCase()) {
    case "COMPLETED":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    case "RENDERING":
    case "MATCHING":
    case "DIRECTING":
    case "TRANSCRIBING":
    case "INGESTING":
      return "bg-amber-500/10 text-amber-400 border-amber-500/30 animate-pulse";
    case "QUEUED":
      return "bg-blue-500/10 text-blue-400 border-blue-500/30";
    case "FAILED":
      return "bg-rose-500/10 text-rose-400 border-rose-500/30";
    default:
      return "bg-zinc-800 text-zinc-400 border-zinc-700";
  }
}
