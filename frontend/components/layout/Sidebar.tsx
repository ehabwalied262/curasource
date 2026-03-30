"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/stores/chatStore";
import {
    Plus,
    MessageSquare,
    Library,
    Settings,
    HeartPulse,
    PanelLeftClose,
} from "lucide-react";

const RECENT_SESSIONS = [
    { id: "1", title: "What is STEMI?" },
    { id: "2", title: "Progressive overload" },
    { id: "3", title: "Metformin in CKD" },
];

export function Sidebar() {
    const pathname = usePathname();
    const toggleSidebar = useChatStore((s) => s.toggleSidebar);
    const clearChat = useChatStore((s) => s.clearChat);

    const isActive = (path: string) => pathname === path || pathname.startsWith(`${path}/`);

    return (
        <aside className="w-[260px] h-screen bg-[#171717] border-r border-white/10 flex flex-col flex-shrink-0 z-20">

            {/* Brand + Collapse */}
            <div className="h-14 flex items-center justify-between px-4 border-b border-white/10">
                <Link href="/" className="flex items-center gap-2 text-stone-100 hover:opacity-80 transition-opacity">
                    <HeartPulse className="text-emerald-400" size={20} strokeWidth={2.5} />
                    <span className="font-display font-bold text-lg tracking-tight">CuraSource</span>
                </Link>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleSidebar}
                    className="h-8 w-8 text-stone-400 hover:text-stone-100 hover:bg-white/10"
                >
                    <PanelLeftClose size={16} />
                </Button>
            </div>

            {/* New Chat */}
            <div className="p-3">
                <Button
                    onClick={clearChat}
                    className="w-full justify-start gap-2 bg-white/5 text-stone-300 border border-white/10 hover:bg-white/10 hover:text-stone-100"
                    variant="outline"
                >
                    <Plus size={15} />
                    New Chat
                </Button>
            </div>

            {/* Recent Sessions */}
            <div className="flex-1 overflow-y-auto px-2 py-1">
                <h3 className="px-3 text-[10px] font-bold text-stone-500 uppercase tracking-widest mb-2">
                    Recent
                </h3>
                <div className="space-y-0.5">
                    {RECENT_SESSIONS.map((session) => (
                        <Link
                            key={session.id}
                            href={`/chat/${session.id}`}
                            className="flex items-center gap-2.5 px-3 py-2 text-sm text-stone-400 rounded-lg hover:bg-white/5 hover:text-stone-200 transition-colors group"
                        >
                            <MessageSquare size={13} className="shrink-0" />
                            <span className="truncate">{session.title}</span>
                        </Link>
                    ))}
                </div>
            </div>

            {/* Bottom Nav */}
            <div className="p-2 border-t border-white/10 space-y-0.5">
                <Link
                    href="/sources"
                    className={cn(
                        "flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                        isActive("/sources")
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "text-stone-400 hover:bg-white/5 hover:text-stone-200"
                    )}
                >
                    <Library size={15} />
                    Corpus Browser
                </Link>
                <Link
                    href="/settings"
                    className={cn(
                        "flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                        isActive("/settings")
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "text-stone-400 hover:bg-white/5 hover:text-stone-200"
                    )}
                >
                    <Settings size={15} />
                    Settings
                </Link>
            </div>
        </aside>
    );
}
