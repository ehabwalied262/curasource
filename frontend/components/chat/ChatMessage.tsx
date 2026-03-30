import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, Citation } from '@/types';
import { CheckCircle2, AlertCircle, BookOpen, HeartPulse } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';

export function ChatMessage({ message }: { message: Message }) {
    const isAssistant = message.role === "assistant";

    return (
        <div className={cn(
            "w-full py-6 px-4",
            isAssistant ? "bg-transparent" : "bg-white/[0.03]"
        )}>
            <div className="max-w-3xl mx-auto flex gap-4">

                {/* Avatar — only for assistant */}
                {isAssistant && (
                    <div className="w-7 h-7 rounded-lg bg-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
                        <HeartPulse className="text-emerald-400" size={14} strokeWidth={2.5} />
                    </div>
                )}

                {/* Message content — indented to match avatar width when user */}
                <div className={cn("flex flex-col gap-3 w-full overflow-hidden", !isAssistant && "pl-11")}>
                    <span className="text-[10px] font-bold text-stone-500 uppercase tracking-widest">
                        {isAssistant ? "CuraSource AI" : "You"}
                    </span>

                    <div className="prose prose-invert prose-stone max-w-none leading-relaxed text-stone-300 prose-p:text-stone-300 prose-headings:text-stone-100 prose-strong:text-stone-200 prose-code:text-emerald-400">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                        </ReactMarkdown>
                    </div>

                    {/* Citations */}
                    {isAssistant && message.citations && message.citations.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-white/10 flex flex-col gap-3">
                            <span className="text-[10px] font-bold text-stone-500 uppercase tracking-widest flex items-center gap-1.5">
                                <BookOpen size={12} /> Sources
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {message.citations.map((cit) => (
                                    <SourceCard key={cit.index} citation={cit} />
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function SourceCard({ citation }: { citation: Citation }) {
    const { setActiveCitation } = useChatStore();
    const isVerified = citation.verification_status === "verified";

    return (
        <div
            onClick={() => setActiveCitation(citation)}
            className="flex flex-col p-3 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 transition-all cursor-pointer"
        >
            <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono text-stone-500">[{citation.index}]</span>
                {isVerified ? (
                    <CheckCircle2 className="text-emerald-500" size={13} />
                ) : (
                    <AlertCircle className="text-amber-500" size={13} />
                )}
            </div>
            <h4 className="text-xs font-semibold text-stone-300 line-clamp-1">{citation.source_title}</h4>
            <p className="text-[10px] text-stone-500 mt-1">
                {citation.chapter ? `Ch. ${citation.chapter} · ` : ""}Page {citation.page_number}
            </p>
        </div>
    );
}
