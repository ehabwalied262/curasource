import { create } from "zustand";
import { Message, Domain, Citation } from "@/types";

interface ChatState {
  messages: Message[];
  domain: Domain;
  isLoading: boolean;
  isStreaming: boolean;
  activeCitation: Citation | null;
  sidebarOpen: boolean;

  // Actions
  setDomain: (domain: Domain) => void;
  addMessage: (message: Message) => void;
  updateLastAssistantMessage: (content: string, citations?: Citation[]) => void;
  appendToLastAssistantMessage: (token: string) => void;
  setLoading: (loading: boolean) => void;
  setStreaming: (streaming: boolean) => void;
  clearChat: () => void;
  setActiveCitation: (citation: Citation | null) => void;
  toggleSidebar: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  domain: "medical",
  isLoading: false,
  isStreaming: false,
  activeCitation: null,
  sidebarOpen: true,

  setDomain: (domain) => set({ domain }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateLastAssistantMessage: (content, citations) =>
    set((state) => {
      const newMessages = [...state.messages];
      const lastIndex = newMessages.findLastIndex((m) => m.role === "assistant");
      if (lastIndex !== -1) {
        newMessages[lastIndex] = { ...newMessages[lastIndex], content, citations };
      }
      return { messages: newMessages };
    }),

  appendToLastAssistantMessage: (token) =>
    set((state) => {
      const newMessages = [...state.messages];
      const lastIndex = newMessages.findLastIndex((m) => m.role === "assistant");
      if (lastIndex !== -1) {
        const prev = newMessages[lastIndex];
        newMessages[lastIndex] = {
          ...prev,
          content: (prev.content === "" ? "" : prev.content) + token,
        };
      }
      return { messages: newMessages };
    }),

  setLoading: (isLoading) => set({ isLoading }),
  setStreaming: (isStreaming) => set({ isStreaming }),

  clearChat: () => set({ messages: [] }),
  setActiveCitation: (citation) => set({ activeCitation: citation }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));