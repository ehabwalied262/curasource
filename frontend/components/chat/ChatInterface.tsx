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
import { SendHorizontal, HeartPulse, Dumbbell, Apple, Menu } from 'lucide-react';

export function ChatInterface() {
    const [input, setInput] = useState("");
    const { messages, domain, setDomain, isLoading } = useChatStore();
    const { sendMessage } = useChat();
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    // The fixed send logic
    const handleSend = async () => {
        if (!input.trim() || isLoading) return;
        const currentInput = input;
        setInput(""); // Clear immediately for snappy UI
        await sendMessage(currentInput);
    };

    // Allow sending with the Enter key
    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full bg-[#FAFAF9]">
            {/* Header */}
            <header className="h-16 border-b border-stone-200 bg-white/80 backdrop-blur-md flex items-center justify-between px-4 md:px-6 sticky top-0 z-10">
                <div className="flex items-center gap-3">
                    {/* Mobile Menu Trigger */}
                    <Sheet>
                        <SheetTrigger asChild>
                            <Button variant="ghost" size="icon" className="md:hidden -ml-2 text-stone-600">
                                <Menu size={20} />
                            </Button>
                        </SheetTrigger>
                        <SheetContent side="left" className="p-0 w-[280px]">
                            <Sidebar />
                        </SheetContent>
                    </Sheet>
                    <h1 className="font-display font-semibold text-lg text-[#0D1B2A] hidden sm:block">CuraSource</h1>
                </div>

                <div className="flex items-center gap-2">
                    <span className="hidden sm:inline-block text-xs font-bold text-stone-400 uppercase mr-2">Domain:</span>
                    <Select value={domain} onValueChange={(v: any) => setDomain(v)}>
                        <SelectTrigger className="w-[140px] sm:w-[160px] h-9 bg-stone-50 border-stone-200">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="medical"><div className="flex items-center gap-2"><HeartPulse size={14} /> Medical</div></SelectItem>
                            <SelectItem value="fitness"><div className="flex items-center gap-2"><Dumbbell size={14} /> Fitness</div></SelectItem>
                            <SelectItem value="nutrition"><div className="flex items-center gap-2"><Apple size={14} /> Nutrition</div></SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </header>

            {/* Messages Area */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth">
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center p-6 md:p-8">
                        <h2 className="font-display text-2xl md:text-3xl text-[#0D1B2A] mb-4">How can I assist your expertise today?</h2>
                        <p className="text-stone-500 text-sm md:text-base max-w-md">Select a domain above and ask a question grounded in medical and fitness literature.</p>
                    </div>
                ) : (
                    messages.map((m) => <ChatMessage key={m.id} message={m} />)
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 md:p-8 bg-gradient-to-t from-[#FAFAF9] via-[#FAFAF9] to-transparent">
                <div className="max-w-3xl mx-auto relative group">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={isLoading}
                        placeholder={`Ask a ${domain} question...`}
                        className="w-full h-12 md:h-14 pl-4 md:pl-6 pr-14 rounded-xl md:rounded-2xl border-stone-200 shadow-sm focus-visible:ring-stone-400 transition-all bg-white text-base"
                    />
                    <Button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="absolute right-1.5 top-1.5 md:right-2 md:top-2 h-9 w-9 md:h-10 md:w-10 rounded-lg md:rounded-xl bg-[#0D1B2A] hover:bg-[#1B2E45] disabled:opacity-50"
                    >
                        <SendHorizontal size={18} />
                    </Button>
                </div>
                <p className="text-[10px] text-center text-stone-400 mt-3 md:mt-4 uppercase tracking-[0.1em] md:tracking-[0.2em] px-4">
                    Grounded in Harrison's, Davidson's, and Clinical Fitness Journals
                </p>
            </div>

            {/* Global Modals/Drawers */}
            <SourcePanel />
        </div>
    );
}