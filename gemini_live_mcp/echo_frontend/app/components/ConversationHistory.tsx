"use client";

import { useState, useEffect } from 'react';
import { X, MessageSquare, Trash2, Loader2 } from 'lucide-react';
import { useAuth } from '@/app/contexts/AuthContext';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ConversationHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onLoadConversation: (conversationId: string) => void;
}

export default function ConversationHistory({
  isOpen,
  onClose,
  onLoadConversation,
}: ConversationHistoryProps) {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || 'http://localhost:8001';

  useEffect(() => {
    if (isOpen && user?.email) {
      loadConversations();
    }
  }, [isOpen, user?.email, page]);

  const loadConversations = async () => {
    if (!user?.email) return;

    setLoading(true);
    try {
      const response = await fetch(
        `${TOKEN_SERVICE_URL}/api/conversations?email=${encodeURIComponent(user.email)}&page=${page}&limit=10`
      );

      if (response.ok) {
        const data = await response.json();
        if (page === 1) {
          setConversations(data);
        } else {
          setConversations((prev) => [...prev, ...data]);
        }
        setHasMore(data.length === 10);
      } else {
        console.error('Failed to load conversations:', await response.text());
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this conversation?')) {
      return;
    }

    if (!user?.email) return;

    // Optimistic delete - remove from UI immediately
    setConversations((prev) => prev.filter((c) => c.id !== conversationId));
    
    // Delete from backend in background (fire-and-forget)
    fetch(
      `${TOKEN_SERVICE_URL}/api/conversations/${conversationId}?email=${encodeURIComponent(user.email)}`,
      {
        method: 'DELETE',
      }
    ).catch(error => {
      console.error('Error deleting conversation from backend:', error);
      // Optionally: Could restore the conversation in UI if backend delete fails
    });
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="fixed top-0 right-0 h-full w-80 bg-white shadow-2xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-purple-600" />
            <h2 className="text-lg font-semibold">Chat History</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto">
          {loading && page === 1 ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-500">
              <MessageSquare className="w-12 h-12 mb-2 opacity-50" />
              <p className="text-sm">No conversations yet</p>
            </div>
          ) : (
            <div className="p-2">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => {
                    onLoadConversation(conv.id);
                    onClose();
                  }}
                  className="group relative p-3 mb-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors border border-transparent hover:border-purple-200"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {conv.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatDate(conv.updated_at)}
                      </p>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      disabled={deleting === conv.id}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-50 rounded transition-all"
                    >
                      {deleting === conv.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-red-600" />
                      ) : (
                        <Trash2 className="w-4 h-4 text-red-600" />
                      )}
                    </button>
                  </div>
                </div>
              ))}

              {/* Load More */}
              {hasMore && (
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={loading}
                  className="w-full py-2 text-sm text-purple-600 hover:bg-purple-50 rounded-lg transition-colors disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                  ) : (
                    'Load More'
                  )}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

