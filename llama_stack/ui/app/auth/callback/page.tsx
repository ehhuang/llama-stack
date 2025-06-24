"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { AuthResponse } from "@/lib/auth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const processCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const errorParam = searchParams.get("error");

      if (errorParam) {
        setError(errorParam);
        setIsProcessing(false);
        return;
      }

      if (!code || !state) {
        setError("Missing required parameters");
        setIsProcessing(false);
        return;
      }

      try {
        const callbackUrl = `/api/auth/github/callback?code=${code}&state=${state}`;
        const response = await fetch(callbackUrl);

        if (response.ok) {
          const data: AuthResponse = await response.json();
          login(data);
        } else {
          const errorData = await response.json();
          setError(errorData.detail || "Authentication failed");
        }
      } catch (err) {
        console.error("Auth callback error:", err);
        setError("An error occurred during authentication");
      } finally {
        setIsProcessing(false);
      }
    };

    processCallback();
  }, [searchParams, login]);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Authentication Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/login")} className="w-full">
              Back to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Authenticating...</CardTitle>
          <CardDescription>
            Please wait while we complete your login.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </CardContent>
      </Card>
    </div>
  );
}
