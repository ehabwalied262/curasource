"use client";

import { useChatStore } from "@/stores/chatStore";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
    const sidebarOpen = useChatStore((s) => s.sidebarOpen);

    return (
        <div className="flex h-screen w-full bg-[#212121]">
            {/* Desktop sidebar — slides in/out */}
            <div className={`hidden md:flex h-full transition-all duration-300 ${sidebarOpen ? "w-[260px]" : "w-0 overflow-hidden"}`}>
                <Sidebar />
            </div>

            <main className="flex-1 relative overflow-hidden">
                {children}
            </main>
        </div>
    );
}
