import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { User, MessageCircle } from "lucide-react";
import NotificationWindow from "@/components/NotificationWindow";
import CurrentMedicationsList from "@/components/CurrentMedicationsList";
import WeekCalendar from "@/components/WeekCalendar";
import ScanMedicationButton from "@/components/ScanMedicationButton";

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
    
    if (user) {
      setUsername(user);
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("username");
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-40 animate-fade-in">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-primary">PillPal</h1>
            {username && <span className="text-sm text-muted-foreground">Welcome, {username}</span>}
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              onClick={() => navigate("/chat")}
              className="gap-2 hover-scale"
            >
              <MessageCircle className="h-4 w-4" />
              Chat
            </Button>
            <Button 
              variant="outline" 
              onClick={() => navigate("/my-data")}
              className="gap-2 hover-scale"
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

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6 max-h-[calc(100vh-80px)] overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
          {/* Left Column - Notifications and Medications */}
          <div className="space-y-6 animate-fade-in">
            <NotificationWindow />
            <CurrentMedicationsList />
          </div>

          {/* Right Column - Calendar */}
          <div className="lg:col-span-2 animate-fade-in">
            <WeekCalendar />
          </div>
        </div>
      </div>

      {/* Floating Scan Button */}
      <ScanMedicationButton />
    </div>
  );
};

export default Dashboard;
