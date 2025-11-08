import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bell } from "lucide-react";
import { toast } from "sonner";

// Slightly reduced height for a more compact panel
const NOTIFICATION_HEIGHT = 190; // px

type NotificationCategory = "reminder" | "low_stock";

type NotificationItem = {
  id: string;
  category: NotificationCategory;
  title: string;
  message: string;
  due_at: string;
  color: string; // "blue" | "red"
  metadata?: Record<string, any>;
};

const NotificationWindow = () => {
  const [show, setShow] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const baseUrl = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost:8000";

  const visibleNotifications = useMemo(
    () => notifications.filter((n) => !dismissed.has(n.id)),
    [notifications, dismissed]
  );

  const colorClasses = (n: NotificationItem) => {
    if (n.category === "low_stock" || n.color === "red") {
      return "border-destructive/30 bg-destructive/10";
    }
    return "border-primary/30 bg-primary/10"; // reminder (blue)
  };

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${baseUrl}/api/notifications`);
      if (!res.ok) throw new Error(`Failed to load notifications (${res.status})`);
      const data = await res.json();
      const items: NotificationItem[] = Array.isArray(data?.notifications) ? data.notifications : [];
      setNotifications(items);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 30000); // refresh every 30s
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleReminderYes = (n: NotificationItem) => {
    setDismissed((prev) => new Set(prev).add(n.id));
    const med = n?.metadata?.medicationName ? ` ${n.metadata.medicationName}` : "";
    toast.success(`Marked${med} as taken.`);
  };

  const handleReminderNo = (n: NotificationItem) => {
    setDismissed((prev) => new Set(prev).add(n.id));
    toast.info("We’ll remind you again later.");
  };

  const handleOrder = (n: NotificationItem) => {
    setDismissed((prev) => new Set(prev).add(n.id));
    const med = n?.metadata?.medicationName ? ` ${n.metadata.medicationName}` : "";
    toast.success(`Order placed for${med}.`);
  };

  const handleDismiss = (n: NotificationItem) => {
    setDismissed((prev) => new Set(prev).add(n.id));
    toast.info("Reminder dismissed.");
  };

  if (!show) return null;

  return (
    <Card className="border-primary/20 shadow-md">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" />
          Notifications
        </CardTitle>
      </CardHeader>
      <CardContent
        className="space-y-2"
        style={{
          maxHeight: NOTIFICATION_HEIGHT,
          overflowY: "auto",
        }}
      >
        {loading && <div className="text-xs text-muted-foreground">Loading…</div>}
        {error && !loading && <div className="text-xs text-destructive">{error}</div>}
        {!loading && !error && visibleNotifications.length === 0 && (
          <div className="text-xs text-muted-foreground">No notifications</div>
        )}
        {visibleNotifications.map((n) => (
          <div key={n.id} className={`rounded-md border p-2 space-y-1 ${colorClasses(n)}`}>
            <p className="text-xs">
              <span className="font-medium">{n.title}</span>
            </p>
            <p className="text-[11px] text-muted-foreground">{n.message}</p>
            {n.category === "reminder" ? (
              <div className="flex gap-2">
                <Button size="sm" onClick={() => handleReminderYes(n)} className="flex-1 h-8 py-1">
                  Yes
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleReminderNo(n)} className="flex-1 h-8 py-1">
                  No
                </Button>
              </div>
            ) : (
              <div className="flex gap-2">
                <Button size="sm" variant="destructive" onClick={() => handleOrder(n)} className="flex-1 h-8 py-1">
                  Order it
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleDismiss(n)} className="flex-1 h-8 py-1">
                  Dismiss
                </Button>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

export default NotificationWindow;