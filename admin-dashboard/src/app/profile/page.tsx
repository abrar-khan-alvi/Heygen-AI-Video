"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { UserCircle, Shield, KeyRound } from "lucide-react";

export default function ProfilePage() {
  const [user, setUser] = useState<any>(null);
  
  // Password change state
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [errorLine, setErrorLine] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    const userStr = localStorage.getItem("admin_user");
    if (userStr) {
      setUser(JSON.parse(userStr));
    }
  }, []);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorLine("");
    setSuccessMsg("");

    if (newPassword !== newPasswordConfirm) {
      setErrorLine("New passwords do not match.");
      return;
    }

    try {
      setIsChangingPassword(true);
      const res = await apiClient.post("/admin/profile/change-password/", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      setSuccessMsg(res.data.message || "Password updated successfully.");
      setOldPassword("");
      setNewPassword("");
      setNewPasswordConfirm("");
    } catch (err: any) {
      setErrorLine(err.response?.data?.error || "Failed to change password. Ensure your current password is correct.");
    } finally {
      setIsChangingPassword(false);
    }
  };

  if (!user) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[50vh]">
        <div className="animate-pulse flex items-center gap-2 text-zinc-500">
          Loading profile...
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-zinc-100">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <UserCircle className="w-5 h-5" />
            <span className="text-sm font-semibold tracking-wide uppercase">My Profile</span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Account Settings</h1>
          <p className="text-zinc-500">Manage your personal admin account and security credentials.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Profile Info Card */}
        <Card className="shadow-sm border-zinc-200">
          <CardHeader>
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-5 h-5 text-zinc-400" />
              <CardTitle>Identity Information</CardTitle>
            </div>
            <CardDescription>Your current dashboard access level and details.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center text-zinc-500 text-2xl font-semibold shrink-0">
                {user.username?.[0]?.toUpperCase()}
              </div>
              <div className="flex flex-col">
                <span className="text-xl font-semibold text-zinc-900">{user.username}</span>
                <span className="text-zinc-500">{user.email}</span>
              </div>
            </div>

            <div className="pt-4 border-t border-zinc-100 flex flex-col gap-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-zinc-500 font-medium">Account Role</span>
                {user.is_superuser ? (
                  <Badge className="bg-indigo-50 text-indigo-700 border border-indigo-200">Super Admin</Badge>
                ) : (
                  <Badge className="bg-zinc-100 text-zinc-700 border border-zinc-200">Staff Admin</Badge>
                )}
              </div>
              
              {!user.is_superuser && user.admin_permissions && (
                <div className="flex justify-between items-start text-sm">
                  <span className="text-zinc-500 font-medium mt-1">Granted Access</span>
                  <div className="flex gap-1.5 flex-wrap justify-end max-w-[200px]">
                    {user.admin_permissions.can_manage_users && (
                      <Badge variant="outline" className="border-zinc-200 text-zinc-600 font-normal">Users</Badge>
                    )}
                    {user.admin_permissions.can_manage_videos && (
                      <Badge variant="outline" className="border-zinc-200 text-zinc-600 font-normal">Videos</Badge>
                    )}
                    {!user.admin_permissions.can_manage_users && !user.admin_permissions.can_manage_videos && (
                      <span className="text-zinc-400 italic">View Only</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Change Password Card */}
        <Card className="shadow-sm border-zinc-200">
          <CardHeader>
            <div className="flex items-center gap-2 mb-1">
              <KeyRound className="w-5 h-5 text-zinc-400" />
              <CardTitle>Change Password</CardTitle>
            </div>
            <CardDescription>Update your password to keep your dashboard secure.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePasswordChange} className="space-y-4">
              {errorLine && (
                <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg">
                  {errorLine}
                </div>
              )}
              {successMsg && (
                <div className="p-3 text-sm text-emerald-600 bg-emerald-50 border border-emerald-100 rounded-lg">
                  {successMsg}
                </div>
              )}
              
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-600 uppercase tracking-wider ml-1">Current Password</label>
                <Input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                  className="h-11 rounded-xl bg-zinc-50/50 border-zinc-200"
                />
              </div>

              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-semibold text-zinc-600 uppercase tracking-wider ml-1">New Password</label>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  className="h-11 rounded-xl bg-zinc-50/50 border-zinc-200"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-600 uppercase tracking-wider ml-1">Confirm New Password</label>
                <Input
                  type="password"
                  value={newPasswordConfirm}
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                  required
                  minLength={8}
                  className="h-11 rounded-xl bg-zinc-50/50 border-zinc-200"
                />
              </div>

              <div className="pt-4">
                <Button 
                  type="submit" 
                  disabled={isChangingPassword}
                  className="w-full h-11 rounded-xl bg-zinc-900 text-white hover:bg-zinc-800 transition-colors"
                >
                  {isChangingPassword ? "Updating..." : "Update Password"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
