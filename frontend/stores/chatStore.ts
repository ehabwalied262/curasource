import { create } from "zustand";
import { Message, Domain, Citation } from "@/types";

interface ChatState {
  messages: Message[];
  domain: Domain;
  isLoading: boolean;
  activeCitation: Citation | null;

  // Actions
  setDomain: (domain: Domain) => void;
  addMessage: (message: Message) => void;
  updateLastAssistantMessage: (content: string, citations?: Citation[]) => void;
  setLoading: (loading: boolean) => void;
  clearChat: () => void;
  setActiveCitation: (citation: Citation | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  domain: "medical", // Defaulting to medical per ARCHITECTURE.md
  isLoading: false,
  activeCitation: null, // <-- initialize here

  setDomain: (domain) => set({ domain }),
  
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  
  updateLastAssistantMessage: (content, citations) =>
    set((state) => {
      const newMessages = [...state.messages];
      const lastIndex = newMessages.findLastIndex((m) => m.role === "assistant");

      if (lastIndex !== -1) {
        newMessages[lastIndex] = { 
          ...newMessages[lastIndex], 
          content, 
          citations
        };
      }
      return { messages: newMessages };
    }),

  setLoading: (isLoading) => set({ isLoading }),
  
  clearChat: () => set({ messages: [] }),

  setActiveCitation: (citation) => set({ activeCitation: citation }),
}));