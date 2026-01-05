"use client";

import { useState } from 'react';
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AppSidebar } from "../components/AppSidebar";
import { ClassroomAuthPrompt } from "../components/ClassroomAuthPrompt";
import { useClassroomAuth } from "../hooks/useClassroomAuth";
import { Loader } from "@/components/ui/loader";
import ChatInterface from "../ChatInterface";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";

export const dynamic = 'force-dynamic';

export default function ChatPage() {
  const { hasTokens, loading: checkingTokens } = useClassroomAuth();
  const [showPrompt, setShowPrompt] = useState(true);

  return (
    <ProtectedRoute>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <div className="flex h-screen flex-col">
            {/* Minimal header with just the toggle button */}
            <div className="flex h-12 shrink-0 items-center px-4">
              <SidebarTrigger />
            </div>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {checkingTokens ? (
            <div className="flex items-center justify-center h-full">
              <Loader variant="circular" size="lg" />
            </div>
          ) : !hasTokens && showPrompt ? (
            <div className="flex items-center justify-center h-full p-6">
              <ClassroomAuthPrompt
                onSuccess={() => setShowPrompt(false)}
                onSkip={() => setShowPrompt(false)}
              />
            </div>
          ) : (
            <ChatInterface />
          )}
        </div>
      </div>
        </SidebarInset>
      </SidebarProvider>
    </ProtectedRoute>
  );
}

