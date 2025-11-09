import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { User } from "lucide-react";
import NotificationWindow from "@/components/NotificationWindow";
import CurrentMedicationsList from "@/components/CurrentMedicationsList";
import WeekCalendar from "@/components/WeekCalendar";
import ScanMedicationButton from "@/components/ScanMedicationButton";
import AIAssistantChat from "@/components/AIAssistantChat";
import logo from "@/assets/logo.png";

const Dashboard = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");

  useEffect(() => {
    const isAuth = localStorage.getItem("isAuthenticated");
    const user = localStorage.getItem("username");
    if (!isAuth) {
      navigate("/");
      return;
    }
    if (user) setUsername(user);
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("username");
    navigate("/");
  };

  return (
    <div className="h-screen overflow-hidden bg-background flex flex-col">
      {/* Header: left = logo + name + welcome, right = actions */}
      <header className="border-b bg-card/50 backdrop-blur-sm shrink-0">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between gap-4">
          {/* Left group */}
          <div className="flex items-center gap-3 min-w-0">
            <img src={logo} alt="PillPal logo" className="h-14 w-14 rounded-lg shrink-0" />
            <h1 className="text-2xl font-bold text-primary shrink-0">PillPal</h1>
            {username && (
              <span className="text-xl text-muted-foreground truncate max-w-[40vw]">
                Welcome, {username}
              </span>
            )}
          </div>

          {/* Right group */}
          <div className="flex items-center gap-3 shrink-0">
            <Button
              variant="outline"
              onClick={() => navigate("/my-data")}
              className="gap-2"
            >
              <User className="h-4 w-4" />
              My Data
            </Button>
            <Button variant="ghost" onClick={handleLogout} size="sm">
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main content (no page scroll; internal scroll in calendar/chat) */}
      <div className="flex-1 container mx-auto px-4 py-6 overflow-hidden">
        <div className="grid lg:grid-cols-[1fr_2fr] gap-6 h-full">
          {/* LEFT: make chat fill remaining height */}
          <div className="flex flex-col h-full min-h-0 gap-6">
            <div className="shrink-0">
              <NotificationWindow />
            </div>
            <div className="shrink-0">
              <CurrentMedicationsList />
            </div>
            {/* Chat grows to fill, so its bottom aligns with calendar */}
            <div className="flex-1 min-h-0">
              <AIAssistantChat />
            </div>
          </div>

          {/* RIGHT: calendar fills full height and scrolls internally */}
          <div className="h-full min-h-0">
            <WeekCalendar />
          </div>
        </div>
      </div>

      {/* Floating scan button */}
      <ScanMedicationButton />
    </div>
  );
};

export default Dashboard;