"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Search, UserPlus, ShieldAlert, MonitorCheck, Plus, Trash2 } from "lucide-react";

export default function AdministrationPage() {
  const [admins, setAdmins] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [isSuperuser, setIsSuperuser] = useState(false);
  const [canManageUsers, setCanManageUsers] = useState(false);
  const [canManageVideos, setCanManageVideos] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const router = useRouter();

  useEffect(() => {
    const userStr = localStorage.getItem("admin_user");
    if (userStr) {
      const parsedUser = JSON.parse(userStr);
      if (!parsedUser.is_superuser) {
        router.push("/");
        return;
      }
      setCurrentUser(parsedUser);
    }
  }, [router]);

  // Fetch when page or search changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAdmins(page, search);
    }, 300);
    return () => clearTimeout(timer);
  }, [page, search]);

  // Reset page when search changes
  useEffect(() => {
    setPage(1);
  }, [search]);

  const fetchAdmins = async (pageNum: number, searchQuery: string) => {
    try {
      setLoading(true);
      const queryParams = new URLSearchParams({
        page: pageNum.toString()
      });
      if (searchQuery) queryParams.append('search', searchQuery);

      const response = await apiClient.get(`/admin/staff/?${queryParams.toString()}`);
      
      if (response.data.results !== undefined) {
        setAdmins(response.data.results);
        setTotalPages(Math.ceil(response.data.count / 50)); // matches PAGE_SIZE
      } else {
        setAdmins(response.data);
        setTotalPages(1);
      }
    } catch (error) {
      console.error("Failed to fetch admins", error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEmail || !newUsername || !newPassword) return;
    
    try {
      await apiClient.post(`/admin/staff/create/`, {
        email: newEmail,
        username: newUsername,
        password: newPassword,
        is_superuser: isSuperuser,
        admin_permissions: {
          can_manage_users: canManageUsers,
          can_manage_videos: canManageVideos
        }
      });
      alert(`New Admin account for ${newEmail} successfully created!`);
      setNewEmail("");
      setNewUsername("");
      setNewPassword("");
      setIsSuperuser(false);
      setCanManageUsers(false);
      setCanManageVideos(false);
      setIsModalOpen(false);
      fetchAdmins(page, search); // Refresh the list
    } catch (error: any) {
      alert(error.response?.data?.error || "Failed to create admin.");
    }
  };

  const togglePermission = async (adminId: number, field: string, value: boolean) => {
    try {
      let payload = {};
      if (field === 'is_superuser') {
        payload = { is_superuser: value };
      } else if (field === 'can_manage_users') {
        payload = { admin_permissions: { can_manage_users: value } };
      } else if (field === 'can_manage_videos') {
        payload = { admin_permissions: { can_manage_videos: value } };
      }
      
      await apiClient.patch(`/admin/staff/${adminId}/permissions/`, payload);
      
      // Update local state without full refetch
      setAdmins(prev => prev.map(a => {
        if (a.id === adminId) {
          if (field === 'is_superuser') return { ...a, is_superuser: value };
          if (field === 'can_manage_users') return { ...a, admin_permissions: { ...a.admin_permissions, can_manage_users: value } };
          if (field === 'can_manage_videos') return { ...a, admin_permissions: { ...a.admin_permissions, can_manage_videos: value } };
        }
        return a;
      }));
    } catch (error: any) {
      alert(error.response?.data?.error || "Failed to update permissions.");
      fetchAdmins(page, search); // Revert on failure
    }
  };

  const deleteAdmin = async (adminId: string) => {
    try {
      await apiClient.delete(`/admin/staff/${adminId}/`);
      setAdmins(prev => prev.filter(admin => admin.id !== adminId));
      setDeleteConfirmId(null);
    } catch (error: any) {
      alert(error.response?.data?.error || "Failed to delete admin.");
      setDeleteConfirmId(null);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-zinc-100">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <MonitorCheck className="w-5 h-5" />
            <span className="text-sm font-semibold tracking-wide uppercase">System Hub</span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">Administration</h1>
          <p className="text-zinc-500">Manage internal staff accounts and system privileges.</p>
        </div>
        
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto mt-4 sm:mt-0">
          <div className="relative w-full sm:w-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
            <Input
              placeholder="Search staff members..."
              className="pl-9 w-full sm:w-[280px] bg-zinc-50/50 border-zinc-200 focus-visible:ring-zinc-900 rounded-full h-10 shadow-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          
          {currentUser?.is_superuser && (
            <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
              <DialogTrigger 
                render={<Button className="bg-zinc-900 hover:bg-zinc-800 text-white rounded-full h-10 px-5 shadow-sm w-full sm:w-auto" />}
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Admin
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px] p-0 overflow-hidden bg-white border-zinc-200 rounded-2xl shadow-xl">
                <div className="px-6 py-6 border-b border-zinc-100 bg-zinc-50/50">
                  <DialogHeader>
                    <div className="flex items-center gap-3 mb-1">
                      <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center text-blue-600">
                        <UserPlus className="w-5 h-5" />
                      </div>
                      <div>
                        <DialogTitle className="text-xl">Provision Admin</DialogTitle>
                        <DialogDescription className="text-xs text-zinc-500">
                          Grant a new user dashboard access
                        </DialogDescription>
                      </div>
                    </div>
                  </DialogHeader>
                </div>

                <div className="px-6 py-6 max-h-[70vh] overflow-y-auto">
                  <form onSubmit={handleCreateAdmin} className="space-y-4">
                    <div className="space-y-3.5">
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-zinc-600 uppercase tracking-wider ml-1">Email</label>
                        <Input
                          type="email"
                          placeholder="colleague@nofaceads.com"
                          value={newEmail}
                          onChange={(e) => setNewEmail(e.target.value)}
                          required
                          className="bg-zinc-50/50 border-zinc-200 focus-visible:ring-blue-500 h-11 rounded-xl"
                        />
                      </div>
                      
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-zinc-600 uppercase tracking-wider ml-1">Username</label>
                        <Input
                          type="text"
                          placeholder="admin_name"
                          value={newUsername}
                          onChange={(e) => setNewUsername(e.target.value)}
                          required
                          className="bg-zinc-50/50 border-zinc-200 focus-visible:ring-blue-500 h-11 rounded-xl"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-zinc-600 uppercase tracking-wider ml-1">Initial Password</label>
                        <Input
                          type="password"
                          placeholder="••••••••"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          required
                          className="bg-zinc-50/50 border-zinc-200 focus-visible:ring-blue-500 h-11 rounded-xl"
                        />
                      </div>
                    </div>

                    {/* Permissions Section */}
                    <div className="pt-2 border-t border-zinc-100 space-y-3">
                      <label className="text-xs font-semibold text-zinc-600 uppercase tracking-wider ml-1">Access Permissions</label>
                      
                      <div className="space-y-2 bg-zinc-50/50 p-3 rounded-xl border border-zinc-200">
                        <label className="flex items-center gap-3 cursor-pointer p-1">
                          <input 
                            type="checkbox" 
                            checked={isSuperuser}
                            onChange={(e) => setIsSuperuser(e.target.checked)}
                            className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-zinc-300"
                          />
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-zinc-900">Super Admin</span>
                            <span className="text-[11px] text-zinc-500">Unrestricted access strictly reserved for founders.</span>
                          </div>
                        </label>
                      </div>

                      {!isSuperuser && (
                        <div className="space-y-2 bg-zinc-50/50 p-3 rounded-xl border border-zinc-200 ml-2 animate-in fade-in slide-in-from-top-2">
                          <label className="flex items-center gap-3 cursor-pointer p-1">
                            <input 
                              type="checkbox" 
                              checked={canManageUsers}
                              onChange={(e) => setCanManageUsers(e.target.checked)}
                              className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-zinc-300"
                            />
                            <span className="text-sm font-medium text-zinc-700">Manage Customers</span>
                          </label>
                          <label className="flex items-center gap-3 cursor-pointer p-1">
                            <input 
                              type="checkbox" 
                              checked={canManageVideos}
                              onChange={(e) => setCanManageVideos(e.target.checked)}
                              className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-zinc-300"
                            />
                            <span className="text-sm font-medium text-zinc-700">Manage Videos</span>
                          </label>
                        </div>
                      )}
                    </div>

                    <div className="pt-2">
                      <Button 
                        type="submit" 
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium h-11 rounded-xl shadow-md shadow-blue-500/10 transition-all hover:shadow-blue-500/20"
                      >
                        Authorize Access
                      </Button>
                    </div>

                    <div className="flex items-start gap-2 mt-4 p-3 bg-amber-50 rounded-xl border border-amber-100/50">
                      <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                      <p className="text-[11px] leading-relaxed text-amber-700/90 font-medium">
                        New staff will not require an email OTP verification. Hand off credentials securely.
                      </p>
                    </div>
                  </form>
                </div>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      <div className="w-full space-y-4">
        {/* Main Table Area */}
        <div className="w-full">
          <div className="bg-white rounded-2xl border border-zinc-200 overflow-hidden shadow-sm">
            <Table>
              <TableHeader className="bg-zinc-50/80 border-b border-zinc-200">
                <TableRow className="hover:bg-transparent">
                  <TableHead className="font-medium text-zinc-500 py-4 pl-6">Core Identity</TableHead>
                  <TableHead className="font-medium text-zinc-500">Access Level</TableHead>
                  <TableHead className="font-medium text-zinc-500 text-right pr-6">Initial Provision</TableHead>
                  {currentUser?.is_superuser && <TableHead className="font-medium text-zinc-500 text-right pr-6">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={currentUser?.is_superuser ? 4 : 3} className="text-center h-48 text-zinc-400">
                      <div className="flex flex-col items-center justify-center gap-3">
                        <div className="w-5 h-5 border-2 border-zinc-300 border-t-zinc-900 rounded-full animate-spin" />
                        Loading staff directory...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : admins.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={currentUser?.is_superuser ? 4 : 3} className="text-center h-48 text-zinc-500">
                      No staff members matching your search.
                    </TableCell>
                  </TableRow>
                ) : (
                  admins.map((admin) => (
                    <TableRow key={admin.id} className="hover:bg-zinc-50/50 transition-colors cursor-default">
                      <TableCell className="py-4 pl-6">
                        <div className="flex flex-col">
                          <span className="font-medium text-zinc-900">{admin.username}</span>
                          <span className="text-sm text-zinc-500">{admin.email}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {currentUser?.is_superuser ? (
                          <div className="flex max-w-md flex-wrap items-center gap-x-5 gap-y-2">
                            <label className="flex items-center gap-2 cursor-pointer group">
                              <input 
                                type="checkbox" 
                                checked={admin.is_superuser} 
                                onChange={(e) => togglePermission(admin.id, 'is_superuser', e.target.checked)} 
                                disabled={currentUser.id === admin.id} 
                                className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed" 
                              />
                              <span className="text-sm font-medium text-zinc-700 group-hover:text-zinc-900 transition-colors">Super Admin</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer group">
                              <input 
                                type="checkbox" 
                                checked={admin.is_superuser || (admin.admin_permissions?.can_manage_users || false)} 
                                disabled={admin.is_superuser} 
                                onChange={(e) => togglePermission(admin.id, 'can_manage_users', e.target.checked)} 
                                className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed" 
                              />
                              <span className={`text-sm font-medium transition-colors ${admin.is_superuser ? 'text-zinc-400' : 'text-zinc-700 group-hover:text-zinc-900'}`}>Manage Customers</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer group">
                              <input 
                                type="checkbox" 
                                checked={admin.is_superuser || (admin.admin_permissions?.can_manage_videos || false)} 
                                disabled={admin.is_superuser} 
                                onChange={(e) => togglePermission(admin.id, 'can_manage_videos', e.target.checked)} 
                                className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-zinc-300 disabled:opacity-50 disabled:cursor-not-allowed" 
                              />
                              <span className={`text-sm font-medium transition-colors ${admin.is_superuser ? 'text-zinc-400' : 'text-zinc-700 group-hover:text-zinc-900'}`}>Manage Videos</span>
                            </label>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            {admin.is_superuser ? (
                              <Badge className="bg-indigo-50 text-indigo-700 border border-indigo-200 px-2.5 py-0.5 rounded-full font-medium shadow-sm">
                                Super Admin
                              </Badge>
                            ) : (
                              <Badge className="bg-zinc-100 text-zinc-700 border border-zinc-200 px-2.5 py-0.5 rounded-full font-medium shadow-sm">
                                Staff Admin
                              </Badge>
                            )}
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-right text-zinc-500 pr-6 text-sm">
                        {new Date(admin.date_joined).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })}
                      </TableCell>
                      {currentUser?.is_superuser && (
                        <TableCell className="text-right pr-4">
                          {currentUser.id !== admin.id && (
                            <>
                              {deleteConfirmId === admin.id ? (
                                <div className="flex items-center justify-end gap-2">
                                  <span className="text-xs text-red-600 font-medium">Delete?</span>
                                  <Button
                                    variant="destructive"
                                    size="sm"
                                    className="h-7 px-3 text-xs rounded-full"
                                    onClick={() => deleteAdmin(admin.id)}
                                  >
                                    Confirm
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-3 text-xs rounded-full text-zinc-500"
                                    onClick={() => setDeleteConfirmId(null)}
                                  >
                                    Cancel
                                  </Button>
                                </div>
                              ) : (
                                <Button 
                                  variant="ghost" 
                                  size="icon" 
                                  onClick={() => setDeleteConfirmId(admin.id)}
                                  className="text-zinc-400 hover:text-red-600 hover:bg-red-50 h-8 w-8 rounded-full"
                                  title="Delete Admin"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              )}
                            </>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          
          {totalPages > 1 && (
            <div className="flex items-center justify-between space-x-2 py-4 px-2">
              <div className="text-sm text-zinc-500 font-medium">
                Page {page} of {totalPages}
              </div>
              <div className="space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="bg-white"
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="bg-white"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
