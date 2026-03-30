"use client";

import { useChatStore } from "@/stores/chatStore";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, AlertCircle, FileText, ExternalLink, BookOpen } from "lucide-react";
import ReactMarkdown from "react-markdown";

export function SourcePanel() {
    const { activeCitation, setActiveCitation } = useChatStore();

    if (!activeCitation) return null;

    const isVerified = activeCitation.verification_status === "verified";

    return (
        <Sheet open={!!activeCitation} onOpenChange={(open) => !open && setActiveCitation(null)}>
            <SheetContent className="w-full sm:max-w-md md:max-w-lg lg:max-w-xl overflow-y-auto bg-[#FAFAF9] border-l-stone-200 sm:pr-0">
                <SheetHeader className="pr-6 pb-6 border-b border-stone-200">
                    <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline" className="font-mono bg-white text-stone-500 border-stone-200">
                            Citation [{activeCitation.index}]
                        </Badge>
                        {isVerified ? (
                            <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50 border-emerald-200 flex items-center gap-1">
                                <CheckCircle2 size={12} /> NLI Verified
                            </Badge>
                        ) : (
                            <Badge className="bg-amber-50 text-amber-700 hover:bg-amber-50 border-amber-200 flex items-center gap-1">
                                <AlertCircle size={12} /> Low Confidence
                            </Badge>
                        )}
                    </div>
                    <SheetTitle className="font-display text-xl text-[#0D1B2A] leading-tight">
                        {activeCitation.source_title}
                    </SheetTitle>
                    <div className="flex flex-wrap text-sm text-stone-500 gap-x-4 gap-y-1 mt-2">
                        {activeCitation.edition && (
                            <span className="flex items-center gap-1"><BookOpen size={14} /> {activeCitation.edition}</span>
                        )}
                        {activeCitation.chapter && (
                            <span className="flex items-center gap-1"><FileText size={14} /> Ch: {activeCitation.chapter}</span>
                        )}
                        <span className="font-medium text-stone-700">Page {activeCitation.page_number}</span>
                    </div>
                </SheetHeader>

                <div className="pr-6 py-6 flex flex-col gap-6">
                    {/* Exact Extracted Text */}
                    {activeCitation.excerpt && (
                        <div>
                            <h3 className="text-xs font-bold text-stone-400 uppercase mb-3">Extracted Chunk</h3>
                            <div className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm prose prose-stone prose-sm max-w-none font-body text-stone-700">
                                <ReactMarkdown>
                                    {activeCitation.excerpt}
                                </ReactMarkdown>
                            </div>
                        </div>
                    )}

                    {/* PDF Viewer Mockup */}
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="text-xs font-bold text-stone-400 uppercase">Original Document</h3>
                            <Button variant="ghost" size="sm" className="h-8 text-[#0D1B2A] font-medium">
                                Open Full PDF <ExternalLink size={14} className="ml-2" />
                            </Button>
                        </div>

                        {/* This div acts as a placeholder for react-pdf later */}
                        <div className="w-full aspect-[1/1.4] bg-stone-200/50 rounded-xl border border-stone-200 flex flex-col items-center justify-center p-8 text-center">
                            <FileText className="text-stone-300 mb-4" size={48} />
                            <p className="text-sm font-medium text-stone-500">Document Viewer Ready</p>
                            <p className="text-xs text-stone-400 mt-2 max-w-[200px]">
                                Wire up `react-pdf` here to render page {activeCitation.page_number} of {activeCitation.source_title}.
                            </p>
                        </div>
                    </div>
                </div>
            </SheetContent>
        </Sheet>
    );
}