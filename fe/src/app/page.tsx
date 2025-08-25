"use client";

import type React from "react";
import './globals.css';
import { useState, useRef, useEffect } from "react";
import { Send, Dumbbell, Zap } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function FitnessChatbot() {
  <div className="bg-red-500">Test CSS</div>
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
      // Placeholder for your FastAPI endpoint
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: input }),
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handlePromptClick = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <div className="flex flex-col h-screen bg-background font-sans text-foreground">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border bg-card shadow-sm">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground">
          <Dumbbell className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h1 className="font-bold text-lg text-foreground">FitBot</h1>
          <p className="text-sm text-muted-foreground">Personal Fitness Assistant</p>
        </div>
        <div className="ml-auto">
          <Zap className="w-5 h-5 text-accent animate-pulse" />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex gap-3 ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {message.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <span className="text-primary-foreground text-xs font-bold">FB</span>
              </div>
            )}

            <div
              className={`max-w-[80%] p-3 rounded-lg shadow-sm ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground ml-auto rounded-br-none"
                  : "bg-card text-card-foreground rounded-bl-none"
              }`}
            >
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
              <p
                className={`text-xs mt-2 opacity-70 ${
                  message.role === "user"
                    ? "text-primary-foreground"
                    : "text-muted-foreground"
                }`}
              >
                {message.timestamp.toLocaleTimeString("id-ID", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>

            {message.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center">
                <span className="text-accent-foreground text-xs font-bold">YOU</span>
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <span className="text-primary-foreground text-xs font-bold">FB</span>
            </div>
            <div className="bg-card text-card-foreground p-3 rounded-lg rounded-bl-none max-w-[80%]">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-primary rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-primary rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                </div>
                <span className="text-sm text-muted-foreground">FitBot sedang mengetik...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border bg-card">
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-2 mb-3 max-w-4xl mx-auto">
          <button
            onClick={() => handlePromptClick("Buatkan program workout untuk pemula")}
            className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium transition-colors rounded-full border border-input bg-background hover:bg-accent hover:text-accent-foreground"
            disabled={isLoading}
          >
            💪 Program Workout
          </button>
          <button
            onClick={() => handlePromptClick("Tips diet sehat untuk menurunkan berat badan")}
            className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium transition-colors rounded-full border border-input bg-background hover:bg-accent hover:text-accent-foreground"
            disabled={isLoading}
          >
            🥗 Tips Diet
          </button>
          <button
            onClick={() => handlePromptClick("Bagaimana cara membangun otot dengan efektif?")}
            className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-medium transition-colors rounded-full border border-input bg-background hover:bg-accent hover:text-accent-foreground"
            disabled={isLoading}
          >
            🏋️ Build Muscle
          </button>
        </div>
        <div className="flex gap-2 max-w-4xl mx-auto">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Tanya tentang workout, nutrisi, atau tips fitness..."
            className="flex-1 min-h-[48px] p-3 rounded-full border border-input bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            className="inline-flex items-center justify-center rounded-full p-3 transition-colors bg-primary text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
