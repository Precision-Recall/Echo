"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Check } from "lucide-react";

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
    'list_courses': 'Retrieving courses',
    'show_assignment_form': 'Preparing assignment form',
    'create_coursework': 'Creating assignment',
    'create_course': 'Creating course',
    'show_course_form': 'Preparing course form',
    'create_google_doc': 'Creating document',
    'create_google_sheet': 'Creating spreadsheet',
    'create_google_form': 'Creating form',
    'get_course': 'Fetching course details',
    'list_coursework': 'Retrieving assignments',
    'get_coursework': 'Fetching assignment details',
    'list_announcements': 'Retrieving announcements',
    'list_students': 'Retrieving students',
    'list_submissions': 'Fetching submissions',
  };

  return nameMap[toolName] || toolName.split('_').map(word => 
    word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ');
};

// Get a brief description of what the tool is doing
const getToolDescription = (tool: ToolStep): string => {
  const { tool: toolName, args } = tool;
  
  if (toolName === 'list_courses') {
    return 'Accessing your Google Classroom';
  } else if (toolName === 'create_google_form') {
    return args?.title ? `${args.title}` : 'Generating questions and structure';
  } else if (toolName === 'create_google_doc') {
    return args?.title ? `${args.title}` : 'Formatting content and headings';
  } else if (toolName === 'create_google_sheet') {
    return args?.title ? `${args.title}` : 'Organizing data into spreadsheet';
  } else if (toolName === 'create_coursework') {
    return args?.title ? `${args.title}` : 'Setting up in Google Classroom';
  } else if (toolName === 'create_course') {
    return args?.name ? `${args.name}` : 'Configuring course settings';
  }
  
  return '';
};

// Count sources/items from result
const getSourceCount = (result: any): number => {
  if (result?.courses) return result.courses.length;
  if (result?.questions) return result.questions.length;
  if (result?.data) return Array.isArray(result.data) ? result.data.length : 0;
  return 0;
};

export function ToolExecutionSteps({ steps }: ToolExecutionStepsProps) {
  const [expanded, setExpanded] = useState(false);
  
  if (steps.length === 0) return null;

  const allCompleted = steps.every(step => step.status === 'completed');
  const hasError = steps.some(step => step.status === 'error');
  const currentStep = steps.findIndex(step => step.status === 'running');
  const activeStep = currentStep >= 0 ? currentStep : steps.length - 1;

  return (
    <div className="my-3">
      <div className="w-full max-w-md">
        {/* Main Status Header - Left Aligned */}
        <div className="flex flex-col items-start gap-1.5 mb-2">
          {!allCompleted && !hasError && (
            <>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <div className="w-3.5 h-3.5 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" />
                </div>
                <span className="text-xs font-medium text-gray-900">
                  {getToolDisplayName(steps[activeStep]?.tool)}
                </span>
              </div>
              {/* Current Step Description */}
              {steps[activeStep] && getToolDescription(steps[activeStep]) && (
                <p className="text-xs text-gray-500 pl-5">
                  {getToolDescription(steps[activeStep])}
                </p>
              )}
            </>
          )}
          {allCompleted && (
            <div className="flex items-center gap-2">
              <div className="w-3.5 h-3.5 rounded-full bg-gray-900 flex items-center justify-center">
                <Check className="w-2 h-2 text-white" />
              </div>
              <span className="text-xs font-medium text-gray-900">Finished</span>
            </div>
          )}
        </div>

        {/* Steps List (Collapsible) */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          {/* Header */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-gray-700">
                {allCompleted ? 'Completed' : 'Processing'} {steps.length} {steps.length === 1 ? 'step' : 'steps'}
              </span>
              {steps.some(s => getSourceCount(s.result) > 0) && (
                <span className="text-xs text-gray-500">
                  · {steps.reduce((acc, s) => acc + getSourceCount(s.result), 0)}
                </span>
              )}
            </div>
            {expanded ? (
              <ChevronUp className="w-3 h-3 text-gray-400" />
            ) : (
              <ChevronDown className="w-3 h-3 text-gray-400" />
            )}
          </button>

          {/* Expanded Content */}
          {expanded && (
            <div className="border-t border-gray-200 bg-gray-50">
              <div className="px-3 py-2 space-y-2">
                {steps.map((step, index) => {
                  const sourceCount = getSourceCount(step.result);
                  const description = getToolDescription(step);
                  
                  return (
                    <div key={index} className="flex items-start gap-2">
                      {/* Status Icon */}
                      <div className="mt-0.5">
                        {step.status === 'completed' ? (
                          <div className="w-3 h-3 rounded-full bg-gray-900 flex items-center justify-center">
                            <Check className="w-1.5 h-1.5 text-white" />
                          </div>
                        ) : step.status === 'running' ? (
                          <div className="w-3 h-3 border-2 border-gray-900 border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <div className="w-3 h-3 rounded-full border-2 border-gray-300" />
                        )}
                      </div>

                      {/* Step Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs font-medium text-gray-900">
                            {getToolDisplayName(step.tool)}
                          </span>
                          {sourceCount > 0 && (
                            <span className="text-xs text-gray-500">
                              · {sourceCount}
                            </span>
                          )}
                        </div>
                        {(step.status === 'running' || step.status === 'completed') && description && (
                          <p className="text-xs text-gray-500 mt-0.5">
                            {description}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

