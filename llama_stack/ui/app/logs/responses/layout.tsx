"use client";

import React from "react";
import { usePathname, useParams } from "next/navigation";
import {
  PageBreadcrumb,
  BreadcrumbSegment,
} from "@/components/layout/page-breadcrumb";
import { truncateText } from "@/lib/truncate-text";

export default function ResponsesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const params = useParams();

  let segments: BreadcrumbSegment[] = [];

  // Default for /logs/responses
  if (pathname === "/logs/responses") {
    segments = [{ label: "Responses" }];
  }

  // For /logs/responses/[id]
  const idParam = params?.id;
  if (idParam && typeof idParam === "string") {
    segments = [
      { label: "Responses", href: "/logs/responses" },
      { label: `Details (${truncateText(idParam, 20)})` },
    ];
  }

  return (
    <div className="container mx-auto p-4">
      <>
        {segments.length > 0 && (
          <PageBreadcrumb segments={segments} className="mb-4" />
        )}
        {children}
      </>
    </div>
  );
}
