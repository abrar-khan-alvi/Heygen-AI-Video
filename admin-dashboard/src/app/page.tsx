"use client";

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, DollarSign, Video, PlayCircle, AlertTriangle } from "lucide-react";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell, Legend
} from "recharts";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await apiClient.get("/admin/stats/dashboard/");
        setStats(response.data);
      } catch (error) {
        console.error("Failed to fetch dashboard stats", error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 h-full">
        <div className="text-slate-500 animate-pulse">Loading dashboard statistics...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-bold text-red-600 mb-4">Error loading data</h1>
        <p>Could not connect to the backend API. Ensure the Django server is running.</p>
      </div>
    );
  }

  const { overview, charts } = stats;

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard Overview</h1>
        <p className="text-muted-foreground mt-1">High-level metrics for BackendGen.</p>
      </div>

      {overview.failed_videos > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Attention Needed</AlertTitle>
          <AlertDescription>
            There are {overview.failed_videos} failed video generation tasks in the system. Please check the Videos queue for details.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Approx. MRR</CardTitle>
            <DollarSign className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${overview.approximate_mrr}</div>
            <p className="text-xs text-muted-foreground">
              {overview.active_paid_subscriptions} active paid subscriptions
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.total_users}</div>
            <p className="text-xs text-muted-foreground">
              +{overview.new_users_30d} in the last 30 days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Free Trials</CardTitle>
            <PlayCircle className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.active_trial_subscriptions}</div>
            <p className="text-xs text-muted-foreground">
              Users currently on lifetime trial
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-medium">Videos Completed</CardTitle>
            <Video className="w-4 h-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.completed_videos}</div>
            <p className="text-xs text-muted-foreground">
              +{overview.completed_videos_30d} in the last 30 days
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Signups (Last 30 Days)</CardTitle>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[300px] min-h-[300px] w-full">
              {charts.signups_by_day.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={charts.signups_by_day}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      tickLine={false} 
                      axisLine={false} 
                      tickFormatter={(value) => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric'})}
                    />
                    <YAxis 
                      tickLine={false} 
                      axisLine={false} 
                      tickFormatter={(value) => `${value}`}
                    />
                    <RechartsTooltip cursor={{fill: 'transparent'}} />
                    <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">
                  No signup data available for the last 30 days.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Subscriptions By Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] min-h-[300px] w-full">
              {charts.subscriptions_by_plan && charts.subscriptions_by_plan.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={charts.subscriptions_by_plan}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {charts.subscriptions_by_plan.map((entry: any, index: number) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip formatter={(value) => [`${value} users`, 'Count']} />
                    <Legend verticalAlign="bottom" height={36}/>
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">
                  No subscription data available.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-7 mt-4">
        <Card className="col-span-1 lg:col-span-7">
          <CardHeader>
            <CardTitle>Videos Generated</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] min-h-[300px] w-full">
              {charts.videos_by_day.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={charts.videos_by_day}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      tickLine={false} 
                      axisLine={false} 
                      tickFormatter={(value) => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric'})}
                    />
                    <YAxis tickLine={false} axisLine={false} />
                    <RechartsTooltip />
                    <Line 
                      type="monotone" 
                      dataKey="count" 
                      stroke="#8b5cf6" 
                      strokeWidth={2} 
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500">
                  No video data available for the last 30 days.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
