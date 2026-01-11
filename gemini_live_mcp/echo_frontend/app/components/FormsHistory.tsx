"use client";

import { useState, useEffect } from 'react';
import { X, Loader2, Trash2, FileText } from 'lucide-react';
import { Button } from "@/components/ui/button";

interface FormSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  embed_url: string;
  view_url: string;
  edit_url: string;
}

interface FormsHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadForm: (form: FormSummary) => void;
  userEmail: string;
}

const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || 'http://localhost:8001';

export function FormsHistory({ isOpen, onClose, onLoadForm, userEmail }: FormsHistoryProps) {
  const [forms, setForms] = useState<FormSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    if (isOpen && userEmail) {
      loadForms();
    }
  }, [isOpen, userEmail, page]);

  const loadForms = async () => {
    if (!userEmail) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        `${TOKEN_SERVICE_URL}/api/forms?email=${encodeURIComponent(userEmail)}&page=${page}&limit=10`
      );
      
      if (response.ok) {
        const data = await response.json();
        if (page === 1) {
          setForms(data);
        } else {
          setForms(prev => [...prev, ...data]);
        }
        setHasMore(data.length === 10);
      }
    } catch (error) {
      console.error('Error loading forms:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteForm = async (formId: string) => {
    // Optimistic update
    setForms(prev => prev.filter(f => f.id !== formId));
    
    // Delete in background
    try {
      await fetch(
        `${TOKEN_SERVICE_URL}/api/forms/${formId}?email=${encodeURIComponent(userEmail)}`,
        { method: 'DELETE' }
      );
    } catch (error) {
      console.error('Error deleting form:', error);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-80 bg-white border-l border-gray-200 shadow-lg z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Forms History</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="h-8 w-8 p-0"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Forms List */}
      <div className="flex-1 overflow-y-auto">
        {loading && forms.length === 0 ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        ) : forms.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <FileText className="w-12 h-12 mb-2 text-gray-300" />
            <p className="text-sm">No forms yet</p>
          </div>
        ) : (
          <div className="p-2">
            {forms.map((form) => (
              <div
                key={form.id}
                className="group p-3 mb-2 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => {
                  onLoadForm(form);
                  onClose();
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-gray-900 truncate">
                      {form.title}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatDate(form.updated_at)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteForm(form.id);
                    }}
                  >
                    <Trash2 className="h-3 w-3 text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
            
            {hasMore && (
              <Button
                variant="outline"
                className="w-full mt-2"
                onClick={() => setPage(p => p + 1)}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Load More'
                )}
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

