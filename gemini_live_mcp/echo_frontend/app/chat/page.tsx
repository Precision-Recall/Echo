"use client";

import { useState } from 'react';
import { ProtectedRoute } from "../components/ProtectedRoute";
import { UserMenu } from "../components/UserMenu";
import { ClassroomAuthPrompt } from "../components/ClassroomAuthPrompt";
import { useClassroomAuth } from "../hooks/useClassroomAuth";
import { Loader } from "@/components/ui/loader";
import ChatInterface from "../ChatInterface";

export default function ChatPage() {
  const { hasTokens, loading: checkingTokens } = useClassroomAuth();
  const [showPrompt, setShowPrompt] = useState(true);

  return (
    <ProtectedRoute>
      <div className="flex flex-col h-screen bg-white">
        {/* Header with User Menu */}
        <header className="border-b border-gray-200 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">E</span>
                </div>
                <span className="text-xl font-semibold text-gray-900">Echo</span>
              </div>
              <UserMenu />
            </div>
          </div>
        </header>

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
    </ProtectedRoute>
  );
}

