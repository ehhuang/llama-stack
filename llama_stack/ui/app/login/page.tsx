"use client";

import React from "react";
import { useAuth } from "@/contexts/auth-context";
import { LoginButton } from "@/components/auth/login-button";
import { GitHubIcon } from "@/components/icons/github-icon";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { LucideIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

interface AuthProvider {
  id: string;
  name: string;
  icon: LucideIcon;
  loginPath: string;
  buttonColor?: string;
}

// Define available auth providers
// Easy to extend with Google, Microsoft, etc.
const authProviders: AuthProvider[] = [
  {
    id: "github",
    name: "GitHub",
    icon: GitHubIcon as LucideIcon,
    loginPath: "/api/auth/github/login",
    buttonColor: "bg-gray-900 hover:bg-gray-800 text-white",
  },
  // Future providers can be added here:
  // {
  //   id: 'google',
  //   name: 'Google',
  //   icon: GoogleIcon,
  //   loginPath: '/api/auth/google/login',
  //   buttonColor: 'bg-blue-600 hover:bg-blue-700 text-white',
  // },
];

export default function LoginPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const error = searchParams.get("error");

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Welcome to Llama Stack
          </CardTitle>
          <CardDescription className="text-center">
            {error === "auth_not_configured"
              ? "Authentication is not configured on this server"
              : "Sign in to access your logs and resources"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error !== "auth_not_configured" && (
            <>
              {authProviders.length > 1 && (
                <>
                  <div className="text-sm text-muted-foreground text-center">
                    Continue with
                  </div>
                  <Separator />
                </>
              )}

              <div className="space-y-2">
                {authProviders.map((provider) => (
                  <LoginButton key={provider.id} provider={provider} />
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
