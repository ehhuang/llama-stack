import Link from 'next/link';
import React from 'react';

export function Header() {
  return (
    <header className="flex items-center h-full px-4">
      <Link href="/" className="text-xl font-semibold hover:text-primary">
        Llama Stack
      </Link>
    </header>
  );
} 