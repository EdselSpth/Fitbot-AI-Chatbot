import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { messages } = await req.json();

  // Ambil pesan terakhir user
  const userMessage = messages[messages.length - 1]?.content || "";

  try {
    const resp = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: userMessage }),
    });

    const data = await resp.json();

    return NextResponse.json({
      role: "assistant",
      content: data.answer,
    });
  } catch (e: any) {
    return NextResponse.json(
      { role: "assistant", content: "⚠️ Error koneksi ke FastAPI" },
      { status: 500 }
    );
  }
}
