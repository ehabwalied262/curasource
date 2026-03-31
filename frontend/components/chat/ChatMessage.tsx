"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message, Citation } from "@/types";
import { CheckCircle2, AlertCircle, BookOpen, HeartPulse, Pencil, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";
import { useChat } from "@/hooks/useChat";
import { AssistantActions } from "./MessageActions";

export function ChatMessage({ message }: { message: Message }) {
    const isAssistant = message.role === "assistant";
    const isStreaming = useChatStore((s) => s.isStreaming);
    const isLoading = useChatStore((s) => s.isLoading);
    const messages = useChatStore((s) => s.messages);
    const isLastMessage = messages[messages.length - 1]?.id === message.id;
    const showCursor = isAssistant && isStreaming && isLastMessage;

    const { retryMessage, editAndResend } = useChat();

    // Edit state for user messages
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState(message.content);

    const handleEditSave = async () => {
        if (!editValue.trim()) return;
        setIsEditing(false);
        await editAndResend(message.id, editValue);
    };

    const handleEditCancel = () => {
        setEditValue(message.content);
        setIsEditing(false);
    };

    return (
        <div className={cn(
            "w-full py-7 px-4 group",
            isAssistant ? "bg-transparent" : "bg-white/[0.03]"
        )}>
            <div className="max-w-3xl mx-auto flex gap-4">

                {/* Avatar — only for assistant */}
                {isAssistant && (
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
                        <HeartPulse className="text-emerald-400" size={15} strokeWidth={2.5} />
                    </div>
                )}

                <div className={cn("flex flex-col gap-2 w-full overflow-hidden", !isAssistant && "pl-12")}>
                    <span className="text-[11px] font-bold text-stone-500 uppercase tracking-widest">
                        {isAssistant ? "CuraSource AI" : "You"}
                    </span>

                    {/* USER MESSAGE */}
                    {!isAssistant && (
                        isEditing ? (
                            <div className="flex flex-col gap-2">
                                <textarea
                                    value={editValue}
                                    onChange={(e) => setEditValue(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleEditSave(); }
                                        if (e.key === "Escape") handleEditCancel();
                                    }}
                                    autoFocus
                                    rows={3}
                                    className="w-full bg-[#2a2a2a] border border-white/20 rounded-lg px-4 py-3 text-[17px] text-stone-100 resize-none focus:outline-none focus:border-emerald-500/50"
                                    style={{ fontFamily: "var(--font-tiempos, Georgia, serif)", lineHeight: 1.9 }}
                                />
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={handleEditSave}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm cursor-pointer transition-colors"
                                    >
                                        <Check size={13} /> Send
                                    </button>
                                    <button
                                        onClick={handleEditCancel}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-stone-300 text-sm cursor-pointer transition-colors"
                                    >
                                        <X size={13} /> Cancel
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="flex items-start gap-2">
                                <p
                                    className="flex-1 text-stone-100 leading-[1.9]"
                                    style={{ fontFamily: "var(--font-tiempos, Georgia, serif)", fontSize: "17px" }}
                                >
                                    {message.content}
                                </p>
                                {!isLoading && (
                                    <button
                                        onClick={() => { setEditValue(message.content); setIsEditing(true); }}
                                        className="shrink-0 p-1.5 rounded-md text-stone-600 hover:text-stone-300 hover:bg-white/10 opacity-0 group-hover:opacity-100 transition-all cursor-pointer mt-0.5"
                                        title="Edit message"
                                    >
                                        <Pencil size={14} />
                                    </button>
                                )}
                            </div>
                        )
                    )}

                    {/* ASSISTANT MESSAGE */}
                    {isAssistant && (
                        <>
                            <div
                                className="prose prose-invert prose-stone max-w-none
                                    prose-p:leading-[1.9] prose-p:text-stone-100
                                    prose-li:leading-[1.9] prose-li:text-stone-100
                                    prose-headings:text-white prose-headings:font-semibold
                                    prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg
                                    prose-strong:text-white prose-strong:font-semibold
                                    prose-code:text-emerald-400 prose-code:text-sm prose-code:font-mono
                                    prose-blockquote:border-emerald-500 prose-blockquote:text-stone-300
                                    text-stone-100"
                                style={{ fontFamily: "var(--font-tiempos, Georgia, serif)", fontSize: "17px" }}
                            >
                                {message.content ? (
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {message.content}
                                    </ReactMarkdown>
                                ) : (
                                    <span className="text-stone-500">Thinking…</span>
                                )}
                                {showCursor && (
                                    <span className="inline-block w-[2px] h-[18px] bg-emerald-400 ml-0.5 align-middle animate-pulse" />
                                )}
                            </div>

                            {/* Action buttons — copy, sound, retry */}
                            {!isStreaming && message.content && (
                                <AssistantActions
                                    text={message.content}
                                    onRetry={() => retryMessage(message.id)}
                                />
                            )}

                            {/* Citations */}
                            {!isStreaming && message.citations && message.citations.length > 0 && (
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
                        </>
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
