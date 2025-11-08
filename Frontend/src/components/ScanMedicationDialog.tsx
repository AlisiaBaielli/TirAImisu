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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Camera } from "lucide-react";
import { toast } from "sonner";

export interface NewMedicationPayload {
  name: string;
  dosage: string;
  numberOfPills: string;
  startDate: string;
  endDate: string;
  frequency: string;
  time: string;
}

interface ScanMedicationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (data: NewMedicationPayload) => void; // CHANGED
}

const ScanMedicationDialog = ({ open, onOpenChange, onConfirm }: ScanMedicationDialogProps) => {
  const [manualEntry, setManualEntry] = useState<NewMedicationPayload>({
    name: "",
    dosage: "",
    numberOfPills: "",
    startDate: "",
    endDate: "",
    frequency: "",
    time: "",
  });

  const handleCameraClick = () => {};

  const handleConfirm = () => {
    if (!manualEntry.name || !manualEntry.dosage) {
      toast.error("Please enter medication name and dosage");
      return;
    }
    onConfirm(manualEntry); // CHANGED
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md animate-scale-in">
        <DialogHeader>
          <DialogTitle>Scan Medication</DialogTitle>
          <DialogDescription>Take a photo or enter medication details manually</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          <div className="flex justify-center">
            <Button variant="outline" size="lg" className="h-32 w-32 rounded-full" onClick={handleCameraClick}>
              <Camera className="h-12 w-12" />
            </Button>
          </div>

          <div className="space-y-4">
            <h3 className="font-semibold text-sm">Manual Entry</h3>

            <div className="space-y-2">
              <Label htmlFor="name">Medication Name</Label>
              <Input
                id="name"
                value={manualEntry.name}
                onChange={(e) => setManualEntry({ ...manualEntry, name: e.target.value })}
                placeholder="e.g., Aspirin"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="dosage">Dosage</Label>
              <Input
                id="dosage"
                value={manualEntry.dosage}
                onChange={(e) => setManualEntry({ ...manualEntry, dosage: e.target.value })}
                placeholder="e.g., 100mg"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="pills">Number of Pills</Label>
              <Input
                id="pills"
                type="number"
                value={manualEntry.numberOfPills}
                onChange={(e) => setManualEntry({ ...manualEntry, numberOfPills: e.target.value })}
                placeholder="1"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input
                  id="startDate"
                  type="date"
                  value={manualEntry.startDate}
                  onChange={(e) => setManualEntry({ ...manualEntry, startDate: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endDate">End Date (Optional)</Label>
                <Input
                  id="endDate"
                  type="date"
                  value={manualEntry.endDate}
                  onChange={(e) => setManualEntry({ ...manualEntry, endDate: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="frequency">Frequency</Label>
                <Select
                  value={manualEntry.frequency}
                  onValueChange={(value) => setManualEntry({ ...manualEntry, frequency: value })}
                >
                  <SelectTrigger id="frequency">
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Every Day</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="time">Time</Label>
                <Input
                  id="time"
                  type="time"
                  value={manualEntry.time}
                  onChange={(e) => setManualEntry({ ...manualEntry, time: e.target.value })}
                />
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleConfirm} className="w-full">Confirm</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ScanMedicationDialog;