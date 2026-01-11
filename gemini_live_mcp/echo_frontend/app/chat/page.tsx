"use client";

import { useState, useEffect } from 'react';
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AppSidebar } from "../components/AppSidebar";
import { ClassroomAuthPrompt } from "../components/ClassroomAuthPrompt";
import { useClassroomAuth } from "../hooks/useClassroomAuth";
import { Loader } from "@/components/ui/loader";
import ChatInterface from "../ChatInterface";
import { SidebarProvider, SidebarInset, useSidebar } from "@/components/ui/sidebar";

function ChatContent() {
  const { hasTokens, loading: checkingTokens } = useClassroomAuth();
  const [showPrompt, setShowPrompt] = useState(true);
  const { setOpen, state } = useSidebar();

  // Handle hover to expand sidebar
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Expand sidebar when mouse is within 80px of left edge (hovering over collapsed sidebar)
      if (e.clientX <= 80) {
        setOpen(true);
      }
      // Collapse sidebar when mouse moves away (beyond 280px from left)
      else if (e.clientX > 280) {
        setOpen(false);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [setOpen]);

  return (
        <SidebarInset>
          <div className="flex h-screen flex-col">
        {/* Main Content */}
        <div className="flex-1 relative">
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
  );
}

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <SidebarProvider defaultOpen={false} style={{ "--sidebar-width": "16rem" } as React.CSSProperties}>
        <AppSidebar />
        <ChatContent />
      </SidebarProvider>
    </ProtectedRoute>
  );
}

