import { useChatStore } from "@/stores/chatStore";
import { Message, Citation } from "@/types";
import { ENDPOINTS } from "@/lib/api";

export function useChat() {
    const {
        domain,
        addMessage,
        updateLastAssistantMessage,
        appendToLastAssistantMessage,
        setLoading,
        setStreaming,
    } = useChatStore();

    const sendMessage = async (content: string) => {
        if (!content.trim()) return;

        addMessage({ id: crypto.randomUUID(), role: "user", content });
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
                const lines = chunk.split("\n");

                for (const line of lines) {
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
                            appendToLastAssistantMessage(
                                "\n\n_Error: " + parsed.error + "_"
                            );
                        }
                    } catch {
                        // incomplete JSON chunk — skip
                    }
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

    return { sendMessage };
}