"use client"; // Required for client-side components

import React from 'react';

export default function Home() {
  return (
    <main className="container mx-auto py-10">
      <h1 className="text-3xl font-bold mb-6">Welcome!</h1>
      <p className="text-lg">
        This is the home page of the Llama Stack UI. Use the sidebar to navigate to different sections.
      </p>
    </main>
  );
}
