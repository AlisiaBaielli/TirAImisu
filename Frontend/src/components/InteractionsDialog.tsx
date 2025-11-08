import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle, CheckCircle } from "lucide-react";

export type InteractionSeverity = "high" | "low";

interface InteractionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  newMedicationName?: string;
  conflictWith?: string;
  severity?: InteractionSeverity;
  description?: string;
  interactionFound?: boolean;
}

const InteractionsDialog = ({
  open,
  onOpenChange,
  newMedicationName,
  conflictWith,
  severity = "low",
  description = "Potential interaction detected.",
  interactionFound = false,
}: InteractionsDialogProps) => {
  const isHigh = severity === "high";

  const handleEmailDoctor = () => {
    try {
      const stored = localStorage.getItem("userData");
      const doctorEmail = stored ? (JSON.parse(stored).doctorEmail as string | undefined) : undefined;
      const to = doctorEmail && doctorEmail.includes("@") ? doctorEmail : "doctor@example.com";
      const subject = encodeURIComponent("Medication Interaction Concern");
      const body = encodeURIComponent(
        `Hello Doctor,\n\nI noticed a potential interaction between "${newMedicationName}" and "${conflictWith}". Severity: ${
          isHigh ? "High" : "Low"
        }.\n\nDetails: ${description}\n\nCould you please advise?\n\nThank you.`
      );
      window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;
    } catch {
      window.location.href = "mailto:doctor@example.com?subject=Medication%20Interaction";
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {interactionFound ? (
              <AlertTriangle className={`h-5 w-5 ${isHigh ? "text-destructive" : "text-amber-600"}`} />
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

              <div
                className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${
                  isHigh ? "bg-destructive/10 text-destructive" : "bg-amber-100 text-amber-700"
                }`}
              >
                Severity: {isHigh ? "High" : "Low"}
              </div>

              <p className="text-sm text-muted-foreground">{description}</p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">No interactions detected with your current medications.</p>
          )}
        </div>

        <DialogFooter>
          {interactionFound ? (
            <Button variant="destructive" onClick={handleEmailDoctor}>
              Email your doctor
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