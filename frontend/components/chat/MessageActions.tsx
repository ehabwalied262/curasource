"use client";

import { useState, useRef } from "react";
import { Copy, Volume2, RotateCcw, Square, Loader2, Check } from "lucide-react";

function stripMarkdown(text: string): string {
    return text
        .replace(/#{1,6}\s+/g, "")
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/\*(.*?)\*/g, "$1")
        .replace(/`{1,3}[^`]*`{1,3}/g, "")
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1")
        .replace(/^\s*[-*+]\s+/gm, "")
        .replace(/^\s*\d+\.\s+/gm, "")
        .trim();
}

interface AssistantActionsProps {
    text: string;
    onRetry: () => void;
}

export function AssistantActions({ text, onRetry }: AssistantActionsProps) {
    const [copied, setCopied] = useState(false);
    const [audioState, setAudioState] = useState<"idle" | "loading" | "playing">("idle");
    const audioRef = useRef<HTMLAudioElement | null>(null);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(stripMarkdown(text));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleSound = async () => {
        if (audioState === "playing") {
            audioRef.current?.pause();
            setAudioState("idle");
            return;
        }

        setAudioState("loading");
        try {
            const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
            const res = await fetch(`${apiBase}/tts`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: stripMarkdown(text) }),
            });

            if (!res.ok) throw new Error("TTS request failed");

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audioRef.current = audio;

            audio.onended = () => {
                setAudioState("idle");
                URL.revokeObjectURL(url);
            };

            await audio.play();
            setAudioState("playing");
        } catch (e) {
            console.error("TTS error:", e);
            setAudioState("idle");
        }
    };

    return (
        <div className="flex items-center gap-0.5 mt-3 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity duration-150">
            <ActionButton onClick={handleCopy} title="Copy">
                {copied ? (
                    <Check size={14} className="text-emerald-400" />
                ) : (
                    <Copy size={14} />
                )}
            </ActionButton>

            <ActionButton onClick={handleSound} title={audioState === "playing" ? "Stop" : "Read aloud"}>
                {audioState === "loading" ? (
                    <Loader2 size={14} className="animate-spin" />
                ) : audioState === "playing" ? (
                    <Square size={14} className="text-emerald-400 fill-emerald-400" />
                ) : (
                    <Volume2 size={14} />
                )}
            </ActionButton>

            <ActionButton onClick={onRetry} title="Retry">
                <RotateCcw size={14} />
            </ActionButton>
        </div>
    );
}

function ActionButton({
    onClick,
    title,
    children,
}: {
    onClick: () => void;
    title: string;
    children: React.ReactNode;
}) {
    return (
        <button
            onClick={onClick}
            title={title}
            className="p-1.5 rounded-md text-stone-500 hover:text-stone-200 hover:bg-white/10 transition-all cursor-pointer"
        >
            {children}
        </button>
    );
}
