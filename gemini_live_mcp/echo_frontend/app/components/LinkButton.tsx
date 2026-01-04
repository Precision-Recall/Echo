"use client";

import { ExternalLink, FileText, Sheet, FormInput } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LinkButtonProps {
  url: string;
  text?: string;
}

export function LinkButton({ url, text }: LinkButtonProps) {
  // Determine the type of link and icon
  const getLinkInfo = () => {
    if (url.includes('docs.google.com/forms')) {
      // Check if it's an edit URL or view URL
      const isEditUrl = url.includes('/edit');
      const defaultLabel = isEditUrl ? 'Edit Form' : 'View Form';
      return { icon: FormInput, label: text || defaultLabel, color: 'bg-gray-900 hover:bg-gray-800' };
    } else if (url.includes('docs.google.com/document')) {
      return { icon: FileText, label: text || 'Open Google Doc', color: 'bg-blue-600 hover:bg-blue-700' };
    } else if (url.includes('docs.google.com/spreadsheets')) {
      return { icon: Sheet, label: text || 'Open Google Sheet', color: 'bg-green-600 hover:bg-green-700' };
    } else {
      return { icon: ExternalLink, label: text || 'Open Link', color: 'bg-gray-900 hover:bg-gray-800' };
    }
  };

  const { icon: Icon, label, color } = getLinkInfo();

  return (
    <Button
      onClick={() => window.open(url, '_blank', 'noopener,noreferrer')}
      className={`${color} text-white rounded-lg px-4 py-2 flex items-center gap-2 transition-all hover:scale-105 shadow-md`}
    >
      <Icon size={16} />
      <span className="font-medium">{label}</span>
    </Button>
  );
}

// Component to render text with links as buttons
interface MessageWithLinksProps {
  text: string;
  className?: string;
}

export function MessageWithLinks({ text, className = "" }: MessageWithLinksProps) {
  // Regex to find URLs
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);
  
  return (
    <div className={`space-y-2 ${className}`}>
      {parts.map((part, index) => {
        if (part.match(urlRegex)) {
          return (
            <div key={index} className="inline-block mr-2">
              <LinkButton url={part} />
            </div>
          );
        } else if (part.trim()) {
          // Regular text - remove link description phrases
          const cleanText = part
            .replace(/(?:You can (?:view|edit) the (?:form|doc|sheet|document|spreadsheet) here:)\s*/gi, '')
            .replace(/(?:You can (?:access|view|edit) the form here:)\s*/gi, '');
          
          return cleanText.trim() ? (
            <p key={index} className="text-sm text-gray-700 whitespace-pre-wrap">
              {cleanText}
            </p>
          ) : null;
        }
        return null;
      })}
    </div>
  );
}

