import React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface LoginButtonProps {
  provider: {
    id: string;
    name: string;
    icon: LucideIcon;
    loginPath: string;
    buttonColor?: string;
  };
  className?: string;
}

export function LoginButton({ provider, className }: LoginButtonProps) {
  const handleLogin = async () => {
    try {
      // Try to fetch the auth endpoint first to check if it exists
      const response = await fetch(provider.loginPath, {
        method: "HEAD",
        redirect: "manual",
      });

      // If we get a redirect response (302/307) or OK, auth is configured
      if (
        response.type === "opaqueredirect" ||
        response.ok ||
        response.status === 302 ||
        response.status === 307
      ) {
        window.location.href = provider.loginPath;
      } else {
        // Auth endpoint doesn't exist or returned an error
        window.location.href = "/login?error=auth_not_configured";
      }
    } catch (error) {
      // Network error or auth not configured
      window.location.href = "/login?error=auth_not_configured";
    }
  };

  const Icon = provider.icon;

  return (
    <Button
      onClick={handleLogin}
      className={cn(
        "w-full flex items-center justify-center gap-3",
        provider.buttonColor || "bg-gray-900 hover:bg-gray-800",
        className,
      )}
    >
      <Icon className="h-5 w-5" />
      <span>Continue with {provider.name}</span>
    </Button>
  );
}
