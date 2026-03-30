import { useChatStore } from "@/stores/chatStore";
import { Message, Citation } from "@/types";
import { ENDPOINTS } from "@/lib/api";

/** Normalizes whatever the backend sends into a Citation[]. */
function normalizeCitations(data: Record<string, unknown>): Citation[] | undefined {
    // Preferred: backend already returns the rich citations array
    if (Array.isArray(data.citations) && data.citations.length > 0) {
        return data.citations as Citation[];
    }
    // Fallback: old sources_used format { file, page }
    if (Array.isArray(data.sources_used) && data.sources_used.length > 0) {
        return (data.sources_used as Array<{ file: string; page: number }>).map(
            (s, i): Citation => ({
                index: i + 1,
                source_title: s.file ?? "Unknown Source",
                edition: "",
                chapter: "",
                page_number: s.page ?? 0,
                excerpt: "",
                verification_status: "verified",
                verification_score: 0,
            })
        );
    }
    return undefined;
}

export function useChat() {
    const {
        domain,
        addMessage,
        updateLastAssistantMessage,
        setLoading
    } = useChatStore();

    const sendMessage = async (content: string) => {
        if (!content.trim()) return;

        const userMessage: Message = {
            id: crypto.randomUUID(),
            role: "user",
            content,
        };
        addMessage(userMessage);

        const assistantId = crypto.randomUUID();
        addMessage({
            id: assistantId,
            role: "assistant",
            content: "...",
        });

        setLoading(true);

        try {
            // Use the centralized environment-aware endpoint
            const response = await fetch(ENDPOINTS.chat, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: content,
                    domain: domain
                }),
            });

            if (!response.ok) throw new Error(`Backend returned status ${response.status}`);

            const data = await response.json();

            const responseData = data as Record<string, unknown>;
            updateLastAssistantMessage(
                (responseData.response_text as string) || (responseData.answer as string) || "",
                normalizeCitations(responseData)
            );

        } catch (error) {
            console.error("CuraSource API Error:", error);
            updateLastAssistantMessage(
                "I'm sorry, I encountered an error connecting to the medical database. Please ensure the backend is running and reachable."
            );
        } finally {
            setLoading(false);
        }
    };

    return { sendMessage };
}