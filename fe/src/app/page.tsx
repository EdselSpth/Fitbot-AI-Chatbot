"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import ReactMarkdown from "react-markdown" // <-- 1. Import library yang dibutuhkan

interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

const quickActions = [
  {
    label: "💪 Program Workout",
    prompt: "Buatkan program workout untuk pemula",
  },
  {
    label: "🥗 Nutrisi Sehat",
    prompt: "Bagaimana nutrisi sehat dasar untuk permulaan fitness?",
  },
  {
    label: "🏋️ Build Muscle",
    prompt: "Bagaimana cara membangun otot dengan efektif?",
  },
]

export default function FitnessChatbot() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Halo! Saya FitBot, asisten fitness pribadi Anda! 💪 Siap untuk memulai perjalanan fitness yang luar biasa? Tanyakan apa saja tentang workout, nutrisi, atau tips kesehatan!",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  // 2. Fungsi sendMessage diubah sedikit untuk menerima prompt langsung
  const sendMessage = async (messageContent?: string) => {
    const contentToSend = messageContent || input
    if (!contentToSend.trim() || isLoading) return

    const userMessage: Message = {
      role: "user",
      content: contentToSend,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userMessage.content }),
      })
      const data = await res.json()

      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: "Maaf, terjadi kesalahan. Silakan coba lagi dalam beberapa saat.",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handlePromptClick = (prompt: string) => {
    // Langsung kirim prompt tanpa menunggu state update
    sendMessage(prompt)
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-slate-700/50 bg-slate-800/30 backdrop-blur-md">
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-to-r from-blue-500 to-cyan-600 shadow-lg">
          <img
            src="/assets/gymbot-logo.png"
            alt="Gym Logo"
            className="w-full h-full object-cover rounded-full"
          />
        </div>
        <div className="flex-1">
          <h1 className="font-bold text-xl text-white">FitBot</h1>
          <p className="text-sm text-slate-300">Your Personal Fitness Assistant</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          <span className="text-xs text-green-400 font-medium">Online</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-transparent to-slate-900/20">
        {messages.map((message, index) => (
          <div key={index} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            {message.role === "assistant" && (
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-cyan-600 flex items-center justify-center shadow-lg ring-2 ring-blue-500/20 flex-shrink-0">
                <img
                  src="/assets/gym_logo.png"
                  alt="Gym Logo"
                  className="w-full h-full object-cover rounded-full"
                />
              </div>
            )}

            <div
              className={`max-w-[80%] p-4 rounded-2xl shadow-xl backdrop-blur-sm ${
                message.role === "user"
                  ? "bg-gradient-to-r from-blue-500 to-cyan-600 text-white rounded-br-none ml-auto"
                  : "bg-slate-800/80 text-white border border-slate-700/50 rounded-bl-none"
              }`}
            >
              {/* 3. INI BAGIAN UTAMA YANG DIPERBAIKI */}
              <div className="prose prose-sm prose-invert max-w-none">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
              <p className={`text-xs mt-2 opacity-70 ${message.role === "user" ? "text-blue-100" : "text-slate-400"}`}>
                {message.timestamp.toLocaleTimeString("id-ID", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>

            {message.role === "user" && (
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg ring-2 ring-cyan-500/20 flex-shrink-0">
                <span className="text-white text-sm font-bold">YOU</span>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 justify-start">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-cyan-600 flex items-center justify-center shadow-lg ring-2 ring-blue-500/20 flex-shrink-0">
              <img
                src="/assets/gym_logo.png"
                alt="Gym Logo"
                className="w-full h-full object-cover rounded-full"
              />
            </div>
            <div className="bg-slate-800/80 text-white border border-slate-700/50 p-4 rounded-2xl rounded-bl-none shadow-xl backdrop-blur-sm">
              <div className="flex items-center gap-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                </div>
                <span className="text-sm text-slate-300">FitBot sedang mengetik...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-slate-700/50 bg-slate-800/30 backdrop-blur-md">
        <div className="flex flex-col gap-3 max-w-4xl mx-auto">
          {/* Quick Actions */}
          <div className="flex gap-2 flex-wrap">
            {quickActions.map((act, idx) => (
              <button
                key={idx}
                onClick={() => handlePromptClick(act.prompt)}
                className="px-4 py-2 text-sm bg-slate-700/80 hover:bg-slate-600/80 text-white border border-slate-600/50 rounded-full transition-all duration-200 backdrop-blur-sm shadow-md hover:shadow-lg ring-1 ring-slate-500/20 hover:ring-slate-400/30 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={isLoading}
              >
                {act.label}
              </button>
            ))}
          </div>
          <div className="flex gap-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Tanya tentang workout, nutrisi, atau tips fitness..."
              className="flex-1 px-4 py-3 bg-slate-700/80 border border-slate-600/50 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent backdrop-blur-sm shadow-lg disabled:opacity-50"
              disabled={isLoading}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg ring-2 ring-blue-500/20 hover:ring-blue-400/30"
              aria-label="Kirim"
            >
              <span className="text-lg">🚀</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}