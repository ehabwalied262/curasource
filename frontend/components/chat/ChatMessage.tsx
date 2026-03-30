import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message, Citation } from '@/types';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { CheckCircle2, AlertCircle, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore'; // <-- Add this import

export function ChatMessage({ message }: { message: Message }) {
    const isAssistant = message.role === "assistant";

    return (
        <div className={cn("flex w-full gap-4 py-8 px-4", !isAssistant ? "bg-stone-50/50" : "bg-white")}>
            <div className="max-w-3xl mx-auto flex gap-4 w-full">
                <Avatar className="h-8 w-8 rounded-sm">
                    <AvatarFallback className={isAssistant ? "bg-[#0D1B2A] text-white" : "bg-stone-200"}>
                        {isAssistant ? "CS" : "U"}
                    </AvatarFallback>
                </Avatar>

                <div className="flex flex-col gap-4 w-full overflow-hidden">
                    <span className="font-semibold text-sm text-stone-500 uppercase tracking-wider">
                        {isAssistant ? "CuraSource AI" : "You"}
                    </span>

                    <div className="prose prose-stone max-w-none leading-relaxed text-stone-800 font-body">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                        </ReactMarkdown>
                    </div>

                    {isAssistant && message.citations && (
                        <div className="mt-6 pt-6 border-t border-stone-100 flex flex-col gap-3">
                            <span className="text-xs font-bold text-stone-400 uppercase flex items-center gap-2">
                                <BookOpen size={14} /> Sources Used
                            </span>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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

// ---------- SourceCard with Zustand integration ----------
function SourceCard({ citation }: { citation: Citation }) {
    const { setActiveCitation } = useChatStore(); // <-- Get the action
    const isVerified = citation.verification_status === "verified";

    return (
        <div
            onClick={() => setActiveCitation(citation)} // <-- Set active citation on click
            className="flex flex-col p-3 rounded-md border border-stone-200 bg-stone-50 hover:border-stone-300 hover:shadow-sm transition-all cursor-pointer group text-left"
        >
            <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-mono font-medium text-stone-500">[{citation.index}]</span>
                {isVerified ? (
                    <CheckCircle2 className="text-emerald-500" size={14} />
                ) : (
                    <AlertCircle className="text-amber-500" size={14} />
                )}
            </div>
            <h4 className="text-sm font-semibold text-[#0D1B2A] line-clamp-1">{citation.source_title}</h4>
            <p className="text-[10px] text-stone-500 uppercase mt-1">
                {citation.chapter ? `Ch. ${citation.chapter} · ` : ""}Page {citation.page_number}
            </p>
        </div>
    );
}