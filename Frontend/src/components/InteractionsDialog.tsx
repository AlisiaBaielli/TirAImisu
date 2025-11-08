import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";

interface InteractionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const InteractionsDialog = ({ open, onOpenChange }: InteractionsDialogProps) => {
  const handleClose = () => {
    toast.success("Medication interactions reviewed");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            <DialogTitle>Medication Interactions</DialogTitle>
          </div>
          <DialogDescription>
            Review potential interactions with your current medications
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="medication">Medication</Label>
            <Input
              id="medication"
              defaultValue="Aspirin + Warfarin"
              readOnly
              className="bg-muted"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="severity">Severity</Label>
            <Input
              id="severity"
              defaultValue="High"
              readOnly
              className="bg-muted text-destructive font-semibold"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="info">Information</Label>
            <Input
              id="info"
              defaultValue="May increase bleeding risk when taken together"
              readOnly
              className="bg-muted"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="details">Extended Information</Label>
            <Textarea
              id="details"
              readOnly
              className="bg-muted min-h-[120px]"
              defaultValue="This combination may significantly increase the risk of bleeding. Both medications affect blood clotting. If you are prescribed both medications, your healthcare provider will monitor you closely and may adjust dosages. Seek immediate medical attention if you experience unusual bleeding, bruising, or blood in urine or stool."
            />
          </div>
        </div>

        <div className="flex gap-3">
          <Button onClick={handleClose} className="flex-1">
            Understood
          </Button>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="flex-1">
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default InteractionsDialog;
