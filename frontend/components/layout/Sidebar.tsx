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
    Trash2,
} from "lucide-react";

export function Sidebar() {
    const pathname = usePathname();
    const {
        toggleSidebar,
        newChat,
        loadConversation,
        deleteConversation,
        conversations,
        activeConversationId,
    } = useChatStore();

    const isActive = (path: string) => pathname === path || pathname.startsWith(`${path}/`);

    // Group conversations by date
    const now = Date.now();
    const today = conversations.filter((c) => now - c.updatedAt < 86400000);
    const yesterday = conversations.filter(
        (c) => now - c.updatedAt >= 86400000 && now - c.updatedAt < 172800000
    );
    const older = conversations.filter((c) => now - c.updatedAt >= 172800000);

    return (
        <aside className="w-[260px] h-full bg-[#171717] border-r border-white/10 flex flex-col flex-shrink-0 z-20">

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
                    onClick={newChat}
                    className="w-full justify-start gap-2 bg-white/5 text-stone-300 border border-white/10 hover:bg-white/10 hover:text-stone-100"
                    variant="outline"
                >
                    <Plus size={15} />
                    New Chat
                </Button>
            </div>

            {/* Conversation History */}
            <div className="flex-1 overflow-y-auto px-2 py-1 space-y-4">
                {conversations.length === 0 ? (
                    <p className="px-3 text-[12px] text-stone-600 mt-2">No conversations yet.</p>
                ) : (
                    <>
                        <ConversationGroup
                            label="Today"
                            items={today}
                            activeId={activeConversationId}
                            onLoad={loadConversation}
                            onDelete={deleteConversation}
                        />
                        <ConversationGroup
                            label="Yesterday"
                            items={yesterday}
                            activeId={activeConversationId}
                            onLoad={loadConversation}
                            onDelete={deleteConversation}
                        />
                        <ConversationGroup
                            label="Older"
                            items={older}
                            activeId={activeConversationId}
                            onLoad={loadConversation}
                            onDelete={deleteConversation}
                        />
                    </>
                )}
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

function ConversationGroup({
    label,
    items,
    activeId,
    onLoad,
    onDelete,
}: {
    label: string;
    items: ReturnType<typeof useChatStore.getState>["conversations"];
    activeId: string;
    onLoad: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    if (items.length === 0) return null;
    return (
        <div>
            <h3 className="px-3 text-[10px] font-bold text-stone-500 uppercase tracking-widest mb-1">
                {label}
            </h3>
            <div className="space-y-0.5">
                {items.map((conv) => (
                    <div
                        key={conv.id}
                        className={cn(
                            "group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors",
                            conv.id === activeId
                                ? "bg-white/10 text-stone-100"
                                : "text-stone-400 hover:bg-white/5 hover:text-stone-200"
                        )}
                        onClick={() => onLoad(conv.id)}
                    >
                        <MessageSquare size={13} className="shrink-0" />
                        <span className="flex-1 truncate text-sm">{conv.title}</span>
                        <button
                            onClick={(e) => { e.stopPropagation(); onDelete(conv.id); }}
                            className="shrink-0 opacity-0 group-hover:opacity-100 p-0.5 rounded hover:text-red-400 transition-all cursor-pointer"
                            title="Delete"
                        >
                            <Trash2 size={12} />
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
