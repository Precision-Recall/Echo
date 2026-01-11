"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/app/contexts/AuthContext';
import { ProtectedRoute } from '@/app/components/ProtectedRoute';
import { SidebarProvider, useSidebar } from "@/components/ui/sidebar";
import { AppSidebar } from "@/app/components/AppSidebar";
import { SidebarInset } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Sparkles, History } from "lucide-react";
import { FormsHistory } from "@/app/components/FormsHistory";

function FormsContentWrapper() {
  const { setOpen } = useSidebar();

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
      <FormsContent />
    </SidebarInset>
  );
}

export default function FormsPage() {
  return (
    <ProtectedRoute>
      <SidebarProvider defaultOpen={false} style={{ "--sidebar-width": "16rem" } as React.CSSProperties}>
        <AppSidebar />
        <FormsContentWrapper />
      </SidebarProvider>
    </ProtectedRoute>
  );
}

function FormsContent() {
  const { user } = useAuth();
  const [formTopic, setFormTopic] = useState("");
  const [numQuestions, setNumQuestions] = useState("5");
  const [questionType, setQuestionType] = useState("MIXED");
  const [isCreating, setIsCreating] = useState(false);
  const [formId, setFormId] = useState<string | null>(null);
  const [formHistoryId, setFormHistoryId] = useState<string | null>(null);
  const [embedUrl, setEmbedUrl] = useState<string | null>(null);
  const [editUrl, setEditUrl] = useState<string | null>(null);
  const [viewUrl, setViewUrl] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<Array<{role: string, content: string}>>([]);
  const [chatInput, setChatInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || 'http://localhost:8001';

  const saveMessageToHistory = async (role: string, content: string) => {
    if (!formHistoryId || !user?.email) return;
    
    try {
      await fetch(
        `${TOKEN_SERVICE_URL}/api/forms/${formHistoryId}/messages?email=${encodeURIComponent(user.email)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role, content }),
        }
      );
    } catch (error) {
      console.error('Error saving message to history:', error);
    }
  };

  const handleLoadFormFromHistory = async (form: any) => {
    if (!user?.email) return;
    
    try {
      // Fetch full form details with chat history
      const response = await fetch(
        `${TOKEN_SERVICE_URL}/api/forms/${form.id}?email=${encodeURIComponent(user.email)}`
      );
      
      if (response.ok) {
        const formDetail = await response.json();
        
        // Load form data
        setFormId(formDetail.form_id);
        setFormHistoryId(formDetail.id);
        setEmbedUrl(formDetail.embed_url);
        setEditUrl(formDetail.edit_url);
        setViewUrl(formDetail.view_url);
        
        // Load chat messages
        const messages = formDetail.chat_messages.map((msg: any) => ({
          role: msg.role,
          content: msg.content,
        }));
        setChatMessages(messages);
      }
    } catch (error) {
      console.error('Error loading form from history:', error);
    }
  };

  const handleCreateForm = async () => {
    if (!formTopic.trim() || !user?.email) return;

    setIsCreating(true);
    try {
      // Get Firebase token
      const idToken = await user.getIdToken();
      
      const response = await fetch('http://localhost:8000/api/forms/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`,
          'X-User-Email': user.email,
        },
        body: JSON.stringify({
          topic: formTopic,
          num_questions: parseInt(numQuestions),
          question_type: questionType,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setFormId(data.form_id);
        setFormHistoryId(data.form_history_id); // Save form history ID
        setEmbedUrl(data.embed_url);
        setEditUrl(data.edit_url);
        setViewUrl(data.view_url);
        setChatMessages([{
          role: 'assistant',
          content: `✅ Form created successfully! You can now edit it using the chat or click "Edit in Google Forms" to open the full editor.`
        }]);
      } else {
        const errorData = await response.json();
        alert(`Failed to create form: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Error creating form:', error);
      alert('Error creating form');
    } finally {
      setIsCreating(false);
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !formId || !user?.email) return;

    const userMessage = chatInput;
    setChatInput("");
    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsProcessing(true);
    
    // Save user message to history (non-blocking)
    if (formHistoryId) {
      saveMessageToHistory('user', userMessage).catch(console.error);
    }
    
    // Add processing message
    setChatMessages(prev => [...prev, { role: 'assistant', content: 'Processing your request...' }]);

    try {
      // Get Firebase token
      const idToken = await user.getIdToken();
      
      const response = await fetch('http://localhost:8000/api/forms/edit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`,
          'X-User-Email': user.email,
        },
        body: JSON.stringify({
          form_id: formId,
          instruction: userMessage,
          form_history_id: formHistoryId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const assistantMessage = data.message;
        
        // Remove processing message and add success message
        setChatMessages(prev => {
          const filtered = prev.filter(msg => msg.content !== 'Processing your request...');
          return [...filtered, { role: 'assistant', content: assistantMessage }];
        });
        
        // Save assistant message to history (non-blocking)
        if (formHistoryId) {
          saveMessageToHistory('assistant', assistantMessage).catch(console.error);
        }
        
        // Reload iframe to show changes
        const iframe = document.getElementById('form-iframe') as HTMLIFrameElement;
        if (iframe && embedUrl) {
          // Force reload by adding a timestamp
          iframe.src = `${embedUrl}&t=${Date.now()}`;
        }
      } else {
        const errorMessage = '❌ Error editing form';
        // Remove processing message and add error message
        setChatMessages(prev => {
          const filtered = prev.filter(msg => msg.content !== 'Processing your request...');
          return [...filtered, { role: 'assistant', content: errorMessage }];
        });
        
        // Save error message to history (non-blocking)
        if (formHistoryId) {
          saveMessageToHistory('assistant', errorMessage).catch(console.error);
        }
      }
    } catch (error) {
      console.error('Error editing form:', error);
      // Remove processing message and add error message
      setChatMessages(prev => {
        const filtered = prev.filter(msg => msg.content !== 'Processing your request...');
        return [...filtered, { role: 'assistant', content: '❌ Error editing form' }];
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {!formId ? (
        // Form Creation UI
        <div className="flex-1 flex items-center justify-center bg-white p-6">
          {/* History Button - Top Right */}
          <div className="absolute top-4 right-4">
            <Button
              onClick={() => setIsHistoryOpen(true)}
              variant="outline"
              className="flex items-center gap-2"
            >
              <History className="w-4 h-4" />
              History
            </Button>
          </div>

          <div className="w-full max-w-md bg-white border border-gray-200 rounded-xl shadow-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <Sparkles className="w-8 h-8 text-gray-900" />
              <h1 className="text-2xl font-bold text-gray-900">Create Google Form with AI</h1>
            </div>

            <div className="space-y-4">
              <div>
                <Label htmlFor="topic">What is your form about?</Label>
                <Input
                  id="topic"
                  placeholder="e.g., Machine Learning Quiz, Customer Feedback Survey"
                  value={formTopic}
                  onChange={(e) => setFormTopic(e.target.value)}
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="numQuestions">Number of Questions</Label>
                <Select value={numQuestions} onValueChange={setNumQuestions}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[5, 10, 15, 20, 25, 30].map(num => (
                      <SelectItem key={num} value={num.toString()}>{num} questions</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="questionType">Question Type</Label>
                <Select value={questionType} onValueChange={setQuestionType}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MIXED">Mixed (Multiple Choice, Text, etc.)</SelectItem>
                    <SelectItem value="MULTIPLE_CHOICE">Multiple Choice Only</SelectItem>
                    <SelectItem value="TEXT">Short Answer Only</SelectItem>
                    <SelectItem value="PARAGRAPH_TEXT">Paragraph Only</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleCreateForm}
                disabled={isCreating || !formTopic.trim()}
                className="w-full bg-gray-900 hover:bg-gray-800 text-white"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating Form...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Create Form
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      ) : (
        // Split View: Form + Chat
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top Bar with New Form, Share, Edit, and History Buttons */}
          <div className="bg-white border-b px-4 py-3 flex items-center justify-between flex-shrink-0">
            <div>
              <h2 className="text-lg font-semibold">Google Form Preview</h2>
              <p className="text-sm text-gray-600">Live preview of your form</p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={() => {
                  // Reset to create new form
                  setFormId(null);
                  setFormHistoryId(null);
                  setEmbedUrl(null);
                  setEditUrl(null);
                  setViewUrl(null);
                  setChatMessages([]);
                  setFormTopic("");
                }}
                variant="outline"
                className="flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                New Form
              </Button>
              <Button
                onClick={() => setIsHistoryOpen(true)}
                variant="outline"
                className="flex items-center gap-2"
              >
                <History className="w-4 h-4" />
                History
              </Button>
              <Button
                onClick={() => {
                  if (viewUrl) {
                    navigator.clipboard.writeText(viewUrl);
                    alert('Share link copied to clipboard!');
                  }
                }}
                variant="outline"
                className="flex items-center gap-2"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
                  <polyline points="16 6 12 2 8 6"></polyline>
                  <line x1="12" y1="2" x2="12" y2="15"></line>
                </svg>
                Copy Share Link
              </Button>
              <Button
                onClick={() => window.open(editUrl || '', '_blank')}
                variant="outline"
                className="flex items-center gap-2"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
                Edit in Google Forms
              </Button>
            </div>
          </div>

          <div className="flex-1 flex overflow-hidden">
            {/* Left: Embedded Google Form */}
            <div className="w-1/2 border-r bg-gray-50 overflow-hidden">
              <iframe
                id="form-iframe"
                src={embedUrl || ''}
                className="w-full h-full"
                title="Google Form Preview"
                frameBorder="0"
                marginHeight={0}
                marginWidth={0}
              >
                Loading…
              </iframe>
            </div>

            {/* Right: AI Chat for Editing */}
            <div className="w-1/2 flex flex-col bg-white overflow-hidden">
              <div className="p-4 border-b flex-shrink-0">
                <h2 className="text-lg font-semibold">Edit Form with AI</h2>
                <p className="text-sm text-gray-600">Ask me to add, edit, or remove questions</p>
              </div>

              {/* Chat Messages - Scrollable */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-32">
                {chatMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {msg.role === 'user' ? (
                      <div className="max-w-[80%] rounded-lg px-4 py-2 bg-gray-900 text-white">
                        {msg.content}
                      </div>
                    ) : (
                      <div className="max-w-[80%]">
                        {msg.content === 'Processing your request...' ? (
                          <div className="flex items-center gap-2 text-gray-600">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm">{msg.content}</span>
                          </div>
                        ) : (
                          <div className="text-gray-900 text-sm whitespace-pre-wrap">
                            {msg.content}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Fixed Chat Input - Always visible at bottom */}
              <div className="absolute bottom-0 right-0 w-1/2 bg-white border-t border-gray-200 p-4 flex-shrink-0">
                <div className="flex gap-2">
                  <textarea
                    placeholder="Ask me to add, edit, or remove questions..."
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    disabled={isProcessing}
                    className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                    rows={1}
                    style={{
                      minHeight: '44px',
                      maxHeight: '120px',
                      overflowY: 'auto'
                    }}
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={isProcessing || !chatInput.trim()}
                    className="bg-gray-900 hover:bg-gray-800 text-white px-6 self-end"
                  >
                    {isProcessing ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                      </svg>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Forms History Sidebar */}
      {user?.email && (
        <FormsHistory
          isOpen={isHistoryOpen}
          onClose={() => setIsHistoryOpen(false)}
          onLoadForm={handleLoadFormFromHistory}
          userEmail={user.email}
        />
      )}
    </div>
  );
}

