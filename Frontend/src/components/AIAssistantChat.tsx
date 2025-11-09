import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Bot, Send, Loader2 } from "lucide-react"; 
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: number;
  text: string;
  sender: "user" | "assistant";
}

const AIAssistantChat = () => {
  const [messages, setMessages] = useState<Message[]>([
    { id: 1, text: "Hello! I'm your medication assistant. How can I help you today?", sender: "assistant" },
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);
  const [hovered, setHovered] = useState(false);
  const EXPAND_PX = 140;

  const handleSend = async () => {
    const messageText = input.trim();
    if (!messageText || isSending) return;

    setIsSending(true);

    const userMessage: Message = { 
      id: Date.now(), 
      text: messageText, 
      sender: "user" 
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    // --- THIS IS THE NEW DELAY ---
    // Wait 400ms before showing "Thinking..."
    await new Promise((resolve) => setTimeout(resolve, 400));
    // -----------------------------

    // --- Create a temporary loading message ---
    const placeholderId = Date.now() + 1;
    const placeholderMessage: Message = {
      id: placeholderId,
      text: "Thinking...",
      sender: "assistant",
    };
    setMessages((prev) => [...prev, placeholderMessage]);
    // ------------------------------------------

    try {
      const userId = localStorage.getItem("userId");
      if (!userId) {
        throw new Error("userId not found in localStorage");
      }

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.text,
          user_id: userId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Server request failed");
      }

      const data = await response.json();
      const botReply = data.response; 
      
      if (!botReply) {
         throw new Error("Invalid response format from server.");
      }

      // --- Update the placeholder with the real message ---
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === placeholderId
            ? { ...msg, text: botReply } // Update text
            : msg
        )
      );

    } catch (error) {
      console.error("Failed to send message:", error);
      // --- Update the placeholder with an error ---
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === placeholderId
            ? { ...msg, text: "Sorry, I'm having trouble connecting to the server." }
            : msg
        )
      );
    } finally {
      setIsSending(false); 
    }
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <Card
      className="flex flex-col h-full rounded-xl shadow bg-white transition-all duration-300 ease-out"
      style={
        hovered
          ? {
              height: `calc(100% + ${EXPAND_PX}px)`,
              marginTop: `-${EXPAND_PX}px`,
              zIndex: 40,
              position: "relative",
            }
          : { height: "100%", marginTop: 0, position: "relative", zIndex: 1 }
      }
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <CardHeader className="pb-2 shrink-0">
        <div className="flex w-full items-center justify-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg font-medium">AI Assistant</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-0 min-h-0">
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 custom-scrollbar">
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  m.sender === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground"
                }`}
              >
                {m.text === "Thinking..." ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                ) : (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.text}
                  </ReactMarkdown>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <div className="p-3 border-t shrink-0">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about medications..."
              className="flex-1"
              disabled={isSending}
            />
            <Button size="icon" onClick={handleSend} disabled={isSending}>
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default AIAssistantChat;