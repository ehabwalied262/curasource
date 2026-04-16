"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message, Citation } from "@/types";
import { CheckCircle2, AlertCircle, BookOpen, HeartPulse, Pencil, Check, X, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";
import { useChat } from "@/hooks/useChat";
import { AssistantActions } from "./MessageActions";

/** Turns raw PDF filenames into clean book titles */
function cleanSourceTitle(raw: string): string {
    return raw
        .replace(/\.pdf$/i, "")
        .replace(/_/g, " ")
        .replace(/\s+/g, " ")
        .replace(/(\d+)(th|st|nd|rd)Ed/gi, "$1$2 Ed.")
        .trim();
}

export function ChatMessage({ message }: { message: Message }) {
    const isAssistant = message.role === "assistant";
    const isStreaming = useChatStore((s) => s.isStreaming);
    const isLoading = useChatStore((s) => s.isLoading);
    const messages = useChatStore((s) => s.messages);
    const isLastMessage = messages[messages.length - 1]?.id === message.id;
    const showCursor = isAssistant && isStreaming && isLastMessage;

    const { retryMessage, editAndResend } = useChat();

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
            "w-full py-8 px-4 group",
            isAssistant ? "bg-transparent" : "bg-white/[0.02]"
        )}>
            <div className="max-w-3xl mx-auto flex gap-4">

                {isAssistant && (
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center shrink-0 mt-1">
                        <HeartPulse className="text-emerald-400" size={15} strokeWidth={2.5} />
                    </div>
                )}

                <div className={cn("flex flex-col w-full overflow-hidden", !isAssistant && "pl-12")}>
                    <span className="text-[11px] font-bold text-stone-500 uppercase tracking-widest mb-3">
                        {isAssistant ? "CuraSource AI" : "You"}
                    </span>

                    {/* ── USER MESSAGE ── */}
                    {!isAssistant && (
                        isEditing ? (
                            <div className="flex flex-col gap-3">
                                <textarea
                                    value={editValue}
                                    onChange={(e) => setEditValue(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleEditSave(); }
                                        if (e.key === "Escape") handleEditCancel();
                                    }}
                                    autoFocus
                                    rows={3}
                                    className="w-full bg-[#2a2a2a] border border-white/20 rounded-lg px-4 py-3 text-stone-100 resize-none focus:outline-none focus:border-emerald-500/50"
                                    style={{ fontSize: "17px", lineHeight: 1.9 }}
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
                                    className="flex-1 text-stone-100"
                                    style={{ fontSize: "17px", lineHeight: 2 }}
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

                    {/* ── ASSISTANT MESSAGE ── */}
                    {isAssistant && (
                        <>
                            <div
                                className="prose prose-invert prose-stone max-w-none
                                    prose-p:text-stone-200 prose-p:mb-4
                                    prose-li:text-stone-200
                                    prose-headings:text-white prose-headings:font-semibold prose-headings:mt-6 prose-headings:mb-3
                                    prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                                    prose-strong:text-white prose-strong:font-semibold
                                    prose-code:text-emerald-400 prose-code:text-sm prose-code:font-mono
                                    prose-blockquote:border-emerald-500/50 prose-blockquote:text-stone-300
                                    prose-ul:my-3 prose-ol:my-3
                                    text-stone-200"
                                style={{
                                    fontSize: "17px",
                                    lineHeight: 2,
                                    letterSpacing: "0.01em",
                                }}
                            >
                                {message.content ? (
                                    <div className={showCursor ? "streaming-text" : ""}>
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {message.content}
                                        </ReactMarkdown>
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-3 py-2">
                                        <div className="thinking-dots">
                                            <span /><span /><span />
                                        </div>
                                        <span className="text-stone-500 text-sm">Searching sources...</span>
                                    </div>
                                )}
                                {showCursor && (
                                    <span className="inline-block w-[3px] h-[20px] bg-emerald-400 rounded-full ml-1 align-middle animate-pulse" />
                                )}
                            </div>

                            {/* Action buttons */}
                            {!isStreaming && message.content && (
                                <AssistantActions
                                    text={message.content}
                                    onRetry={() => retryMessage(message.id)}
                                />
                            )}

                            {/* ── SOURCES ── */}
                            {!isStreaming && message.citations && message.citations.length > 0 && (
                                <div className="mt-6 bg-[#1a1a1a] border border-white/[0.08] rounded-xl p-5">
                                    <span className="text-[11px] font-bold text-stone-400 uppercase tracking-widest flex items-center gap-1.5 mb-4">
                                        <BookOpen size={12} /> Referenced Sources
                                    </span>
                                    <div className="flex flex-col gap-2">
                                        {message.citations.map((cit) => (
                                            <SourceRow key={cit.index} citation={cit} />
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

function SourceRow({ citation }: { citation: Citation }) {
    const { setActiveCitation } = useChatStore();
    const isVerified = citation.verification_status === "verified";

    return (
        <div
            onClick={() => setActiveCitation(citation)}
            className="flex items-center gap-3 px-4 py-3 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-transparent hover:border-white/10 transition-all cursor-pointer group/source"
        >
            {/* Icon */}
            <div className="w-7 h-7 rounded-md bg-emerald-500/10 flex items-center justify-center shrink-0">
                <FileText size={13} className="text-emerald-400" />
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-stone-200 truncate">
                    {cleanSourceTitle(citation.source_title)}
                </p>
                <p className="text-[11px] text-stone-500 mt-0.5">
                    {citation.chapter ? `Ch. ${citation.chapter} · ` : ""}Page {citation.page_number}
                </p>
            </div>

            {/* Verification badge */}
            <div className="shrink-0 flex items-center gap-1.5">
                {isVerified ? (
                    <>
                        <span className="text-[10px] text-emerald-500 font-medium hidden group-hover/source:inline">Verified</span>
                        <CheckCircle2 className="text-emerald-500" size={14} />
                    </>
                ) : (
                    <>
                        <span className="text-[10px] text-amber-500 font-medium hidden group-hover/source:inline">Low confidence</span>
                        <AlertCircle className="text-amber-500" size={14} />
                    </>
                )}
            </div>
        </div>
    );
}
