"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import { useClassroomAuth } from '../hooks/useClassroomAuth';

interface ClassroomAuthPromptProps {
  onSuccess?: () => void;
  onSkip?: () => void;
}

export function ClassroomAuthPrompt({ onSuccess, onSkip }: ClassroomAuthPromptProps) {
  const { authorize, loading } = useClassroomAuth();
  const [error, setError] = useState<string | null>(null);

  const handleAuthorize = async () => {
    try {
      setError(null);
      await authorize();
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || 'Authorization failed');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-gray-100 rounded-full">
          <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
        
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Connect Google Services
          </h3>
          
          <p className="text-gray-600 text-sm">
            To enable full functionality, please authorize access to your Google Workspace services.
          </p>
        </div>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
            <div className="flex items-start gap-2">
          <svg className="w-4 h-4 text-gray-600 mt-0.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
          </svg>
              <div className="text-sm text-gray-600">
                <p className="font-medium mb-1">Permissions requested:</p>
                <ul className="list-disc list-inside space-y-0.5 text-xs">
              <li>View and manage your Google Classroom courses and assignments</li>
              <li>Create and edit Google Docs documents</li>
              <li>Create and edit Google Sheets spreadsheets</li>
              <li>Create and edit Google Forms</li>
              <li>Access Google Drive for file storage</li>
              <li>View your email address and profile information</li>
                </ul>
              </div>
            </div>
          </div>

          {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <Button
              onClick={handleAuthorize}
              disabled={loading}
          className="flex-1 bg-gray-900 hover:bg-gray-800 text-white"
            >
              {loading ? (
                <>
                  <Loader variant="circular" size="sm" />
                  <span className="ml-2">Authorizing...</span>
                </>
              ) : (
            'Authorize Google Services'
              )}
            </Button>
            
            {onSkip && (
              <Button
                onClick={onSkip}
                variant="ghost"
                className="text-gray-600 hover:text-gray-900"
                disabled={loading}
              >
                Skip for now
              </Button>
            )}
          </div>

      <p className="text-xs text-gray-500">
            You can authorize later from the settings menu.
          </p>
    </div>
  );
}

