import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Sparkles, Video, Cloud, Settings, Film, BrainCircuit } from "lucide-react";

export const metadata: Metadata = {
  title: "AI B-Roll Autopilot Studio",
  description: "Autonomous Emotional B-Roll Editing & Continuous Learning Engine",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col bg-zinc-950 text-zinc-100 antialiased selection:bg-indigo-500/30 selection:text-indigo-200">
        {/* Top Navigation */}
        <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md px-6 py-3.5">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                <Film className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold tracking-tight text-base text-zinc-100">AI B-ROLL AUTOPILOT</span>
                  <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Studio MVP</span>
                </div>
                <p className="text-xs text-zinc-400">Emotional Resonance & Cloud Watcher</p>
              </div>
            </Link>

            {/* Nav Links */}
            <nav className="flex items-center gap-1.5 bg-zinc-900/90 border border-zinc-800 p-1 rounded-xl">
              <Link
                href="/"
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <Video className="w-3.5 h-3.5 text-indigo-400" />
                Studio
              </Link>
              <Link
                href="/drive"
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <Cloud className="w-3.5 h-3.5 text-cyan-400" />
                Google Drive
              </Link>
              <Link
                href="/settings"
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors"
              >
                <Settings className="w-3.5 h-3.5 text-zinc-400" />
                Settings
              </Link>
            </nav>

            {/* Live Indicator */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-full">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span className="font-medium">Pipeline Active</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-zinc-800/60 py-6 text-center text-xs text-zinc-500">
          AI B-Roll Autopilot Studio • Powered by Whisper, Gemini AI Director & Azure Container Apps
        </footer>
      </body>
    </html>
  );
}
