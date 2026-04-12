"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ArrowLeft, Video, User, FileText, Cpu, Image as ImageIcon,
  Calendar, Clock, Hash, Globe, CheckCircle, AlertCircle,
  Film, Layers, Mic, Copy, ExternalLink
} from "lucide-react";

function DetailRow({ label, value, mono = false, full = false }: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  full?: boolean;
}) {
  if (!value && value !== 0) return null;
  return (
    <div className={`flex flex-col gap-1 ${full ? "col-span-2" : ""}`}>
      <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">{label}</span>
      <span className={`text-sm text-zinc-800 break-words ${mono ? "font-mono bg-zinc-50 px-2 py-1 rounded-md border border-zinc-100 text-xs" : ""}`}>
        {value}
      </span>
    </div>
  );
}

function ScriptBlock({ label, content }: { label: string; content: string }) {
  const [copied, setCopied] = useState(false);
  if (!content) return null;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">{label}</span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-xs text-zinc-500"
          onClick={() => {
            navigator.clipboard.writeText(content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          }}
        >
          <Copy className="w-3 h-3 mr-1" />
          {copied ? "Copied!" : "Copy"}
        </Button>
      </div>
      <pre className="text-sm text-zinc-700 bg-zinc-50 border border-zinc-100 rounded-xl p-4 whitespace-pre-wrap leading-relaxed font-sans max-h-72 overflow-y-auto">
        {content}
      </pre>
    </div>
  );
}

function getStatusBadge(status: string) {
  switch (status) {
    case "video_completed":    return <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">Completed</Badge>;
    case "video_processing":   return <Badge className="bg-blue-100 text-blue-700 border-blue-200 animate-pulse">Processing</Badge>;
    case "video_failed":       return <Badge className="bg-red-100 text-red-700 border-red-200">Failed</Badge>;
    case "draft":              return <Badge className="bg-zinc-100 text-zinc-600 border-zinc-200">Draft</Badge>;
    case "script_generated":   return <Badge className="bg-amber-100 text-amber-700 border-amber-200">Script Generated</Badge>;
    case "script_finalized":   return <Badge className="bg-purple-100 text-purple-700 border-purple-200">Script Finalized</Badge>;
    default:                   return <Badge variant="outline">{status.replace(/_/g, " ")}</Badge>;
  }
}

export default function VideoDetailPage() {
  const [video, setVideo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;

  useEffect(() => {
    if (!id) return;
    apiClient.get(`/admin/videos/${id}/`)
      .then((res) => setVideo(res.data))
      .catch(() => router.push("/videos"))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-6 h-6 border-2 border-zinc-300 border-t-zinc-900 rounded-full animate-spin" />
      </div>
    );
  }

  if (!video) return null;

  const isCompleted = video.status === "video_completed";
  // Only use the locally-stored video file — no HeyGen CDN URL
  const playableUrl = video.video_file_url || null;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Button
            variant="ghost"
            size="sm"
            className="text-zinc-500 hover:text-zinc-900 -ml-2 mb-1"
            onClick={() => router.back()}
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <h1 className="text-2xl font-bold text-zinc-900">{video.title || "Untitled Project"}</h1>
          <div className="flex items-center gap-2 flex-wrap">
            {getStatusBadge(video.status)}
            {video.industry && (
              <Badge variant="outline" className="text-zinc-500 font-normal">{video.industry}</Badge>
            )}
          </div>
        </div>
        {playableUrl && (
          <a href={playableUrl} target="_blank" rel="noreferrer">
            <Button className="bg-zinc-900 hover:bg-zinc-700 text-white gap-2">
              <ExternalLink className="w-4 h-4" /> Open Video
            </Button>
          </a>
        )}
      </div>

      {/* Video Player — only uses the locally-stored file */}
      {isCompleted && playableUrl && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-semibold text-zinc-600"><Film className="w-4 h-4" /> Video File</CardTitle>
          </CardHeader>
          <CardContent>
            <video controls className="w-full rounded-xl max-h-96 bg-black" src={playableUrl} />
          </CardContent>
        </Card>
      )}

      {/* Status message if failed */}
      {video.video_status_message && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-100">
          <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-700">Status Message</p>
            <p className="text-sm text-red-600 mt-0.5">{video.video_status_message}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">

          {/* Project Details */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-zinc-600">
                <Layers className="w-4 h-4" /> Project Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <DetailRow label="Project ID" value={video.id} mono />
                <DetailRow label="HeyGen Video ID" value={video.heygen_video_id || "—"} mono />
                <DetailRow label="Industry" value={video.industry || "—"} />
                <DetailRow label="Background" value={video.background || "—"} />
                <DetailRow label="Service Description" value={video.service_description || "—"} full />
              </div>
            </CardContent>
          </Card>

          {/* Avatar Details */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-zinc-600">
                <ImageIcon className="w-4 h-4" /> Avatar Configuration
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {video.avatar_preview_url && (
                  <div className="col-span-2 flex items-center gap-4 p-3 bg-zinc-50 rounded-xl border border-zinc-100">
                    <img
                      src={video.avatar_preview_url}
                      alt={video.avatar_name}
                      className="w-16 h-16 object-cover rounded-lg border border-zinc-200"
                    />
                    <div className="flex flex-col gap-1">
                      <span className="font-semibold text-zinc-900">{video.avatar_name || "Unknown"}</span>
                      <span className="text-xs text-zinc-500 capitalize">{video.avatar_gender} · {video.avatar_outfit}</span>
                    </div>
                  </div>
                )}
                <DetailRow label="Avatar ID" value={video.avatar_id || "—"} mono />
                <DetailRow label="Avatar Name" value={video.avatar_name || "—"} />
                <DetailRow label="Gender" value={video.avatar_gender ? <span className="capitalize">{video.avatar_gender}</span> : "—"} />
                <DetailRow label="Outfit" value={video.avatar_outfit || "—"} />
                <DetailRow label="Preview Image URL" value={video.avatar_preview_url ? (
                  <a href={video.avatar_preview_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline truncate block max-w-xs">{video.avatar_preview_url}</a>
                ) : "—"} />
                <DetailRow label="Preview Video URL" value={video.avatar_preview_video_url ? (
                  <a href={video.avatar_preview_video_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline truncate block max-w-xs">{video.avatar_preview_video_url}</a>
                ) : "—"} />
              </div>
            </CardContent>
          </Card>

          {/* Scripts */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-zinc-600">
                <FileText className="w-4 h-4" /> Scripts
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <ScriptBlock label="Generated Script (AI Draft)" content={video.generated_script} />
              <ScriptBlock label="Finalized Script (User Edited)" content={video.finalized_script} />
              {!video.generated_script && !video.finalized_script && (
                <p className="text-sm text-zinc-400 italic">No scripts generated yet.</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* Owner */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-zinc-600">
                <User className="w-4 h-4" /> Owner
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <DetailRow label="User ID" value={video.user_id} mono />
              <DetailRow label="Email" value={video.user_email || "—"} />
              <DetailRow label="Username" value={video.user_username || "—"} />
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-2 text-xs"
                onClick={() => router.push(`/users/${video.user_id}`)}
              >
                View User Profile →
              </Button>
            </CardContent>
          </Card>

          {/* Timestamps */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-zinc-600">
                <Calendar className="w-4 h-4" /> Timestamps
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <DetailRow
                label="Created At"
                value={new Date(video.created_at).toLocaleString(undefined, {
                  dateStyle: "medium", timeStyle: "short"
                })}
              />
              <DetailRow
                label="Last Updated"
                value={new Date(video.updated_at).toLocaleString(undefined, {
                  dateStyle: "medium", timeStyle: "short"
                })}
              />
            </CardContent>
          </Card>

          {/* Video Output */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold text-zinc-600">
                <Video className="w-4 h-4" /> Video Output
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Status</span>
                {getStatusBadge(video.status)}
              </div>
              <DetailRow label="HeyGen Job ID" value={video.heygen_video_id || "—"} mono />
              <DetailRow label="Video File" value={video.video_file_url ? (
                <a href={video.video_file_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline text-xs break-all">{video.video_file_url}</a>
              ) : "—"} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
