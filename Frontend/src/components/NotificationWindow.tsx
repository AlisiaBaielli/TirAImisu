import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bell } from "lucide-react";
import { toast } from "sonner";

const NotificationWindow = () => {
  const [hasNotification, setHasNotification] = useState(true);
  const medicationName = "Aspirin 100mg";

  const handleResponse = (taken: boolean) => {
    setHasNotification(false);
    if (taken) {
      toast.success(`Marked ${medicationName} as taken`);
    } else {
      toast.info("Reminder will be shown again later");
    }
  };

  if (!hasNotification) {
    return null;
  }

  return (
    <Card className="border-primary/20 shadow-md">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" />
          Medication Reminder
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm">
          Have you taken <span className="font-semibold text-primary">{medicationName}</span>?
        </p>
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => handleResponse(true)}
            className="flex-1"
          >
            Yes
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleResponse(false)}
            className="flex-1"
          >
            No
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default NotificationWindow;
