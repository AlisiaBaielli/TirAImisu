import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Bot, Send } from "lucide-react";

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
  const endRef = useRef<HTMLDivElement | null>(null);

  // Replace your old handleSend in AIAssistantChat.tsx with this:
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { 
      id: messages.length + 1, 
      text: input, 
      sender: "user" 
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    // --- Start Real API Call ---
    try {
      const userId = localStorage.getItem("userId");
      if (!userId) {
        throw new Error("user_id not found in localStorage");
      }

      // Send the request to your backend
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.text, // Send the message text
          user_id: userId
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Server request failed");
      }

      const data = await response.json();
      console.log('Data from server:', data);
      
      // Use data[1] based on your curl test
      const botReply = data.response; 
      console.log('Parsed bot reply:', botReply);
      
      // Or, if you fixed your backend to return {"response": ...}
      // const botReply = data.response;

      if (!botReply) {
         throw new Error("Invalid response format from server.");
      }

      // Add the REAL bot response to the chat
      const assistantMessage: Message = {
        id: userMessage.id + 1,
        text: botReply, // Use the real reply
        sender: "assistant",
      };
      setMessages((prev) => [...prev, assistantMessage]);

    } catch (error) {
      console.error("Failed to send message:", error);
      // Show an error message in the chat
      const errMessage: Message = {
        id: userMessage.id + 1,
        text: "Sorry, I'm having trouble connecting to the server.",
        sender: "assistant",
      };
      setMessages((prev) => [...prev, errMessage]);
    }
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <Card className="flex flex-col h-full rounded-xl shadow bg-white">
      <CardHeader className="pb-2 shrink-0">
        <div className="flex w-full items-center justify-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <CardTitle className="text-lg font-medium">AI Assistant</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-0 min-h-0">
        {/* Scrollable messages area fills remaining space */}
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
                {m.text}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        {/* Input bar fixed at bottom of card */}
        <div className="p-3 border-t shrink-0">
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about medications..."
              className="flex-1"
            />
            <Button size="icon" onClick={handleSend}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default AIAssistantChat;