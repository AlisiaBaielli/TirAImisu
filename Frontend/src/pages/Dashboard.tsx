import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { User } from "lucide-react";
import NotificationWindow from "@/components/NotificationWindow";
import CurrentMedicationsList from "@/components/CurrentMedicationsList";
import WeekCalendar from "@/components/WeekCalendar";
import ScanMedicationButton from "@/components/ScanMedicationButton";
import AIAssistantChat from "@/components/AIAssistantChat";

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
      <header className="border-b bg-card/50 backdrop-blur-sm shrink-0">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-primary">PillPal</h1>
            {username && (
              <span className="text-sm text-muted-foreground">
                Welcome, {username}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
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

      <div className="flex-1 container mx-auto px-4 py-6 overflow-hidden">
        {/* 2-column layout; left uses 3 fixed rows (chat fixed height), right spans them */}
        <div className="grid lg:grid-cols-[1fr_2fr] gap-6 h-full">
          <div className="grid grid-rows-[auto_auto_340px] gap-6 h-full min-h-0">
            <NotificationWindow />
            <CurrentMedicationsList />
            <AIAssistantChat /> {/* fills 340px row; internal messages scroll */}
          </div>
          <div className="h-full min-h-0">
            <WeekCalendar /> {/* spans same total height; bottom aligns with chat bottom */}
          </div>
        </div>
      </div>

      {/* Floating scan button overlapping calendar */}
      <ScanMedicationButton />
    </div>
  );
};

export default Dashboard;