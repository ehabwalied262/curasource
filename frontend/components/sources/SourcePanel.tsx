"use client";

import { useChatStore } from "@/stores/chatStore";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import {
    CheckCircle2,
    AlertCircle,
    FileText,
    BookOpen,
    X,
    Quote,
    BarChart3,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

/** Turns raw PDF filenames into clean book titles */
function cleanSourceTitle(raw: string): string {
    return raw
        .replace(/\.pdf$/i, "")
        .replace(/_/g, " ")
        .replace(/\s+/g, " ")
        .replace(/(\d+)(th|st|nd|rd)Ed/gi, "$1$2 Ed.")
        .trim();
}

export function SourcePanel() {
    const { activeCitation, setActiveCitation } = useChatStore();

    if (!activeCitation) return null;

    const isVerified = activeCitation.verification_status === "verified";
    const confidencePercent = Math.round(activeCitation.verification_score * 100);

    return (
        <Sheet
            open={!!activeCitation}
            onOpenChange={(open) => !open && setActiveCitation(null)}
        >
            <SheetContent className="w-full sm:max-w-lg overflow-y-auto bg-[#1a1a1a] border-l border-white/10 p-0">
                {/* ── Header ── */}
                <div className="sticky top-0 z-10 bg-[#1a1a1a]/95 backdrop-blur-md border-b border-white/10 px-6 py-5">
                    <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                            {/* Badges */}
                            <div className="flex items-center gap-2 mb-3">
                                <Badge
                                    variant="outline"
                                    className="font-mono text-stone-400 border-white/20 bg-white/5 text-xs"
                                >
                                    Source [{activeCitation.index}]
                                </Badge>
                                {isVerified ? (
                                    <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 text-xs flex items-center gap-1">
                                        <CheckCircle2 size={11} /> Verified
                                    </Badge>
                                ) : (
                                    <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-xs flex items-center gap-1">
                                        <AlertCircle size={11} /> Low Confidence
                                    </Badge>
                                )}
                            </div>

                            {/* Title */}
                            <h2 className="text-lg font-semibold text-stone-100 leading-snug">
                                {cleanSourceTitle(activeCitation.source_title)}
                            </h2>

                            {/* Metadata row */}
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-stone-500">
                                {activeCitation.edition && (
                                    <span className="flex items-center gap-1.5">
                                        <BookOpen size={11} />
                                        {activeCitation.edition}
                                    </span>
                                )}
                                {activeCitation.chapter && (
                                    <span className="flex items-center gap-1.5">
                                        <FileText size={11} />
                                        Chapter {activeCitation.chapter}
                                    </span>
                                )}
                                <span className="flex items-center gap-1.5 text-stone-400 font-medium">
                                    <FileText size={11} />
                                    Page {activeCitation.page_number}
                                </span>
                                <span className="flex items-center gap-1.5">
                                    <BarChart3 size={11} />
                                    {confidencePercent}% match
                                </span>
                            </div>
                        </div>

                        {/* Close button */}
                        <button
                            onClick={() => setActiveCitation(null)}
                            className="shrink-0 p-1.5 rounded-lg text-stone-500 hover:text-stone-200 hover:bg-white/10 transition-colors cursor-pointer"
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* ── Excerpt ── */}
                <div className="px-6 py-6">
                    {activeCitation.excerpt ? (
                        <div>
                            <div className="flex items-center gap-2 mb-4">
                                <Quote size={14} className="text-emerald-400" />
                                <h3 className="text-[11px] font-bold text-stone-400 uppercase tracking-widest">
                                    Source Excerpt
                                </h3>
                            </div>

                            <div className="relative">
                                {/* Accent bar */}
                                <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-full bg-emerald-500/40" />

                                <div
                                    className="pl-5 prose prose-invert prose-sm max-w-none
                                        prose-p:text-stone-300 prose-p:leading-relaxed prose-p:mb-3
                                        prose-li:text-stone-300
                                        prose-strong:text-stone-100
                                        prose-headings:text-stone-100
                                        text-stone-300"
                                    style={{
                                        fontFamily: "var(--font-tiempos, Georgia, serif)",
                                        fontSize: "15px",
                                        lineHeight: 1.85,
                                    }}
                                >
                                    <ReactMarkdown>{activeCitation.excerpt}</ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <FileText className="text-stone-700 mb-3" size={32} />
                            <p className="text-sm text-stone-500">No excerpt available</p>
                        </div>
                    )}

                    {/* ── Confidence meter ── */}
                    <div className="mt-8 bg-white/[0.03] border border-white/[0.08] rounded-xl p-4">
                        <h3 className="text-[10px] font-bold text-stone-500 uppercase tracking-widest mb-3">
                            Relevance Score
                        </h3>
                        <div className="flex items-center gap-3">
                            <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${
                                        confidencePercent > 70
                                            ? "bg-emerald-500"
                                            : confidencePercent > 50
                                            ? "bg-amber-500"
                                            : "bg-red-500"
                                    }`}
                                    style={{ width: `${confidencePercent}%` }}
                                />
                            </div>
                            <span
                                className={`text-sm font-semibold tabular-nums ${
                                    confidencePercent > 70
                                        ? "text-emerald-400"
                                        : confidencePercent > 50
                                        ? "text-amber-400"
                                        : "text-red-400"
                                }`}
                            >
                                {confidencePercent}%
                            </span>
                        </div>
                        <p className="text-[11px] text-stone-600 mt-2">
                            {confidencePercent > 70
                                ? "High similarity to your query — this source directly supports the answer."
                                : confidencePercent > 50
                                ? "Moderate relevance — this source partially relates to your query."
                                : "Low match — this source may not directly answer your question."}
                        </p>
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}
