import { useChatStore } from "@/stores/chatStore";
import { Message, Citation } from "@/types";
import { ENDPOINTS } from "@/lib/api";

export function useChat() {
    const {
        domain,
        messages,
        addMessage,
        updateLastAssistantMessage,
        appendToLastAssistantMessage,
        deleteFromMessage,
        setLoading,
        setStreaming,
    } = useChatStore();

    /** Core stream logic — shared by send, retry, and edit */
    const streamResponse = async (content: string) => {
        addMessage({ id: crypto.randomUUID(), role: "assistant", content: "" });
        setLoading(true);
        setStreaming(true);

        try {
            const response = await fetch(ENDPOINTS.chatStream, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: content, domain }),
            });

            if (!response.ok || !response.body) {
                throw new Error(`Backend returned status ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                for (const line of chunk.split("\n")) {
                    if (!line.startsWith("data: ")) continue;
                    try {
                        const parsed = JSON.parse(line.slice(6));
                        if (parsed.token) {
                            appendToLastAssistantMessage(parsed.token);
                        }
                        if (parsed.done && parsed.citations) {
                            updateLastAssistantMessage(
                                useChatStore.getState().messages.findLast(
                                    (m: Message) => m.role === "assistant"
                                )?.content ?? "",
                                parsed.citations as Citation[]
                            );
                        }
                        if (parsed.error) {
                            appendToLastAssistantMessage("\n\n_Error: " + parsed.error + "_");
                        }
                    } catch { /* incomplete JSON chunk */ }
                }
            }
        } catch (error) {
            console.error("CuraSource stream error:", error);
            updateLastAssistantMessage(
                "I'm sorry, I encountered an error connecting to the medical database. Please ensure the backend is running."
            );
        } finally {
            setLoading(false);
            setStreaming(false);
        }
    };

    const sendMessage = async (content: string) => {
        if (!content.trim()) return;
        addMessage({ id: crypto.randomUUID(), role: "user", content });
        await streamResponse(content);
    };

    /** Retry: called from the retry button on an assistant message */
    const retryMessage = async (assistantMessageId: string) => {
        const state = useChatStore.getState();
        const idx = state.messages.findIndex((m) => m.id === assistantMessageId);
        if (idx === -1) return;

        // Find the user message right before this assistant message
        const userMsg = state.messages.slice(0, idx).findLast((m) => m.role === "user");
        if (!userMsg) return;

        // Delete the assistant message (and anything after) then re-stream
        deleteFromMessage(assistantMessageId);
        await streamResponse(userMsg.content);
    };

    /** Edit: replace a user message and re-stream */
    const editAndResend = async (userMessageId: string, newContent: string) => {
        if (!newContent.trim()) return;
        deleteFromMessage(userMessageId);
        addMessage({ id: crypto.randomUUID(), role: "user", content: newContent });
        await streamResponse(newContent);
    };

    return { sendMessage, retryMessage, editAndResend };
}
