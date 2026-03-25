"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await apiClient.post("/auth/login/", { email_or_username: email, password });
      
      const { tokens, user } = response.data;
      const { access, refresh } = tokens;

      if (!user.is_staff) {
        setError("You do not have permission to access the admin dashboard.");
        setLoading(false);
        return;
      }

      localStorage.setItem("admin_access_token", access);
      localStorage.setItem("admin_refresh_token", refresh);
      localStorage.setItem("admin_user", JSON.stringify(user));
      document.cookie = "is_admin_logged_in=true; path=/";

      router.push("/");
    } catch (err: any) {
      if (err.response?.status === 401 || err.response?.status === 400) {
        setError(
          err.response?.data?.email_or_username?.[0] || 
          err.response?.data?.password?.[0] || 
          "Invalid credentials. Please try again."
        );
      } else {
        setError("An error occurred during login. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 font-sans p-4">
      <div className="w-full max-w-[400px] bg-white rounded-2xl shadow-sm border border-zinc-200 p-8 sm:p-10">
        
        {/* Branding */}
        <div className="flex flex-col items-center mb-10 text-center">
          <img 
            src="/logo.png" 
            alt="No Face ADS Logo" 
            className="w-14 h-14 rounded-xl object-cover mb-5 shadow-sm ring-1 ring-zinc-900/5 group-hover:scale-105 transition-transform" 
          />
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
            No Face ADS
          </h1>
          <p className="text-sm text-zinc-500 mt-1.5">
            Sign in to the staff dashboard
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-6">
          {error && (
            <div className="p-3.5 text-sm text-red-600 bg-red-50 rounded-lg flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-zinc-700">Email address</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="h-11 bg-zinc-50/50 border-zinc-200 focus-visible:ring-zinc-900 rounded-lg transition-colors placeholder:text-zinc-400"
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm font-medium text-zinc-700">Password</Label>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="h-11 bg-zinc-50/50 border-zinc-200 focus-visible:ring-zinc-900 rounded-lg transition-colors"
              />
            </div>
          </div>

          <Button 
            type="submit" 
            className="w-full h-11 bg-zinc-900 hover:bg-zinc-800 text-white font-medium rounded-lg transition-all" 
            disabled={loading}
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <div className="h-4 w-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                <span>Signing in...</span>
              </div>
            ) : (
              "Sign in"
            )}
          </Button>
        </form>
        
      </div>
    </div>
  );
}
