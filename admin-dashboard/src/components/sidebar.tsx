"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Users, LayoutDashboard, Video, LogOut, ShieldCheck, UserCircle } from "lucide-react";
import { useEffect, useState } from "react";

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const userData = localStorage.getItem("admin_user");
    if (userData) {
      setUser(JSON.parse(userData));
    } else if (pathname !== "/login") {
      router.push("/login"); // Protect routes
    }
  }, [pathname, router]);

  const handleLogout = () => {
    localStorage.removeItem("admin_access_token");
    localStorage.removeItem("admin_refresh_token");
    localStorage.removeItem("admin_user");
    document.cookie = "is_admin_logged_in=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    router.push("/login");
  };

  if (!mounted) return null;
  if (pathname === "/login") return null;

  const links = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Users", href: "/users", icon: Users },
    { name: "Administration", href: "/administration", icon: ShieldCheck },
    { name: "Videos", href: "/videos", icon: Video },
    { name: "My Profile", href: "/profile", icon: UserCircle },
  ];

  return (
    <div className="flex flex-col w-64 h-screen border-r bg-white">
      <div className="flex items-center justify-center p-6 border-b gap-3">
        <img src="/logo.png" alt="No Face ADS Logo" className="w-8 h-8 rounded-md object-cover" />
        <h2 className="text-xl font-bold tracking-tight">No Face ADS</h2>
      </div>
      
      <nav className="flex-1 p-4 flex flex-col gap-2">
        {links.map((link) => {
          if (!user?.is_superuser) {
            if (link.name === "Administration") return null;
            if (link.name === "Users" && !user?.admin_permissions?.can_manage_users) return null;
            if (link.name === "Videos" && !user?.admin_permissions?.can_manage_videos) return null;
          }

          const Icon = link.icon;
          const isActive = pathname === link.href;
          
          return (
            <Link
              key={link.name}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
                isActive 
                  ? "bg-slate-100 text-slate-900 font-medium" 
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Icon className="w-5 h-5" />
              {link.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t">
        {user && (
          <div className="mb-4">
            <p className="text-sm font-medium">{user.username}</p>
            <p className="text-xs text-slate-500">{user.email}</p>
            {user.is_superuser && (
              <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-semibold bg-blue-100 text-blue-700 rounded-full">
                Superadmin
              </span>
            )}
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 text-red-600 rounded-md hover:bg-red-50 transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Logout
        </button>
      </div>
    </div>
  );
}
