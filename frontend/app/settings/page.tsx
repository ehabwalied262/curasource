"use client";

import { HeartPulse, Database, Cpu, Shield, Info } from "lucide-react";

function Section({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
    return (
        <div className="border border-white/10 rounded-xl overflow-hidden">
            <div className="flex items-center gap-2.5 px-5 py-4 border-b border-white/10 bg-white/[0.03]">
                <Icon size={15} className="text-emerald-400" />
                <h2 className="text-sm font-semibold text-stone-200">{title}</h2>
            </div>
            <div className="divide-y divide-white/10">{children}</div>
        </div>
    );
}

function Row({ label, value, note }: { label: string; value: string; note?: string }) {
    return (
        <div className="flex items-center justify-between px-5 py-3.5">
            <div>
                <p className="text-sm text-stone-300">{label}</p>
                {note && <p className="text-xs text-stone-600 mt-0.5">{note}</p>}
            </div>
            <span className="text-xs font-mono bg-white/5 border border-white/10 text-stone-400 px-2.5 py-1 rounded-md">
                {value}
            </span>
        </div>
    );
}

export default function SettingsPage() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

    return (
        <div className="h-full overflow-y-auto bg-[#212121]">
            <div className="max-w-2xl mx-auto px-5 py-10">

                {/* Page title */}
                <div className="mb-8">
                    <h1 className="font-display text-2xl text-stone-100 mb-1">Settings</h1>
                    <p className="text-sm text-stone-500">Application configuration and system information.</p>
                </div>

                <div className="flex flex-col gap-4">

                    {/* Appearance */}
                    <Section title="Appearance" icon={Info}>
                        <Row label="Theme" value="Dark" note="Default dark mode, matches Claude UI" />
                        <Row label="Font" value="DM Sans + Fraunces" />
                    </Section>

                    {/* Models */}
                    <Section title="AI Models" icon={Cpu}>
                        <Row
                            label="Language Model"
                            value="Llama 3 8B"
                            note="meta-llama/Meta-Llama-3-8B-Instruct via HF Inference API"
                        />
                        <Row
                            label="Embedding Model"
                            value="BGE-Large EN v1.5"
                            note="BAAI/bge-large-en-v1.5 · 1024 dimensions · via HF Inference API"
                        />
                        <Row label="Max Response Tokens" value="500" />
                    </Section>

                    {/* Database */}
                    <Section title="Vector Database" icon={Database}>
                        <Row
                            label="Provider"
                            value="Qdrant Cloud"
                            note="Frankfurt, EU Central (GCP)"
                        />
                        <Row label="Collection" value="curasource_chunks" />
                        <Row label="Vector Size" value="1024 dims" />
                        <Row label="Distance Metric" value="Cosine" />
                    </Section>

                    {/* API */}
                    <Section title="Backend API" icon={HeartPulse}>
                        <Row
                            label="Endpoint"
                            value={backendUrl.replace("https://", "").replace("http://", "")}
                            note="Set via NEXT_PUBLIC_API_URL environment variable"
                        />
                        <Row label="Framework" value="FastAPI + Uvicorn" />
                        <Row label="Hosted on" value="HF Spaces" />
                    </Section>

                    {/* Privacy */}
                    <Section title="Privacy & Data" icon={Shield}>
                        <Row
                            label="Chat History"
                            value="Local only"
                            note="Sessions are stored in browser memory and cleared on refresh"
                        />
                        <Row
                            label="Sources"
                            value="Read only"
                            note="Medical and fitness textbooks ingested locally, never modified"
                        />
                    </Section>

                </div>

                <p className="text-center text-xs text-stone-700 mt-8">
                    CuraSource — Medical & Fitness RAG Assistant
                </p>
            </div>
        </div>
    );
}
