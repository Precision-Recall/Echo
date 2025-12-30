"use client";

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import { GraduationCap, ShieldCheck } from 'lucide-react';
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
    <div className="max-w-2xl mx-auto p-6 bg-white border border-gray-200 rounded-lg shadow-sm">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-gray-100 rounded-full">
          <GraduationCap className="w-6 h-6 text-gray-900" />
        </div>
        
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Connect Google Classroom
          </h3>
          
          <p className="text-gray-600 mb-4">
            To access your courses, create assignments, and manage coursework, please authorize access to your Google Classroom.
          </p>

          <div className="bg-gray-50 border border-gray-200 rounded-md p-3 mb-4">
            <div className="flex items-start gap-2">
              <ShieldCheck className="w-4 h-4 text-gray-600 mt-0.5" />
              <div className="text-sm text-gray-600">
                <p className="font-medium mb-1">Permissions requested:</p>
                <ul className="list-disc list-inside space-y-0.5 text-xs">
                  <li>View and manage your courses</li>
                  <li>View and manage coursework and assignments</li>
                  <li>View and manage course rosters</li>
                  <li>Create and edit documents, sheets, and slides</li>
                </ul>
              </div>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <Button
              onClick={handleAuthorize}
              disabled={loading}
              className="bg-gray-900 hover:bg-gray-800 text-white"
            >
              {loading ? (
                <>
                  <Loader variant="circular" size="sm" />
                  <span className="ml-2">Authorizing...</span>
                </>
              ) : (
                'Authorize Google Classroom'
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

          <p className="text-xs text-gray-500 mt-3">
            You can authorize later from the settings menu.
          </p>
        </div>
      </div>
    </div>
  );
}

