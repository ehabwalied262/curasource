import { useChatStore } from "@/stores/chatStore";
import { Message, Citation } from "@/types";
import { ENDPOINTS } from "@/lib/api";
import { useRef } from "react";

/** Drains a token queue at a smooth, readable pace */
function createTokenBuffer(onToken: (t: string) => void) {
    const queue: string[] = [];
    let draining = false;
    let done = false;

    const TOKEN_DELAY = 30; // ms between tokens — smooth & readable

    async function drain() {
        if (draining) return;
        draining = true;

        while (queue.length > 0) {
            const token = queue.shift()!;
            onToken(token);
            // Adaptive: tiny pause per token, slightly longer after punctuation
            const pause = /[.!?,:;]\s*$/.test(token) ? TOKEN_DELAY * 2.5 : TOKEN_DELAY;
            await new Promise((r) => setTimeout(r, pause));
        }

        draining = false;

        // If stream ended but queue was still draining, we're now fully done
        if (done && queue.length === 0) {
            flushResolve?.();
        }
    }

    let flushResolve: (() => void) | null = null;

    return {
        push(token: string) {
            queue.push(token);
            drain();
        },
        /** Signal that no more tokens will arrive; returns a promise that resolves when queue is empty */
        finish(): Promise<void> {
            done = true;
            if (queue.length === 0 && !draining) return Promise.resolve();
            return new Promise((resolve) => {
                flushResolve = resolve;
                drain(); // kick drain in case it stopped
            });
        },
    };
}

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

    const abortControllerRef = useRef<AbortController | null>(null);

    const stopStreaming = () => {
        abortControllerRef.current?.abort();
    };

    /** Core stream logic — shared by send, retry, and edit */
    const streamResponse = async (content: string) => {
        abortControllerRef.current = new AbortController();
        addMessage({ id: crypto.randomUUID(), role: "assistant", content: "" });
        setLoading(true);
        setStreaming(true);

        let pendingCitations: Citation[] | null = null;

        const buffer = createTokenBuffer((token) => {
            appendToLastAssistantMessage(token);
        });

        try {
            // Send last 10 messages as history (excluding the empty placeholder we just added)
            const allMessages = useChatStore.getState().messages;
            const history = allMessages
                .slice(0, -1)   // exclude the empty assistant placeholder
                .slice(-10)     // keep last 10 messages max
                .map((m: Message) => ({ role: m.role, content: m.content }));

            const response = await fetch(ENDPOINTS.chatStream, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: content, domain, history }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok || !response.body) {
                throw new Error(`Backend returned status ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            // Accumulate raw bytes across TCP chunks so large SSE events
            // (e.g. the final done+citations payload) are never split mid-JSON.
            let sseBuffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                sseBuffer += decoder.decode(value, { stream: true });

                // SSE events are separated by \n\n — only process complete events
                const events = sseBuffer.split("\n\n");
                sseBuffer = events.pop() ?? ""; // keep any trailing incomplete event

                for (const event of events) {
                    for (const line of event.split("\n")) {
                        if (!line.startsWith("data: ")) continue;
                        try {
                            const parsed = JSON.parse(line.slice(6));
                            if (parsed.token) {
                                buffer.push(parsed.token);
                            }
                            if (parsed.done && parsed.citations) {
                                pendingCitations = parsed.citations as Citation[];
                            }
                            if (parsed.error) {
                                buffer.push("\n\n_Error: " + parsed.error + "_");
                            }
                        } catch { /* malformed JSON */ }
                    }
                }
            }

            // Wait for all buffered tokens to finish rendering
            await buffer.finish();

            // Now apply citations
            if (pendingCitations) {
                updateLastAssistantMessage(
                    useChatStore.getState().messages.findLast(
                        (m: Message) => m.role === "assistant"
                    )?.content ?? "",
                    pendingCitations
                );
            }
        } catch (error: any) {
            if (error?.name === "AbortError") {
                // User stopped the stream — keep whatever was already rendered
                return;
            }
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

        const userMsg = state.messages.slice(0, idx).findLast((m) => m.role === "user");
        if (!userMsg) return;

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

    return { sendMessage, retryMessage, editAndResend, stopStreaming };
}
