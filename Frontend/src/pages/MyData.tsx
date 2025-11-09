import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

const formatCardNumber = (v: string) =>
  v.replace(/\D/g, "").slice(0, 16).replace(/(\d{4})(?=\d)/g, "$1 ").trim();

const formatExpiry = (v: string) => {
  const d = v.replace(/\D/g, "").slice(0, 4);
  if (d.length <= 2) return d;
  return d.slice(0, 2) + "/" + d.slice(2);
};

const formatCvc = (v: string) => v.replace(/\D/g, "").slice(0, 4);

type FormShape = {
  full_name: string;
  age: string;
  gender: string;
  email: string;
  healthIssues: string;
  doctor_email: string;
  address: string;       // maps from backend `street`
  house_number: string;
  city: string;
  post_code: string;
  phone_number: string;
  credit_card_number: string;
  expiry_date: string;
  cvv: string;
};

const MyData = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<FormShape>({
    full_name: "",
    age: "",
    gender: "",
    email: "",
    healthIssues: "",
    doctor_email: "",
    address: "",
    house_number: "",
    city: "",
    post_code: "",
    phone_number: "",
    credit_card_number: "",
    expiry_date: "",
    cvv: "",
  });

  useEffect(() => {
    const isAuth = localStorage.getItem("isAuthenticated");
    if (!isAuth) {
      navigate("/");
      return;
    }
    const userId = localStorage.getItem("userId") || "1";
    const load = async () => {
      try {
        const base = (import.meta as any)?.env?.VITE_BACKEND_URL;
        const res = await fetch(`${base}/api/users/${userId}`);
        if (!res.ok) throw new Error(`Failed to load user (${res.status})`);
        const data = await res.json();
        const u = data?.user ?? {};
        const next: FormShape = {
          full_name: u.full_name ?? "",
          age: String(u.age ?? ""),
          gender: u.gender ?? "",
          email: u.email ?? "",
          healthIssues: "",
          doctor_email: u.doctor_email ?? "",
          address: u.street ?? "",
          house_number: u.house_number ?? "",
          city: u.city ?? "",
          post_code: u.post_code ?? "",
          phone_number: u.phone_number ?? "",
          credit_card_number: u.credit_card_number ?? "",
          expiry_date: u.expiry_date ?? "",
          cvv: u.cvv ?? "",
        };
        setFormData(next);
        localStorage.setItem("userData", JSON.stringify({ ...next, user_id: userId, doctorEmail: u.doctor_email ?? "" }));
      } catch {
        const saved = localStorage.getItem("userData");
        if (saved) {
          try {
            const parsed = JSON.parse(saved);
            setFormData((prev) => ({ ...prev, ...parsed }));
          } catch {}
        }
      }
    };
    load();
  }, [navigate]);

  const handleChange = (field: keyof FormShape, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    const userId = localStorage.getItem("userId") || "1";
    const base = (import.meta as any)?.env?.VITE_BACKEND_URL;
    
    try {
      // Prepare payload with backend field names
      const payload = {
        full_name: formData.full_name,
        age: formData.age,
        gender: formData.gender,
        email: formData.email,
        street: formData.address,  // map address -> street
        house_number: formData.house_number,
        city: formData.city,
        post_code: formData.post_code,
        phone_number: formData.phone_number,
        doctor_email: formData.doctor_email,
        credit_card_number: formData.credit_card_number,
        expiry_date: formData.expiry_date,
        cvv: formData.cvv,
      };

      const res = await fetch(`${base}/api/users/${userId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Failed to save (${res.status})`);
      }

      // Save both snake_case and common camelCase keys to keep other components working
      const compat = {
        ...formData,
        doctorEmail: formData.doctor_email,
        houseNumber: formData.house_number,
        postalCode: formData.post_code,
        phoneNumber: formData.phone_number,
        cardNumber: formData.credit_card_number,
        cardExpiry: formData.expiry_date,
        cardCvc: formData.cvv,
      };
      localStorage.setItem("userData", JSON.stringify(compat));
      toast.success("Saved successfully");
    } catch (err: any) {
      toast.error(err.message || "Failed to save changes");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="container mx-auto px-4 py-3 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/dashboard")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-2xl font-bold text-primary">My Data</h1>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>Personal Information</CardTitle>
            <CardDescription>Update your profile, contact and payment details</CardDescription>
          </CardHeader>

          <CardContent className="space-y-8">
            {/* Full name */}
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                value={formData.full_name}
                onChange={(e) => handleChange("full_name", e.target.value)}
                placeholder="First Last"
              />
            </div>

            {/* Basic */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="age">Age</Label>
                <Input
                  id="age"
                  type="number"
                  value={formData.age}
                  onChange={(e) => handleChange("age", e.target.value)}
                  placeholder="Age"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="gender">Gender</Label>
                <Input
                  id="gender"
                  value={formData.gender}
                  onChange={(e) => handleChange("gender", e.target.value)}
                  placeholder="Gender"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                placeholder="your.email@example.com"
              />
            </div>

            {/* Address */}
            <div className="space-y-2">
              <Label>Address</Label>
              <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
                <div className="md:col-span-3 space-y-2">
                  <Label htmlFor="address" className="sr-only">Street</Label>
                  <Input
                    id="address"
                    value={formData.address}
                    onChange={(e) => handleChange("address", e.target.value)}
                    placeholder="Street"
                  />
                </div>
                <div className="md:col-span-1 space-y-2">
                  <Label htmlFor="house_number" className="sr-only">No.</Label>
                  <Input
                    id="house_number"
                    value={formData.house_number}
                    onChange={(e) => handleChange("house_number", e.target.value)}
                    placeholder="No."
                  />
                </div>
                <div className="md:col-span-2 space-y-2">
                  <Label htmlFor="city" className="sr-only">City</Label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => handleChange("city", e.target.value)}
                    placeholder="City"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="post_code">Postal Code</Label>
                <Input
                  id="post_code"
                  value={formData.post_code}
                  onChange={(e) => handleChange("post_code", e.target.value)}
                  placeholder="e.g. 1011AB"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="phone_number">Phone Number</Label>
                <Input
                  id="phone_number"
                  type="tel"
                  value={formData.phone_number}
                  onChange={(e) => handleChange("phone_number", e.target.value)}
                  placeholder="+31 6 12345678"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="doctor_email">Doctor Email</Label>
              <Input
                id="doctor_email"
                type="email"
                value={formData.doctor_email}
                onChange={(e) => handleChange("doctor_email", e.target.value)}
                placeholder="doctor@example.com"
              />
            </div>

            {/* Payment */}
            <div className="space-y-2">
              <Label>Payment Information</Label>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="credit_card_number" className="sr-only">Card Number</Label>
                  <Input
                    id="credit_card_number"
                    inputMode="numeric"
                    autoComplete="cc-number"
                    placeholder="1234 5678 9012 3456"
                    value={formData.credit_card_number}
                    onChange={(e) => handleChange("credit_card_number", formatCardNumber(e.target.value))}
                  />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="expiry_date" className="sr-only">Expiry</Label>
                    <Input
                      id="expiry_date"
                      inputMode="numeric"
                      autoComplete="cc-exp"
                      placeholder="MM/YY"
                      value={formData.expiry_date}
                      onChange={(e) => handleChange("expiry_date", formatExpiry(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="cvv" className="sr-only">CVC</Label>
                    <Input
                      id="cvv"
                      inputMode="numeric"
                      autoComplete="cc-csc"
                      placeholder="CVC"
                      value={formData.cvv}
                      onChange={(e) => handleChange("cvv", formatCvc(e.target.value))}
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button onClick={handleSave} className="flex-1">Save Changes</Button>
              <Button variant="outline" onClick={() => navigate("/dashboard")} className="flex-1">
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MyData;