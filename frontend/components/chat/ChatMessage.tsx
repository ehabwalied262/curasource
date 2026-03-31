import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, Citation } from '@/types';
import { CheckCircle2, AlertCircle, BookOpen, HeartPulse } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';

export function ChatMessage({ message }: { message: Message }) {
    const isAssistant = message.role === "assistant";
    const isStreaming = useChatStore((s) => s.isStreaming);
    const messages = useChatStore((s) => s.messages);
    const isLastMessage = messages[messages.length - 1]?.id === message.id;
    const showCursor = isAssistant && isStreaming && isLastMessage;

    return (
        <div className={cn(
            "w-full py-7 px-4",
            isAssistant ? "bg-transparent" : "bg-white/[0.03]"
        )}>
            <div className="max-w-3xl mx-auto flex gap-4">

                {/* Avatar — only for assistant */}
                {isAssistant && (
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
                        <HeartPulse className="text-emerald-400" size={15} strokeWidth={2.5} />
                    </div>
                )}

                <div className={cn("flex flex-col gap-3 w-full overflow-hidden", !isAssistant && "pl-12")}>
                    <span className="text-[11px] font-bold text-stone-500 uppercase tracking-widest">
                        {isAssistant ? "CuraSource AI" : "You"}
                    </span>

                    <div className="prose prose-invert prose-stone max-w-none
                        prose-p:text-[15px] prose-p:leading-[1.85] prose-p:text-stone-200
                        prose-li:text-[15px] prose-li:leading-[1.85] prose-li:text-stone-200
                        prose-headings:text-stone-100 prose-headings:font-semibold
                        prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                        prose-strong:text-stone-100 prose-strong:font-semibold
                        prose-code:text-emerald-400 prose-code:text-sm
                        prose-blockquote:border-emerald-500 prose-blockquote:text-stone-400
                        text-stone-200">
                        {message.content ? (
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {message.content}
                            </ReactMarkdown>
                        ) : (
                            <span className="text-stone-500 text-[15px]">Thinking…</span>
                        )}
                        {showCursor && (
                            <span className="inline-block w-[2px] h-[18px] bg-emerald-400 ml-0.5 align-middle animate-pulse" />
                        )}
                    </div>

                    {/* Citations */}
                    {isAssistant && !isStreaming && message.citations && message.citations.length > 0 && (
                        <div className="mt-5 pt-4 border-t border-white/10 flex flex-col gap-3">
                            <span className="text-[11px] font-bold text-stone-500 uppercase tracking-widest flex items-center gap-1.5">
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
                <span className="text-[11px] font-mono text-stone-500">[{citation.index}]</span>
                {isVerified ? (
                    <CheckCircle2 className="text-emerald-500" size={13} />
                ) : (
                    <AlertCircle className="text-amber-500" size={13} />
                )}
            </div>
            <h4 className="text-[13px] font-semibold text-stone-300 line-clamp-1">{citation.source_title}</h4>
            <p className="text-[11px] text-stone-500 mt-1">
                {citation.chapter ? `Ch. ${citation.chapter} · ` : ""}Page {citation.page_number}
            </p>
        </div>
    );
}
