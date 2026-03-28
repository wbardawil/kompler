"use client";

import { useState, useRef, useEffect } from "react";
import { askQuestion } from "@/lib/api";
import { Send, Bot, User, Loader2, AlertCircle } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: any[];
  flags?: string[];
  loading?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I can answer questions about your uploaded documents. Ask me anything — for example:\n\n" +
        "- \"Which supplier certificates expire this quarter?\"\n" +
        "- \"What does SOP-042 say about temperature limits?\"\n" +
        "- \"Summarize all documents related to ISO 9001\"\n\n" +
        "Q&A is always free — no credits consumed.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    // Add loading message
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", loading: true },
    ]);

    try {
      const response = await askQuestion(question);
      setMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1
            ? {
                role: "assistant",
                content: response.answer,
                citations: response.citations,
                flags: response.flags,
                loading: false,
              }
            : m
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m, i) =>
          i === prev.length - 1
            ? {
                role: "assistant",
                content: "Sorry, I encountered an error. Please try again.",
                loading: false,
              }
            : m
        )
      );
    }

    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Ask Your Documents</h2>
      <p className="text-sm text-gray-500 mb-4">
        Free — 0 credits. Ask anything about your uploaded documents.
      </p>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
          >
            {msg.role === "assistant" && (
              <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center flex-shrink-0">
                <Bot size={16} className="text-brand-700" />
              </div>
            )}
            <div
              className={`max-w-[70%] rounded-xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-brand-600 text-white"
                  : "bg-white border border-gray-200"
              }`}
            >
              {msg.loading ? (
                <Loader2 size={16} className="animate-spin text-gray-400" />
              ) : (
                <>
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

                  {/* Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs font-medium text-gray-500 mb-1">Sources:</p>
                      {msg.citations.map((cite: any, j: number) => (
                        <p key={j} className="text-xs text-gray-500">
                          {cite.filename || cite.document_id}
                          {cite.relevant_text && (
                            <span className="italic"> — "{cite.relevant_text.slice(0, 100)}..."</span>
                          )}
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Flags */}
                  {msg.flags && msg.flags.length > 0 && (
                    <div className="mt-2 flex items-start gap-2">
                      <AlertCircle size={14} className="text-amber-500 mt-0.5" />
                      <div>
                        {msg.flags.map((flag: string, j: number) => (
                          <p key={j} className="text-xs text-amber-600">
                            {flag}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                <User size={16} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Ask a question about your documents..."
          className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={loading}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-brand-600 text-white px-4 py-3 rounded-xl hover:bg-brand-700 disabled:opacity-50 transition-colors"
        >
          <Send size={18} />
        </button>
      </div>

      <p className="text-xs text-gray-400 mt-2 text-center">
        AI-generated responses. Verify critical information against authoritative sources.
      </p>
    </div>
  );
}
