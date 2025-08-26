"use client";
import { useState, useRef, useEffect } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
};

const quickActions = [
  {
    label: "💪 Program Workout",
    prompt: "Buatkan program workout untuk pemula",
  },
  {
    label: "🥗 Tips Diet",
    prompt: "Tips diet sehat untuk menurunkan berat badan",
  },
  {
    label: "🏋️ Build Muscle",
    prompt: "Bagaimana cara membangun otot dengan efektif?",
  },
];

export default function FitnessChatbot() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Halo! Saya FitBot, asisten fitness pribadi Anda! 💪 Siap untuk memulai perjalanan fitness yang luar biasa? Tanyakan apa saja tentang workout, nutrisi, atau tips kesehatan!",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userMessage.content }),
      });
      const data = await res.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: "Maaf, terjadi kesalahan. Silakan coba lagi dalam beberapa saat.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") sendMessage();
  };

  const handlePromptClick = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 bg-white border-b border-gray-200 shadow-sm">
        <div className="w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center">
          <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center">
            <div className="w-3 h-3 bg-gray-900 rounded-full"></div>
          </div>
        </div>
        <div>
          <div className="font-semibold text-lg text-gray-900">FitBot</div>
          <div className="text-sm text-gray-500">Your Personal Fitness Assistant</div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-3 ${
              msg.role === "user" ? "flex-row-reverse" : "flex-row"
            }`}
          >
            {/* Avatar */}
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-gray-900 flex items-center justify-center">
                {msg.role === "assistant" ? (
                  <div className="w-5 h-5 rounded-full bg-white flex items-center justify-center">
                    <div className="w-2.5 h-2.5 bg-gray-900 rounded-full"></div>
                  </div>
                ) : (
                  <div className="w-5 h-5 rounded-full bg-gray-600"></div>
                )}
              </div>
            </div>

            {/* Message Bubble */}
            <div
              className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl text-sm ${
                msg.role === "user"
                  ? "bg-teal-400 text-gray-900 rounded-br-md"
                  : "bg-white text-gray-900 rounded-bl-md shadow-sm border border-gray-100"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Loading bubble */}
        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-gray-900 flex items-center justify-center">
                <div className="w-5 h-5 rounded-full bg-white flex items-center justify-center">
                  <div className="w-2.5 h-2.5 bg-gray-900 rounded-full"></div>
                </div>
              </div>
            </div>
            <div className="max-w-xs lg:max-w-md px-4 py-3 rounded-2xl rounded-bl-md bg-white shadow-sm border border-gray-100">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce"></div>
                  <div 
                    className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" 
                    style={{ animationDelay: "0.15s" }}
                  ></div>
                  <div 
                    className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" 
                    style={{ animationDelay: "0.3s" }}
                  ></div>
                </div>
                <span className="text-sm text-gray-500">FitBot sedang mengetik...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area + Quick Actions */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-2 mb-4">
          {quickActions.map((act, idx) => (
            <button
              key={idx}
              onClick={() => handlePromptClick(act.prompt)}
              className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-full border border-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isLoading}
            >
              {act.label}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="flex items-center gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Tanyakan sesuatu..."
            className="flex-1 px-4 py-3 bg-gray-100 border border-gray-200 rounded-full text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="p-3 bg-teal-400 hover:bg-teal-500 text-white rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Kirim"
          >
            <svg 
              width="20" 
              height="20" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              viewBox="0 0 24 24"
            >
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}