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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Trash2, Eye, UserCircle } from "lucide-react";

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [currentUser, setCurrentUser] = useState<any>(null);

  const router = useRouter();

  // Route protection
  useEffect(() => {
    const userStr = localStorage.getItem("admin_user");
    if (userStr) {
      const parsedUser = JSON.parse(userStr);
      if (!parsedUser.is_superuser && !parsedUser.admin_permissions?.can_manage_users) {
        router.push("/");
        return;
      }
      setCurrentUser(parsedUser);
    }
  }, [router]);

  // Fetch when page or search changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchUsers(page, search);
    }, 300);
    return () => clearTimeout(timer);
  }, [page, search]);

  // Reset page when search changes
  useEffect(() => {
    setPage(1);
  }, [search]);

  const fetchUsers = async (pageNum: number, searchQuery: string) => {
    try {
      setLoading(true);
      const queryParams = new URLSearchParams({
        page: pageNum.toString()
      });
      if (searchQuery) queryParams.append('search', searchQuery);
      
      const response = await apiClient.get(`/admin/users/?${queryParams.toString()}`);
      
      if (response.data.results !== undefined) {
        setUsers(response.data.results);
        setTotalPages(Math.ceil(response.data.count / 50)); // matches PAGE_SIZE 50
      } else {
        setUsers(response.data);
        setTotalPages(1);
      }
    } catch (error) {
      console.error("Failed to fetch users", error);
    } finally {
      setLoading(false);
    }
  };

  const handlePromote = async (userId: string) => {
    if (!window.confirm("Are you sure you want to promote this user to an Admin?")) return;
    try {
      await apiClient.post(`/admin/users/${userId}/promote/`);
      alert("User successfully promoted to Admin!");
      fetchUsers(page, search);
    } catch (error: any) {
      alert(error.response?.data?.message || "Failed to promote user.");
    }
  };

  const deleteUser = async (userId: string) => {
    if (!window.confirm("Are you sure you want to permanently delete this user? This action cannot be undone.")) return;
    try {
      await apiClient.delete(`/admin/users/${userId}/`);
      setUsers(prev => prev.filter(user => user.id !== userId));
    } catch (error: any) {
      alert(error.response?.data?.error || "Failed to delete user.");
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900">Registered Users</h1>
        <p className="text-sm text-zinc-500">View and search through your standard customer base.</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>User Directory</CardTitle>
            <div className="flex items-center gap-2">
              <Input
                placeholder="Search email or username..."
                className="w-[300px]"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Username</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Auth</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center h-24">
                      Loading users...
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center h-24">
                      No users found.
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <UserCircle className="w-4 h-4 text-zinc-400" />
                          <span>{user.username}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-zinc-500">{user.email}</TableCell>
                      <TableCell>
                        {!user.is_active ? <Badge variant="destructive" className="bg-red-50 text-red-700 hover:bg-red-50 border-red-200">Disabled</Badge> : 
                        !user.is_email_verified && user.auth_provider === 'email' ? <Badge variant="secondary" className="bg-amber-50 text-amber-700 hover:bg-amber-50 border-amber-200">Unverified</Badge> : 
                        <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50 border-emerald-200">Verified</Badge>}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="uppercase text-[10px] text-zinc-500 font-medium">
                          {user.auth_provider || 'email'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-zinc-500 text-sm">
                        {user.last_login ? new Date(user.last_login).toLocaleDateString(undefined, {month: 'short', day: 'numeric', year: 'numeric'}) : 'Never'}
                      </TableCell>
                      <TableCell className="text-zinc-500 text-sm">
                        {new Date(user.date_joined).toLocaleDateString(undefined, {month: 'short', day: 'numeric', year: 'numeric'})}
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          onClick={() => router.push(`/users/${user.id}`)}
                          className="text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 h-8 w-8 rounded-full mr-1"
                          title="View Details"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {currentUser?.is_superuser && (
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            onClick={() => deleteUser(user.id)}
                            className="text-zinc-400 hover:text-red-600 hover:bg-red-50 h-8 w-8 rounded-full"
                            title="Delete User"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </TableCell>
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
        </CardContent>
      </Card>
    </div>
  );
}
