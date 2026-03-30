// types/index.ts
export type Role = "user" | "assistant";
export type Domain = "medical" | "fitness" | "nutrition";
export type VerificationStatus = "verified" | "low_confidence" | "failed";

export interface Citation {
    index: number;
    source_title: string;
    edition: string;
    chapter: string;
    page_number: number;
    excerpt: string;
    verification_status: VerificationStatus;
    verification_score: number;
}

export interface Message {
    id: string;
    role: Role;
    content: string;
    citations?: Citation[]; // Assistant only
}

export interface CorpusSource {
    id: string;
    source_file: string;
    title: string;
    domain: Domain;
    edition: string;
    publication_year: number;
    authors: string;
    total_chunks: number;
}