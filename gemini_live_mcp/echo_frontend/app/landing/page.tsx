"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import { Button } from "@/components/ui/button";
import { Sparkles, MessageSquare, Zap, Download } from "lucide-react";
import Image from "next/image";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user && !loading) {
      router.push('/');
    }
  }, [user, loading, router]);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <Image
                src="/logo.png"
                alt="Echo Logo"
                width={40}
                height={40}
                className="rounded-lg"
              />
              <span className="text-xl font-semibold text-gray-900">Echo</span>
            </div>
            <Button
              onClick={() => router.push('/login')}
              variant="ghost"
              className="text-gray-700 hover:text-gray-900 hover:bg-gray-50"
            >
              Sign in
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 tracking-tight">
            Your AI-powered
            <br />
            classroom assistant
          </h1>
          <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed">
            Manage assignments, create courses, and interact with Google Classroom using natural language. Powered by Gemini AI.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Button
              onClick={() => router.push('/login')}
              size="lg"
              className="bg-gray-900 hover:bg-gray-800 text-white px-8 py-6 text-lg rounded-xl"
            >
              Get Started
            </Button>
            <Button
              onClick={() => router.push('/learn-more')}
              variant="outline"
              size="lg"
              className="border-gray-300 text-gray-700 hover:bg-gray-50 px-8 py-6 text-lg rounded-xl"
            >
              Learn More
            </Button>
            <Button
              onClick={() => router.push('/download')}
              variant="outline"
              size="lg"
              className="border-purple-300 text-purple-700 hover:bg-purple-50 px-8 py-6 text-lg rounded-xl"
            >
              <Download className="w-5 h-5 mr-2" />
              Download Desktop
            </Button>
          </div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-8 mt-20">
            <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
              <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mx-auto mb-4 border border-gray-200">
                <MessageSquare className="w-6 h-6 text-gray-900" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Natural Conversations</h3>
              <p className="text-gray-600 text-sm">
                Chat naturally to create assignments, manage courses, and get classroom insights.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
              <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mx-auto mb-4 border border-gray-200">
                <Zap className="w-6 h-6 text-gray-900" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Instant Actions</h3>
              <p className="text-gray-600 text-sm">
                Create assignments and courses with intuitive forms, powered by AI understanding.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
              <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center mx-auto mb-4 border border-gray-200">
                <Sparkles className="w-6 h-6 text-gray-900" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Google Classroom Integration</h3>
              <p className="text-gray-600 text-sm">
                Seamlessly connected to your Google Classroom for real-time updates.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            © 2025 Echo. Powered by Gemini AI.
          </p>
        </div>
      </footer>
    </div>
  );
}

