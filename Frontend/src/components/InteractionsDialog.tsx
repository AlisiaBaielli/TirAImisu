import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle, CheckCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface InteractionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  newMedicationName?: string;
  conflictWith?: string;
  description?: string;
  interactionFound?: boolean;
}

const InteractionsDialog = ({
  open,
  onOpenChange,
  newMedicationName,
  conflictWith,
  description = "Potential interaction detected.",
  interactionFound = false,
}: InteractionsDialogProps) => {
  const [sending, setSending] = useState(false);

  const handleEmailDoctor = async () => {
    const userId = parseInt(localStorage.getItem("userId") || "1", 10);
    const raw = (import.meta as any)?.env?.VITE_BACKEND_URL;
    const base = raw ? String(raw).replace(/\/$/, "") : ""; // empty string fallback

    const content =
      `Potential interaction detected.\n` +
      `New medication: ${newMedicationName || "Unknown"}\n` +
      `Conflicts with: ${conflictWith || "Unknown"}\n` +
      `Details: ${description || "N/A"}`;

    try {
      setSending(true);
      const res = await fetch(`${base}/api/send-email-to-doctor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, content }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok || data?.success === false) {
        throw new Error(data?.detail || data?.error || `Failed to send email (status ${res.status})`);
      }

      toast.success("Email sent to your doctor.");
      onOpenChange(false);
    } catch (err: any) {
      toast.error(err?.message || "Could not send email.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {interactionFound ? (
              <AlertTriangle className="h-5 w-5 text-destructive" />
            ) : (
              <CheckCircle className="h-5 w-5 text-success" />
            )}
            <DialogTitle>{interactionFound ? "Medication Interaction" : "No Interactions Found"}</DialogTitle>
          </div>
          <DialogDescription>
            {interactionFound ? "Review the potential interaction" : "This medication does not interact with your current medications"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {interactionFound ? (
            <>
              <p className="text-sm">
                The medication <span className="font-semibold">{newMedicationName}</span> may clash with{" "}
                <span className="font-semibold">{conflictWith}</span>.
              </p>
              <p className="text-sm text-muted-foreground">{description}</p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No interactions detected with your current medications.</p>
          )}
        </div>

        <DialogFooter>
          {interactionFound ? (
            <Button variant="destructive" onClick={handleEmailDoctor} disabled={sending}>
              {sending ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Sending…
                </span>
              ) : (
                "Email your doctor"
              )}
            </Button>
          ) : (
            <Button onClick={() => onOpenChange(false)}>Close</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default InteractionsDialog;