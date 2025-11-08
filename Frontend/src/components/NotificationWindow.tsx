import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bell } from "lucide-react";
import { toast } from "sonner";

// Increased height for notifications
const NOTIFICATION_HEIGHT = 260; // px

const NotificationWindow = () => {
  const [show, setShow] = useState(true);

  // Question 1 state
  const [takenAnswered, setTakenAnswered] = useState(false);

  // Stock warning state
  const [stockHandled, setStockHandled] = useState(false);

  const aspirinName = "Aspirin 100mg";
  const lowStockMed = "Paracetamol";

  // Example: Add more notifications here if needed
  const notifications = [
    {
      key: "taken",
      content: (
        <div className="rounded-md border border-success/30 bg-success/10 p-3 space-y-2">
          <p className="text-sm">
            Have you taken <span className="font-semibold text-success">{aspirinName}</span>?
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={() => handleTaken(true)}
              className="flex-1"
              disabled={takenAnswered}
            >
              Yes
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleTaken(false)}
              className="flex-1"
              disabled={takenAnswered}
            >
              No
            </Button>
          </div>
        </div>
      ),
    },
    {
      key: "stock",
      content: (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 space-y-2">
          <p className="text-sm">
            You will run out of <span className="font-semibold text-destructive">{lowStockMed}</span> in a week.
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              onClick={handleOrder}
              className="flex-1"
              disabled={stockHandled}
            >
              Order it
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleDismissStock}
              className="flex-1"
              disabled={stockHandled}
            >
              Dismiss
            </Button>
          </div>
        </div>
      ),
    },
    // Add more notification objects here as needed
  ];

  function handleTaken(taken: boolean) {
    setTakenAnswered(true);
    if (taken) {
      toast.success(`Marked ${aspirinName} as taken.`);
    } else {
      toast.info("We’ll remind you again later.");
    }
    maybeHide(true, stockHandled);
  }

  function handleOrder() {
    setStockHandled(true);
    toast.success(`Order placed for ${lowStockMed}.`);
    maybeHide(takenAnswered, true);
  }

  function handleDismissStock() {
    setStockHandled(true);
    toast.info("Reminder dismissed.");
    maybeHide(takenAnswered, true);
  }

  function maybeHide(takenDone: boolean, stockDone: boolean) {
    if (takenDone && stockDone) setShow(false);
  }

  if (!show) return null;

  return (
    <Card className="border-primary/20 shadow-md">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" />
          Notifications
        </CardTitle>
      </CardHeader>
      <CardContent
        className="space-y-4"
        style={{
          maxHeight: NOTIFICATION_HEIGHT,
          overflowY: "auto",
        }}
      >
        {notifications.map((n) => n.content)}
      </CardContent>
    </Card>
  );
};

export default NotificationWindow;