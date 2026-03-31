import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Message, Domain, Citation } from "@/types";

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  domain: Domain;
  createdAt: number;
  updatedAt: number;
}

interface ChatState {
  // Active session
  messages: Message[];
  domain: Domain;
  activeConversationId: string;

  // History
  conversations: Conversation[];

  // UI state
  isLoading: boolean;
  isStreaming: boolean;
  activeCitation: Citation | null;
  sidebarOpen: boolean;

  // Conversation actions
  newChat: () => void;
  loadConversation: (id: string) => void;
  deleteConversation: (id: string) => void;

  // Message actions
  setDomain: (domain: Domain) => void;
  addMessage: (message: Message) => void;
  updateLastAssistantMessage: (content: string, citations?: Citation[]) => void;
  appendToLastAssistantMessage: (token: string) => void;
  deleteFromMessage: (messageId: string) => void;

  // UI actions
  setLoading: (loading: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  clearChat: () => void;
  setActiveCitation: (citation: Citation | null) => void;
  toggleSidebar: () => void;
}

function generateId() {
  return crypto.randomUUID();
}

function titleFromMessages(messages: Message[]): string {
  const first = messages.find((m) => m.role === "user");
  if (!first) return "New conversation";
  return first.content.slice(0, 52) + (first.content.length > 52 ? "…" : "");
}

/** Sync current messages back into the conversations list */
function syncToHistory(
  conversations: Conversation[],
  id: string,
  messages: Message[],
  domain: Domain
): Conversation[] {
  if (messages.length === 0) return conversations;
  const existing = conversations.find((c) => c.id === id);
  const updated: Conversation = {
    id,
    title: titleFromMessages(messages),
    messages,
    domain,
    createdAt: existing?.createdAt ?? Date.now(),
    updatedAt: Date.now(),
  };
  const rest = conversations.filter((c) => c.id !== id);
  return [updated, ...rest];
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      domain: "medical",
      activeConversationId: generateId(),
      conversations: [],
      isLoading: false,
      isStreaming: false,
      activeCitation: null,
      sidebarOpen: true,

      // ── Conversation management ──────────────────────────

      newChat: () =>
        set((state) => {
          const synced = syncToHistory(
            state.conversations,
            state.activeConversationId,
            state.messages,
            state.domain
          );
          return {
            conversations: synced,
            messages: [],
            activeConversationId: generateId(),
            domain: state.domain,
            activeCitation: null,
          };
        }),

      loadConversation: (id) =>
        set((state) => {
          const synced = syncToHistory(
            state.conversations,
            state.activeConversationId,
            state.messages,
            state.domain
          );
          const target = synced.find((c) => c.id === id);
          if (!target) return { conversations: synced };
          return {
            conversations: synced,
            messages: target.messages,
            domain: target.domain,
            activeConversationId: id,
            activeCitation: null,
          };
        }),

      deleteConversation: (id) =>
        set((state) => {
          const remaining = state.conversations.filter((c) => c.id !== id);
          if (id !== state.activeConversationId) {
            return { conversations: remaining };
          }
          // If deleting active, switch to most recent or start fresh
          const next = remaining[0];
          return {
            conversations: remaining,
            messages: next?.messages ?? [],
            domain: next?.domain ?? state.domain,
            activeConversationId: next?.id ?? generateId(),
            activeCitation: null,
          };
        }),

      // ── Message actions ───────────────────────────────────

      setDomain: (domain) => set({ domain }),

      addMessage: (message) =>
        set((state) => {
          const messages = [...state.messages, message];
          return {
            messages,
            conversations: syncToHistory(
              state.conversations,
              state.activeConversationId,
              messages,
              state.domain
            ),
          };
        }),

      updateLastAssistantMessage: (content, citations) =>
        set((state) => {
          const newMessages = [...state.messages];
          const lastIndex = newMessages.findLastIndex((m) => m.role === "assistant");
          if (lastIndex !== -1) {
            newMessages[lastIndex] = { ...newMessages[lastIndex], content, citations };
          }
          return {
            messages: newMessages,
            conversations: syncToHistory(
              state.conversations,
              state.activeConversationId,
              newMessages,
              state.domain
            ),
          };
        }),

      appendToLastAssistantMessage: (token) =>
        set((state) => {
          const newMessages = [...state.messages];
          const lastIndex = newMessages.findLastIndex((m) => m.role === "assistant");
          if (lastIndex !== -1) {
            const prev = newMessages[lastIndex];
            newMessages[lastIndex] = { ...prev, content: prev.content + token };
          }
          return { messages: newMessages };
        }),

      deleteFromMessage: (messageId) =>
        set((state) => {
          const idx = state.messages.findIndex((m) => m.id === messageId);
          if (idx === -1) return state;
          const messages = state.messages.slice(0, idx);
          return {
            messages,
            conversations: syncToHistory(
              state.conversations,
              state.activeConversationId,
              messages,
              state.domain
            ),
          };
        }),

      // ── UI actions ────────────────────────────────────────

      setLoading: (isLoading) => set({ isLoading }),
      setStreaming: (isStreaming) => set({ isStreaming }),
      clearChat: () => get().newChat(),
      setActiveCitation: (citation) => set({ activeCitation: citation }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
    }),
    {
      name: "curasource-chat",
      // Don't persist transient UI state
      partialize: (state) => ({
        messages: state.messages,
        domain: state.domain,
        activeConversationId: state.activeConversationId,
        conversations: state.conversations,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
);
