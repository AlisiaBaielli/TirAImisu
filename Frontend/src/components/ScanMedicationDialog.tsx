import { useState, useRef } from "react";
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
import { Camera, Loader2 } from "lucide-react";
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
  onConfirm: (data: NewMedicationPayload) => void;
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

  // Camera state
  const [cameraActive, setCameraActive] = useState(false);
  const [photo, setPhoto] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const handleCameraClick = async () => {
    setCameraActive(true);
    setPhoto(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch {
      toast.error("Could not access camera");
      setCameraActive(false);
    }
  };

  const handleTakePhoto = async () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/png");
      setPhoto(dataUrl);
      const stream = video.srcObject as MediaStream;
      stream?.getTracks().forEach((track) => track.stop());
      setCameraActive(false);

      setScanning(true);
      try {
        const base64 = dataUrl.split(",")[1];
        const userId = localStorage.getItem("userId") || "1";
        const base = (import.meta as any)?.env?.VITE_BACKEND_URL ?? "http://localhost:8000";
        const res = await fetch(`${base}/api/camera-agent/scan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, image_b64: base64 }),
        });
        if (!res.ok) throw new Error("Failed to scan medication image");
        const result = await res.json();
        setManualEntry((prev) => ({
          ...prev,
          name: result.medication_name ?? "",
          dosage: result.dosage ?? "",
          numberOfPills: result.num_pills ? String(result.num_pills) : "",
        }));
        toast.success("Medication scanned!");
      } catch (e: any) {
        toast.error(e?.message ?? "Scan failed");
      } finally {
        setScanning(false);
      }
    }
  };

  const handleCancelCamera = () => {
    setCameraActive(false);
    setPhoto(null);
    if (videoRef.current) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream?.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }
  };

  const handleConfirm = () => {
    if (!manualEntry.name || !manualEntry.dosage) {
      toast.error("Please enter medication name and dosage");
      return;
    }
    // Do not call backend here — ScanMedicationButton will persist + run interaction checks.
    onConfirm(manualEntry);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md animate-scale-in">
        <DialogHeader>
          <DialogTitle>Add Medication</DialogTitle>
          <DialogDescription>Take a photo or enter medication details manually</DialogDescription>
        </DialogHeader>
        <div className="space-y-6 py-4">
          {/* Camera / Photo area */}
          <div className="flex flex-col items-center relative">
            {!cameraActive && !photo && !scanning && (
              <Button
                variant="outline"
                size="lg"
                className="h-32 w-32 rounded-full"
                onClick={handleCameraClick}
                disabled={scanning}
              >
                <Camera className="h-12 w-12" />
              </Button>
            )}

            {cameraActive && (
              <div className="flex flex-col items-center gap-2 relative">
                <video ref={videoRef} className="rounded-lg border" style={{ width: 220, height: 160 }} />
                <div className="flex gap-2 mt-2">
                  <Button size="sm" onClick={handleTakePhoto} disabled={scanning}>
                    {scanning ? "Scanning..." : "Take Photo"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleCancelCamera} disabled={scanning}>
                    Cancel
                  </Button>
                </div>
                <canvas ref={canvasRef} style={{ display: "none" }} />
                {scanning && (
                  <div className="absolute inset-0 bg-black/50 flex flex-col items-center justify-center rounded-lg">
                    <Loader2 className="h-6 w-6 animate-spin text-white mb-2" />
                    <p className="text-xs text-white tracking-wide animate-pulse">Processing image...</p>
                  </div>
                )}
              </div>
            )}

            {photo && (
              <div className="flex flex-col items-center gap-2 relative">
                <img src={photo} alt="Medication" className="rounded-lg border w-32 h-32 object-cover" />
                <Button size="sm" variant="outline" onClick={() => setPhoto(null)} disabled={scanning}>
                  Retake
                </Button>
              </div>
            )}

            {scanning && !cameraActive && !photo && (
              <div className="h-32 w-32 flex flex-col items-center justify-center rounded-full border">
                <Loader2 className="h-6 w-6 animate-spin text-primary mb-2" />
                <p className="text-xs text-muted-foreground animate-pulse">Processing...</p>
              </div>
            )}
          </div>

          {/* Manual Entry */}
          <div className="space-y-4">
            <h3 className="font-semibold text-sm">Manual Entry</h3>
            <div className="space-y-2">
              <Label htmlFor="name">Medication Name</Label>
              <Input id="name" value={manualEntry.name} onChange={(e) => setManualEntry({ ...manualEntry, name: e.target.value })} placeholder="e.g., Aspirin" disabled={scanning} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dosage">Dosage</Label>
              <Input id="dosage" value={manualEntry.dosage} onChange={(e) => setManualEntry({ ...manualEntry, dosage: e.target.value })} placeholder="e.g., 100mg" disabled={scanning} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="pills">Number of Pills</Label>
              <Input id="pills" type="number" value={manualEntry.numberOfPills} onChange={(e) => setManualEntry({ ...manualEntry, numberOfPills: e.target.value })} placeholder="1" disabled={scanning} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input id="startDate" type="date" value={manualEntry.startDate} onChange={(e) => setManualEntry({ ...manualEntry, startDate: e.target.value })} disabled={scanning} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="endDate">End Date (Optional)</Label>
                <Input id="endDate" type="date" value={manualEntry.endDate} onChange={(e) => setManualEntry({ ...manualEntry, endDate: e.target.value })} disabled={scanning} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="frequency">Frequency</Label>
                <Select value={manualEntry.frequency} onValueChange={(value) => setManualEntry({ ...manualEntry, frequency: value })} disabled={scanning}>
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
                <Input id="time" type="time" value={manualEntry.time} onChange={(e) => setManualEntry({ ...manualEntry, time: e.target.value })} disabled={scanning} />
              </div>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleConfirm} className="w-full" disabled={scanning}>
            {scanning ? "Processing..." : "Confirm"}
          </Button>
        </DialogFooter>
        {scanning && (
            <div className="fixed inset-0 flex flex-col items-center justify-center bg-black/40 backdrop-blur-sm z-50">
              <div className="bg-white rounded-full p-6 shadow-xl flex flex-col items-center justify-center animate-fade-in">
                <Loader2 className="h-10 w-10 text-primary animate-spin mb-2" />
                <p className="text-sm font-medium text-gray-600 animate-pulse">Scanning your pill...</p>
              </div>
            </div>
          )}


      </DialogContent>
    </Dialog>
  );
};

export default ScanMedicationDialog;