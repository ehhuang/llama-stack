'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const navItems = [
  { href: "/chat_completions", label: "Chat Completions" },
  { href: "/responses", label: "Responses" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="h-full p-4 space-y-4">
      <div>
        <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
          Logs
        </h2>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block px-4 py-2 text-sm text-muted-foreground hover:text-primary",
                pathname === item.href && "text-primary bg-muted"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
} 