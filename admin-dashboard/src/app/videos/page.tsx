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
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button"; // Added Button import
import { Search, Film, Clock, Eye } from "lucide-react";

export default function VideosPage() {
  const [videos, setVideos] = useState<any[]>([]);
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
      if (!parsedUser.is_superuser && !parsedUser.admin_permissions?.can_manage_videos) {
        router.push("/");
        return;
      }
      setCurrentUser(parsedUser);
    }
  }, [router]);

  // Fetch when page or search changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchVideos(page, search);
    }, 300);
    return () => clearTimeout(timer);
  }, [page, search]);

  // Reset page when search changes
  useEffect(() => {
    setPage(1);
  }, [search]);

  const fetchVideos = async (pageNum: number, searchQuery: string) => {
    try {
      setLoading(true);
      const queryParams = new URLSearchParams({
        page: pageNum.toString()
      });
      if (searchQuery) queryParams.append('search', searchQuery);

      const response = await apiClient.get(`/admin/videos/?${queryParams.toString()}`);
      
      if (response.data.results !== undefined) {
        setVideos(response.data.results);
        setTotalPages(Math.ceil(response.data.count / 50)); // matches PAGE_SIZE
      } else {
        setVideos(response.data);
        setTotalPages(1);
      }
    } catch (error) {
      console.error("Failed to fetch videos", error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "video_completed": return <Badge className="bg-green-600">Completed</Badge>;
      case "video_processing": return <Badge className="bg-blue-600 animate-pulse">Processing</Badge>;
      case "video_failed": return <Badge variant="destructive">Failed</Badge>;
      case "draft": return <Badge variant="secondary">Draft</Badge>;
      default: return <Badge variant="outline">{status.replace("_", " ")}</Badge>;
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Videos</h1>
          <p className="text-muted-foreground mt-1">Monitor all video generation tasks across the platform.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Global Video Queue</CardTitle>
            <div className="flex items-center gap-2">
              <Input
                placeholder="Search title or user email..."
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
                  <TableHead>Title</TableHead>
                  <TableHead>User Email</TableHead>
                  <TableHead>Industry</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center h-24">
                      Loading videos...
                    </TableCell>
                  </TableRow>
                ) : videos.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center h-24">
                      No videos found.
                    </TableCell>
                  </TableRow>
                ) : (
                  videos.map((video) => (
                    <TableRow key={video.id}>
                      <TableCell className="font-medium">{video.title || "Untitled"}</TableCell>
                      <TableCell>{video.user_email}</TableCell>
                      <TableCell>{video.industry || "-"}</TableCell>
                      <TableCell>{getStatusBadge(video.status)}</TableCell>
                      <TableCell>{new Date(video.created_at).toLocaleString()}</TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          onClick={() => router.push(`/videos/${video.id}`)}
                          className="text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 h-8 w-8 rounded-full ml-auto"
                          title="View Details"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
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
