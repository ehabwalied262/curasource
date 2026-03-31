/**
 * Resolves the backend API URL. 
 * Falls back to localhost for resilient local development if the .env is missing.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export const ENDPOINTS = {
    chat: `${API_BASE_URL}/chat`,
    chatStream: `${API_BASE_URL}/chat/stream`,
    sources: `${API_BASE_URL}/sources`,
    feedback: `${API_BASE_URL}/feedback`,
} as const;