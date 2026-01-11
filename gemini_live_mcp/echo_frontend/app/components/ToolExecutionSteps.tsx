"use client";

import { useState } from "react";
import { AlertCircle, Check, Loader2, Sparkles, BookOpen, FileText, Sheet, FormInput, GraduationCap, ClipboardList, Upload } from "lucide-react";

interface ToolStep {
  tool: string;
  args?: any;
  result?: any;
  status: 'running' | 'completed' | 'error';
}

interface ToolExecutionStepsProps {
  steps: ToolStep[];
}

// Map technical tool names to user-friendly names
const getToolDisplayName = (toolName: string): string => {
  const nameMap: Record<string, string> = {
    'list_courses': 'Finding courses…',
    'get_course': 'Fetching course…',
    'list_coursework': 'Finding coursework…',
    'get_coursework': 'Fetching coursework…',
    'list_announcements': 'Finding announcements…',
    'list_students': 'Finding students…',
    'list_submissions': 'Finding submissions…',
    'show_assignment_form': 'Preparing assignment form…',
    'create_coursework': 'Creating assignment…',
    'show_course_form': 'Preparing course form…',
    'create_course': 'Creating course…',
    'create_google_doc': 'Creating document…',
    'create_google_sheet': 'Creating spreadsheet…',
    'create_google_form': 'Creating form…',
    'upload_files': 'Uploading to Drive…',
  };

  return nameMap[toolName] || toolName.split('_').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
};

const getToolIcon = (toolName: string) => {
  if (toolName.includes('upload')) return Upload;
  if (toolName.includes('coursework') || toolName.includes('assignment')) return ClipboardList;
  if (toolName.includes('course')) return GraduationCap;
  if (toolName.includes('doc')) return FileText;
  if (toolName.includes('sheet')) return Sheet;
  if (toolName.includes('form')) return FormInput;
  if (toolName.includes('student')) return BookOpen;
  return Sparkles;
};

const safeString = (v: unknown): string => (typeof v === 'string' ? v : '');

const getToolSubtitle = (step: ToolStep): string => {
  const { tool: toolName, args, result, status } = step;
  if (status === 'error') {
    return safeString(result?.error) || 'Something went wrong.';
  }
  if (status === 'running') {
    if (toolName === 'list_courses') return 'Accessing Google Classroom…';
    if (toolName === 'create_course') return args?.name ? `Creating "${args.name}"…` : 'Creating your course…';
    if (toolName === 'create_coursework') return args?.title ? `Creating "${args.title}"…` : 'Creating assignment…';
    if (toolName === 'create_google_doc') return args?.title ? `Drafting "${args.title}"…` : 'Drafting document…';
    if (toolName === 'create_google_sheet') return args?.title ? `Building "${args.title}"…` : 'Building spreadsheet…';
    if (toolName === 'create_google_form') return args?.title ? `Building "${args.title}"…` : 'Building form…';
    if (toolName === 'show_course_form') return 'Fetching your student lists…';
    if (toolName === 'upload_files') return args?.count ? `Uploading ${args.count} file${args.count === 1 ? '' : 's'}…` : 'Uploading files…';
    return 'Working…';
  }

  // completed
  if (toolName === 'list_courses' && Array.isArray(result?.courses)) {
    return `${result.courses.length} course${result.courses.length === 1 ? '' : 's'} found`;
  }
  if (toolName === 'list_students' && Array.isArray(result?.students)) {
    return `${result.students.length} student${result.students.length === 1 ? '' : 's'} found`;
  }
  if (toolName === 'create_course' && result?.enrollment_code) {
    const code = result.enrollment_code;
    const emailSent = result.email_sent ? ` • emailed ${Array.isArray(result.email_recipients) ? result.email_recipients.length : 'students'}` : '';
    return `Created • code ${code}${emailSent}`;
  }
  if (toolName === 'create_coursework' && result?.courseWork?.title) {
    return `Created "${result.courseWork.title}"`;
  }
  if (toolName === 'create_google_doc' && result?.url) return 'Document created';
  if (toolName === 'create_google_sheet' && result?.url) return 'Spreadsheet created';
  if (toolName === 'create_google_form' && result?.url) return 'Form created';
  if (toolName === 'show_course_form') return 'Ready';
  if (toolName === 'show_assignment_form') return 'Ready';
  if (toolName === 'upload_files' && Array.isArray(result?.files)) {
    return `${result.files.length} file${result.files.length === 1 ? '' : 's'} uploaded`;
  }

  return 'Done';
};

export function ToolExecutionSteps({ steps }: ToolExecutionStepsProps) {
  if (steps.length === 0) return null;

  return (
    <div className="my-3 w-full max-w-md space-y-2">
                {steps.map((step, index) => {
        const title = getToolDisplayName(step.tool);
        const subtitle = getToolSubtitle(step);
        const Icon = getToolIcon(step.tool);

        const isError = step.status === 'error';
        const isRunning = step.status === 'running';
        const isDone = step.status === 'completed';
                  
                  return (
          <div
            key={index}
            className={[
              "rounded-xl border px-4 py-3 backdrop-blur",
              "bg-white",
              isError ? "border-red-300 bg-red-50/50" : "border-gray-200",
            ].join(" ")}
          >
            <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                {isRunning ? (
                  <Loader2 className="h-5 w-5 text-gray-500 animate-spin" />
                ) : isError ? (
                  <AlertCircle className="h-5 w-5 text-red-600" />
                ) : isDone ? (
                  <Check className="h-5 w-5 text-emerald-600" />
                        ) : (
                  <Icon className="h-5 w-5 text-gray-600" />
                        )}
                      </div>

              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium text-gray-900 truncate">
                  {title}
                </div>
                {subtitle && (
                  <div className={["text-sm", isError ? "text-red-700" : "text-gray-500"].join(" ")}>
                    {subtitle}
                        </div>
                        )}
              </div>
            </div>
        </div>
        );
      })}
    </div>
  );
}

