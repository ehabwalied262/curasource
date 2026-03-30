"use client";

import { useChatStore } from "@/stores/chatStore";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, FileText, BookOpen } from "lucide-react";
import ReactMarkdown from "react-markdown";

export function SourcePanel() {
    const { activeCitation, setActiveCitation } = useChatStore();

    if (!activeCitation) return null;

    const isVerified = activeCitation.verification_status === "verified";

    return (
        <Sheet open={!!activeCitation} onOpenChange={(open) => !open && setActiveCitation(null)}>
            <SheetContent className="w-full sm:max-w-md overflow-y-auto bg-[#171717] border-l border-white/10">
                <SheetHeader className="pb-5 border-b border-white/10">
                    <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="font-mono text-stone-400 border-white/20 bg-white/5 text-xs">
                            [{activeCitation.index}]
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
                    <SheetTitle className="text-stone-100 text-lg leading-snug">
                        {activeCitation.source_title}
                    </SheetTitle>
                    <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 text-xs text-stone-500">
                        {activeCitation.edition && (
                            <span className="flex items-center gap-1"><BookOpen size={11} /> {activeCitation.edition}</span>
                        )}
                        {activeCitation.chapter && (
                            <span className="flex items-center gap-1"><FileText size={11} /> Ch: {activeCitation.chapter}</span>
                        )}
                        <span className="text-stone-400 font-medium">Page {activeCitation.page_number}</span>
                    </div>
                </SheetHeader>

                <div className="py-5 flex flex-col gap-5">
                    {activeCitation.excerpt && (
                        <div>
                            <h3 className="text-[10px] font-bold text-stone-500 uppercase tracking-widest mb-2">Extracted Chunk</h3>
                            <div className="bg-white/5 border border-white/10 rounded-xl p-4 prose prose-invert prose-sm max-w-none text-stone-400 prose-p:text-stone-400">
                                <ReactMarkdown>{activeCitation.excerpt}</ReactMarkdown>
                            </div>
                        </div>
                    )}

                    <div>
                        <h3 className="text-[10px] font-bold text-stone-500 uppercase tracking-widest mb-2">Original Document</h3>
                        <div className="w-full aspect-[1/1.2] bg-white/5 rounded-xl border border-white/10 flex flex-col items-center justify-center p-8 text-center">
                            <FileText className="text-stone-700 mb-3" size={40} />
                            <p className="text-sm font-medium text-stone-500">PDF Viewer</p>
                            <p className="text-xs text-stone-600 mt-1 max-w-[180px]">
                                Page {activeCitation.page_number} of {activeCitation.source_title}
                            </p>
                        </div>
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}
