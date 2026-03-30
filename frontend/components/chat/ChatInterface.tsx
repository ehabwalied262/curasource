"use client";

import { useState, useEffect, useRef } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useChat } from '@/hooks/useChat';
import { ChatMessage } from './ChatMessage';
import { SourcePanel } from '@/components/sources/SourcePanel';
import { Sidebar } from '@/components/layout/Sidebar';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { SendHorizontal, HeartPulse, Dumbbell, Apple, Menu, PanelLeftOpen } from 'lucide-react';

export function ChatInterface() {
    const [input, setInput] = useState("");
    const { messages, domain, setDomain, isLoading, sidebarOpen, toggleSidebar } = useChatStore();
    const { sendMessage } = useChat();
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;
        const currentInput = input;
        setInput("");
        await sendMessage(currentInput);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full bg-[#212121]">

            {/* Header */}
            <header className="h-14 border-b border-white/10 bg-[#212121]/80 backdrop-blur-md flex items-center justify-between px-4 sticky top-0 z-10">
                <div className="flex items-center gap-2">

                    {/* Mobile menu */}
                    <Sheet>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon" className="md:hidden h-8 w-8 text-stone-400 hover:text-stone-100 hover:bg-white/10">
                                <Menu size={18} />
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="p-0 w-[260px] bg-[#171717] border-r border-white/10">
                            <Sidebar />
                        </SheetContent>
                    </Sheet>

                    {/* Desktop sidebar open button — only shown when sidebar is closed */}
                    {!sidebarOpen && (
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={toggleSidebar}
                            className="hidden md:flex h-8 w-8 text-stone-400 hover:text-stone-100 hover:bg-white/10"
                        >
                            <PanelLeftOpen size={18} />
                        </Button>
                    )}

                    <span className="font-display font-semibold text-stone-200 hidden sm:block">
                        CuraSource
                    </span>
                </div>

                {/* Domain selector */}
                <div className="flex items-center gap-2">
                    <span className="hidden sm:inline-block text-[10px] font-bold text-stone-500 uppercase tracking-widest mr-1">Domain</span>
                    <Select value={domain} onValueChange={(v: any) => setDomain(v)}>
                        <SelectTrigger className="w-[130px] h-8 bg-white/5 border-white/10 text-stone-300 text-sm">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#2a2a2a] border-white/10 text-stone-200">
                            <SelectItem value="medical"><div className="flex items-center gap-2"><HeartPulse size={13} /> Medical</div></SelectItem>
                            <SelectItem value="fitness"><div className="flex items-center gap-2"><Dumbbell size={13} /> Fitness</div></SelectItem>
                            <SelectItem value="nutrition"><div className="flex items-center gap-2"><Apple size={13} /> Nutrition</div></SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </header>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8">
                        <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center mb-6">
                            <HeartPulse className="text-emerald-400" size={24} />
                        </div>
                        <h2 className="font-display text-2xl md:text-3xl text-stone-100 mb-3">
                            How can I assist your expertise today?
                        </h2>
                        <p className="text-stone-500 text-sm max-w-md">
                            Select a domain above and ask a question grounded in medical and fitness literature.
                        </p>
                    </div>
                ) : (
                    messages.map((m) => <ChatMessage key={m.id} message={m} />)
                )}
            </div>

            {/* Input */}
            <div className="p-4 md:p-6 bg-gradient-to-t from-[#212121] via-[#212121]/90 to-transparent">
                <div className="max-w-3xl mx-auto relative">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        placeholder={`Ask a ${domain} question...`}
                        className="w-full h-12 md:h-14 pl-5 pr-14 rounded-xl border-white/10 bg-[#2a2a2a] text-stone-100 placeholder:text-stone-500 focus-visible:ring-emerald-500/50 text-base"
                    />
                    <Button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="absolute right-2 top-1.5 md:top-2 h-9 w-9 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                        <SendHorizontal size={16} />
                    </Button>
                </div>
                <p className="text-[10px] text-center text-stone-600 mt-3 uppercase tracking-widest">
                    Grounded in Harrison&apos;s, Davidson&apos;s, and Clinical Fitness Journals
                </p>
            </div>

            <SourcePanel />
        </div>
    );
}
