"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, UserCircle, Calendar, ShieldCheck, Mail, KeyRound, Clock, Film, AlertCircle, FileText } from "lucide-react";

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;
  
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState<any>(null);

  useEffect(() => {
    const userStr = localStorage.getItem("admin_user");
    if (userStr) {
      const parsedUser = JSON.parse(userStr);
      if (!parsedUser.is_superuser && !parsedUser.admin_permissions?.can_manage_users) {
        router.push("/");
        return;
      }
      setCurrentUser(parsedUser);
    } else {
      router.push("/");
      return;
    }

    const fetchUser = async () => {
      try {
        const response = await apiClient.get(`/admin/users/${userId}/`);
        setUser(response.data);
      } catch (error) {
        console.error("Failed to fetch user", error);
        alert("Failed to load user details.");
      } finally {
        setLoading(false);
      }
    };

    if (userId) {
      fetchUser();
    }
  }, [router, userId]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-[60vh]">
        <div className="flex flex-col items-center gap-3 text-zinc-500">
          <div className="w-6 h-6 border-2 border-zinc-300 border-t-zinc-900 rounded-full animate-spin" />
          Loading user details...
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="p-8 flex flex-col items-center justify-center h-[60vh] gap-4">
        <h2 className="text-xl font-semibold text-zinc-900">User Not Found</h2>
        <Button onClick={() => router.push('/users')} variant="outline">Back to Directory</Button>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-4">
        <Button 
          variant="outline" 
          size="icon" 
          onClick={() => router.push('/users')}
          className="rounded-full w-10 h-10"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 flex items-center gap-3">
            {user.username}
            {!user.is_active ? (
              <Badge variant="destructive" className="bg-red-50 text-red-700 hover:bg-red-50 border-red-200">Disabled</Badge>
            ) : !user.is_email_verified && user.auth_provider === 'email' ? (
              <Badge variant="secondary" className="bg-amber-50 text-amber-700 hover:bg-amber-50 border-amber-200">Unverified</Badge>
            ) : (
              <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50 border-emerald-200">Verified</Badge>
            )}
          </h1>
          <p className="text-sm text-zinc-500 mt-1">Detailed profile information and activity.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Profile Info */}
        <Card className="md:col-span-2 shadow-sm border-zinc-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCircle className="w-5 h-5 text-indigo-600" />
              Core Identity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="space-y-1 p-4 bg-zinc-50 rounded-xl border border-zinc-100">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5"><Mail className="w-3.5 h-3.5"/> Email Address</span>
                <p className="text-zinc-900 font-medium">{user.email}</p>
              </div>
              
              <div className="space-y-1 p-4 bg-zinc-50 rounded-xl border border-zinc-100">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5"><KeyRound className="w-3.5 h-3.5"/> User ID</span>
                <p className="text-zinc-900 font-mono text-sm max-w-[200px] truncate" title={user.id}>{user.id}</p>
              </div>

              <div className="space-y-1 p-4 bg-zinc-50 rounded-xl border border-zinc-100">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5"><ShieldCheck className="w-3.5 h-3.5"/> Authentication Method</span>
                <div className="pt-1">
                  <Badge variant="outline" className="uppercase text-xs font-medium text-zinc-600 bg-white shadow-sm">
                    {user.auth_provider || 'Email'}
                  </Badge>
                </div>
              </div>

              <div className="space-y-1 p-4 bg-zinc-50 rounded-xl border border-zinc-100">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5"><Clock className="w-3.5 h-3.5"/> Last Login</span>
                <p className="text-zinc-900 font-medium">
                  {user.last_login ? new Date(user.last_login).toLocaleString(undefined, {
                    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit'
                  }) : 'Never logged in'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Context Sidebar */}
        <div className="space-y-6">
          
          {/* Statistics */}
          <Card className="shadow-sm border-zinc-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Video Usage Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <div className="flex items-center gap-2 text-zinc-600">
                  <Film className="w-4 h-4" />
                  <span className="text-sm font-medium">Total Videos Created</span>
                </div>
                <span className="font-bold text-zinc-900">{user.total_videos || 0}</span>
              </div>
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <div className="flex items-center gap-2 text-zinc-600">
                  <FileText className="w-4 h-4" />
                  <span className="text-sm font-medium">Generated Scripts</span>
                </div>
                <span className="font-bold text-zinc-900">{user.generated_scripts || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-red-600">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">Failed Operations</span>
                </div>
                <span className="font-bold text-red-600">{user.failed_videos || 0}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm border-zinc-200">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Account Lifecycle</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3 text-sm text-zinc-600">
                <div className="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                  <Calendar className="w-4 h-4" />
                </div>
                <div>
                  <p className="font-medium text-zinc-900">Joined Date</p>
                  <p>{new Date(user.date_joined).toLocaleDateString(undefined, {
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                  })}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
