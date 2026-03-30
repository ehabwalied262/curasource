"use client";

import { useState } from "react";
import { CorpusSource, Domain } from "@/types";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Search,
    HeartPulse,
    Dumbbell,
    Apple,
    BookOpen,
    Database,
    ArrowRight
} from "lucide-react";

// Mock data based on your architecture requirements
const MOCK_CORPUS: CorpusSource[] = [
    {
        id: "src_001",
        source_file: "harrisons_21st.pdf",
        title: "Harrison's Principles of Internal Medicine",
        domain: "medical",
        edition: "21st Edition",
        publication_year: 2022,
        authors: "Loscalzo, Fauci, Kasper, Hauser, Longo, Jameson",
        total_chunks: 40234,
    },
    {
        id: "src_002",
        source_file: "davidsons_24th.pdf",
        title: "Davidson's Principles and Practice of Medicine",
        domain: "medical",
        edition: "24th Edition",
        publication_year: 2022,
        authors: "Penman, Ralston, Strachan, Hobson",
        total_chunks: 28150,
    },
    {
        id: "src_003",
        source_file: "acsm_guidelines_11th.pdf",
        title: "ACSM's Guidelines for Exercise Testing and Prescription",
        domain: "fitness",
        edition: "11th Edition",
        publication_year: 2021,
        authors: "American College of Sports Medicine",
        total_chunks: 12400,
    },
    {
        id: "src_004",
        source_file: "nsca_essentials_4th.pdf",
        title: "Essentials of Strength Training and Conditioning",
        domain: "fitness",
        edition: "4th Edition",
        publication_year: 2015,
        authors: "National Strength and Conditioning Association",
        total_chunks: 15890,
    },
];

export default function CorpusBrowserPage() {
    const [searchQuery, setSearchQuery] = useState("");
    const [activeTab, setActiveTab] = useState<Domain | "all">("all");

    const filteredCorpus = MOCK_CORPUS.filter((source) => {
        const matchesSearch = source.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            source.authors.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesDomain = activeTab === "all" || source.domain === activeTab;
        return matchesSearch && matchesDomain;
    });

    return (
        <div className="min-h-screen bg-[#FAFAF9] p-6 md:p-12">
            <div className="max-w-6xl mx-auto space-y-8">

                {/* Header Section */}
                <div className="space-y-4">
                    <h1 className="font-display text-4xl font-semibold text-[#0D1B2A]">
                        Corpus Browser
                    </h1>
                    <p className="text-stone-500 max-w-2xl font-body text-lg">
                        Explore the verified medical and fitness literature powering CuraSource.
                        Every AI response is strictly grounded in these indexed volumes.
                    </p>
                </div>

                {/* Controls Section */}
                <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white p-2 rounded-2xl border border-stone-200 shadow-sm">
                    <Tabs
                        defaultValue="all"
                        className="w-full md:w-auto"
                        onValueChange={(v) => setActiveTab(v as Domain | "all")}
                    >
                        <TabsList className="bg-stone-50 p-1">
                            <TabsTrigger value="all" className="rounded-xl data-[state=active]:bg-white data-[state=active]:shadow-sm">All Sources</TabsTrigger>
                            <TabsTrigger value="medical" className="rounded-xl data-[state=active]:bg-white data-[state=active]:shadow-sm"><HeartPulse size={14} className="mr-2" /> Medical</TabsTrigger>
                            <TabsTrigger value="fitness" className="rounded-xl data-[state=active]:bg-white data-[state=active]:shadow-sm"><Dumbbell size={14} className="mr-2" /> Fitness</TabsTrigger>
                            <TabsTrigger value="nutrition" className="rounded-xl data-[state=active]:bg-white data-[state=active]:shadow-sm"><Apple size={14} className="mr-2" /> Nutrition</TabsTrigger>
                        </TabsList>
                    </Tabs>

                    <div className="relative w-full md:w-96">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" size={18} />
                        <Input
                            placeholder="Search by title or author..."
                            className="pl-10 rounded-xl border-stone-200 bg-stone-50 focus-visible:ring-stone-400"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                {/* Grid Section */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredCorpus.map((source) => (
                        <CorpusCard key={source.id} source={source} />
                    ))}
                    {filteredCorpus.length === 0 && (
                        <div className="col-span-full py-12 text-center text-stone-500">
                            No sources found matching your criteria.
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
}

// CorpusCard Component
function CorpusCard({ source }: { source: CorpusSource }) {
    const isMedical = source.domain === "medical";

    return (
        <div className="group flex flex-col bg-white rounded-2xl border border-stone-200 p-6 hover:shadow-md hover:border-stone-300 transition-all duration-200">

            {/* Domain Badge */}
            <div className="mb-4 flex items-center justify-between">
                <Badge
                    variant="secondary"
                    className={`uppercase tracking-wider text-[10px] font-bold ${isMedical
                            ? "bg-blue-50 text-blue-700 hover:bg-blue-50"
                            : "bg-emerald-50 text-emerald-700 hover:bg-emerald-50"
                        }`}
                >
                    {isMedical ? (
                        <><HeartPulse size={12} className="mr-1.5" /> Medical</>
                    ) : (
                        <><Dumbbell size={12} className="mr-1.5" /> Fitness</>
                    )}
                </Badge>
                <BookOpen size={16} className="text-stone-300 group-hover:text-stone-400 transition-colors" />
            </div>

            {/* Title & Author */}
            <div className="flex-1">
                <h3 className="font-display text-xl font-semibold text-[#0D1B2A] leading-tight mb-2 line-clamp-3">
                    {source.title}
                </h3>
                <p className="text-sm font-body text-stone-500 line-clamp-2">
                    {source.authors}
                </p>
            </div>

            {/* Metadata & Action */}
            <div className="mt-6 pt-6 border-t border-stone-100 space-y-4">
                <div className="flex items-center justify-between text-xs text-stone-500 font-medium">
                    <span>{source.edition} · {source.publication_year}</span>
                    <span className="flex items-center gap-1.5">
                        <Database size={12} />
                        {source.total_chunks.toLocaleString()} chunks
                    </span>
                </div>

                <Button
                    variant="ghost"
                    className="w-full justify-between text-[#0D1B2A] hover:bg-stone-50 hover:text-[#0D1B2A]"
                >
                    Browse Source <ArrowRight size={16} className="ml-2 opacity-50 group-hover:opacity-100 transition-opacity" />
                </Button>
            </div>
        </div>
    );
}