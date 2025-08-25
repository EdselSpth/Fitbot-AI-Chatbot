'use client'

import { useState } from 'react'

export default function Chat() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [input, setInput] = useState('')

  const sendMessage = async () => {
    if (!input.trim()) return

    // Tambahin pesan user ke state
    setMessages((prev) => [...prev, { role: 'user', content: input }])

    // Request ke FastAPI
    const res = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: input }),
    })
    const data = await res.json()

    // Tambahin balasan AI
    setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }])

    setInput('')
  }

  return (
    <div className="flex flex-col w-full max-w-md py-24 mx-auto stretch">
      {messages.map((m, idx) => (
        <div key={idx} className="whitespace-pre-wrap mb-2">
          <b>{m.role === 'user' ? 'User:' : 'AI:'}</b> {m.content}
        </div>
      ))}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          sendMessage()
        }}
      >
        <input
          className="fixed bottom-0 w-full max-w-md p-2 mb-8 border rounded shadow-xl"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tanya soal fitness..."
        />
      </form>
    </div>
  )
}
