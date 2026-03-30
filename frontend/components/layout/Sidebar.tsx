"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Plus,
    MessageSquare,
    Library,
    Settings,
    UserCircle,
    HeartPulse
} from "lucide-react";

// Mock history based on your UI_UX.md
const RECENT_SESSIONS = [
    { id: "1", title: "What is STEMI?" },
    { id: "2", title: "Progressive overload" },
    { id: "3", title: "Metformin in CKD" },
];

export function Sidebar() {
    const pathname = usePathname();

    // Helper to check if a link is active
    const isActive = (path: string) => pathname === path || pathname.startsWith(`${path}/`);

    return (
        <aside className="w-[280px] h-screen bg-[#FAFAF9] border-r border-stone-200 flex flex-col flex-shrink-0 z-20">
            {/* Brand Header */}
            <div className="h-16 flex items-center px-6 border-b border-stone-200">
                <Link href="/" className="flex items-center gap-2 text-[#0D1B2A] hover:opacity-80 transition-opacity">
                    <HeartPulse className="text-[#0D1B2A]" size={24} strokeWidth={2.5} />
                    <span className="font-display font-bold text-xl tracking-tight">CuraSource</span>
                </Link>
            </div>

            {/* Primary Action */}
            <div className="p-4">
                <Button
                    className="w-full justify-start gap-2 bg-white text-[#0D1B2A] border border-stone-200 hover:bg-stone-50 hover:text-[#0D1B2A] shadow-sm"
                    variant="outline"
                >
                    <Plus size={16} />
                    New Chat
                </Button>
            </div>

            {/* Recent Sessions List */}
            <div className="flex-1 overflow-y-auto px-3 py-2">
                <h3 className="px-3 text-xs font-bold text-stone-400 uppercase tracking-wider mb-2">
                    Recent Sessions
                </h3>
                <div className="space-y-1">
                    {RECENT_SESSIONS.map((session) => (
                        <Link
                            key={session.id}
                            href={`/chat/${session.id}`}
                            className="flex items-center gap-3 px-3 py-2 text-sm font-body text-stone-600 rounded-lg hover:bg-stone-100 transition-colors group"
                        >
                            <MessageSquare size={14} className="text-stone-400 group-hover:text-stone-600" />
                            <span className="truncate">{session.title}</span>
                        </Link>
                    ))}
                </div>
            </div>

            {/* Bottom Navigation */}
            <div className="p-3 border-t border-stone-200 space-y-1 bg-white">
                <Link
                    href="/sources"
                    className={cn(
                        "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors",
                        isActive("/sources")
                            ? "bg-[#0D1B2A] text-white"
                            : "text-stone-600 hover:bg-stone-100"
                    )}
                >
                    <Library size={16} />
                    Corpus Browser
                </Link>
                <Link
                    href="/settings"
                    className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-stone-600 rounded-lg hover:bg-stone-100 transition-colors"
                >
                    <Settings size={16} />
                    Settings
                </Link>
                <Link
                    href="/account"
                    className="flex items-center gap-3 px-3 py-2 text-sm font-medium text-stone-600 rounded-lg hover:bg-stone-100 transition-colors"
                >
                    <UserCircle size={16} />
                    User Account
                </Link>
            </div>
        </aside>
    );
}