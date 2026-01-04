"use client";

import { useState, useEffect, useRef, useCallback } from 'react';
import { useGeminiWebSocket, WebSocketMessage } from './hooks/useGeminiWebSocket';
import { PromptInput, PromptInputActions, PromptInputAction, PromptInputTextarea } from "@/components/ui/prompt-input";
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import { Markdown } from "@/components/ui/markdown";
import { ArrowUp, Square, X } from "lucide-react";
import { 
  ChainOfThought, 
  ChainOfThoughtContent, 
  ChainOfThoughtItem, 
  ChainOfThoughtStep, 
  ChainOfThoughtTrigger 
} from "@/components/ui/chain-of-thought";
import { AssignmentForm, AssignmentData } from "./components/AssignmentForm";
import { CourseForm, CourseData } from "./components/CourseForm";
import { MessageWithLinks } from "./components/LinkButton";
import { ToolExecutionSteps } from "./components/ToolExecutionSteps";
import { useAuth } from "./contexts/AuthContext";

interface ToolStep {
  tool: string;
  args?: any;
  result?: any;
  status: 'running' | 'completed' | 'error';
}

interface ThoughtStep {
  id: string;
  thought: string;
  timestamp: number;
}

interface Course {
  id: string;
  name: string;
  section?: string;
  descriptionHeading?: string;
}

interface Message {
  id: string;
  role: 'user' | 'model';
  text: string;
  toolSteps?: ToolStep[];
  thoughts?: ThoughtStep[];
  showAssignmentForm?: boolean;
  assignmentCourseId?: string;
  assignmentCourses?: Course[];
  showCourseForm?: boolean;
}

// Helper function to create user-friendly error messages
function getUserFriendlyError(errorMessage: string): string {
  const lowerError = errorMessage.toLowerCase();
  
  // Rate limit / quota errors
  if (lowerError.includes('quota') || lowerError.includes('429') || lowerError.includes('resource_exhausted')) {
    return 'Rate limit reached. Please try again in a moment.';
  }
  
  // Authentication errors
  if (lowerError.includes('401') || lowerError.includes('unauthorized') || lowerError.includes('api key')) {
    return 'Authentication error. Please check your API configuration.';
  }
  
  // Network errors
  if (lowerError.includes('network') || lowerError.includes('connection') || lowerError.includes('timeout')) {
    return 'Connection error. Please check your internet and try again.';
  }
  
  // Generic error
  return 'An error occurred. Please try again.';
}

export default function ChatInterface() {
  const { user } = useAuth();
  // Voice mode removed - chat only
  const [statusText, setStatusText] = useState('I\'m here and ready to help. Just let me know what you need.');
  
  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isToolProcessing, setIsToolProcessing] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  
  
  // Thread ID for conversation memory
  const [threadId] = useState(() => `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);

  // Voice mode removed - only chat WebSocket remains

  // --- 2. CHAT CONNECTION ---
  const { 
    connectionState: chatConnectionState, 
    sendText, 
    connect: connectChat 
  } = useGeminiWebSocket('/ws/chat', (message) => {
      switch (message.type) {
        case 'thought':
          // Handle thinking/reasoning steps
          if (message.thought) {
            setMessages(prev => {
              const lastMsg = prev[prev.length - 1];
              const newThought: ThoughtStep = { 
                id: Date.now().toString(), 
                thought: message.thought || '', 
                timestamp: Date.now() 
              };
              if (lastMsg && lastMsg.role === 'model') {
                const thoughts = lastMsg.thoughts || [];
                return [...prev.slice(0, -1), { ...lastMsg, thoughts: [...thoughts, newThought] }];
              } else {
                return [...prev, { id: Date.now().toString(), role: 'model', text: '', thoughts: [newThought] }];
              }
            });
          }
          break;

        case 'text_chunk':
          setIsChatLoading(false);
          setIsToolProcessing(false);
          if (message.text) {
            setMessages(prev => {
              const lastMsg = prev[prev.length - 1];
              if (lastMsg && lastMsg.role === 'model') {
                return [...prev.slice(0, -1), { ...lastMsg, text: lastMsg.text + message.text }];
              } else {
                return [...prev, { id: Date.now().toString(), role: 'model', text: message.text || '' }];
              }
            });
          }
          break;
        
        case 'tool_start':
          setIsChatLoading(false);
          setIsToolProcessing(true);
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            const newStep: ToolStep = { tool: message.tool || 'unknown', args: message.args, status: 'running' };
            if (lastMsg && lastMsg.role === 'model') {
              const steps = lastMsg.toolSteps || [];
              return [...prev.slice(0, -1), { ...lastMsg, toolSteps: [...steps, newStep] }];
            } else {
              return [...prev, { id: Date.now().toString(), role: 'model', text: '', toolSteps: [newStep] }];
            }
          });
          break;
        
        case 'tool_end':
          setIsToolProcessing(true);
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'model' && lastMsg.toolSteps) {
              const steps = [...lastMsg.toolSteps];
              const stepIndex = steps.findIndex(s => s.tool === message.tool && s.status === 'running');
              if (stepIndex !== -1) {
                steps[stepIndex] = { ...steps[stepIndex], result: message.result, status: 'completed' };
                return [...prev.slice(0, -1), { ...lastMsg, toolSteps: steps }];
              }
            }
            return prev;
          });
          break;
          
        case 'error':
           const friendlyError = getUserFriendlyError(message.text || 'Unknown error');
           setMessages(prev => [...prev, { id: Date.now().toString(), role: 'model', text: friendlyError }]);
           setIsChatLoading(false);
           setIsToolProcessing(false);
           break;
        
        case 'show_assignment_form':
          // AI has decided to show the assignment form
          const courseId = message.data?.course_id || '';
          const courses = message.data?.courses || [];
          console.log('📝 [FORM] Received show_assignment_form with', courses.length, 'courses');
          
          setMessages(prev => {
            // Check if ANY message already has an assignment form (prevent duplicates)
            const hasExistingForm = prev.some(msg => msg.showAssignmentForm);
            if (hasExistingForm) {
              console.warn('⚠️ [FORM] Assignment form already exists, skipping duplicate');
              return prev;
            }
            
            console.log('✅ [FORM] Creating assignment form');
            
            // Always create a new message for the form
            return [
              ...prev,
              {
                id: `form-${Date.now()}`,
                role: 'model',
                text: '📝 Please select a course and fill in the assignment details below:',
                showAssignmentForm: true,
                assignmentCourseId: courseId,
                assignmentCourses: courses
              }
            ];
          });
          setIsChatLoading(false);
          setIsToolProcessing(false);
          break;
        
        case 'show_course_form':
          // AI has decided to show the course creation form
          console.log('📚 [FORM] Received show_course_form');
          
          setMessages(prev => {
            // Check if ANY message already has a course form (prevent duplicates)
            const hasExistingForm = prev.some(msg => msg.showCourseForm);
            if (hasExistingForm) {
              console.warn('⚠️ [FORM] Course form already exists, skipping duplicate');
              return prev;
            }
            
            console.log('✅ [FORM] Creating course form');
            
            // Always create a new message for the form
            return [
              ...prev,
              {
                id: `form-${Date.now()}`,
                role: 'model',
                text: '📚 Let me help you create a new course. Please fill in the details below:',
                showCourseForm: true
              }
            ];
          });
          setIsChatLoading(false);
          setIsToolProcessing(false);
          break;
      }
  });

  // Auto-connect Chat on mount (only when user is authenticated)
  useEffect(() => {
    if (user) {
      // Small delay to ensure component is fully mounted
      const timer = setTimeout(() => {
    connectChat();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [connectChat, user]);

  // Voice mode removed

  // Chat Submission
  const handleChatSubmit = () => {
    if (!chatInput.trim()) return;
    
    // Check connection
    if (chatConnectionState !== 'connected') {
        // Don't send if not connected - show error instead
        setMessages(prev => [...prev, 
          { id: Date.now().toString(), role: 'user', text: chatInput },
          { id: (Date.now() + 1).toString(), role: 'model', text: 'Not connected to backend. Please wait for connection...' }
        ]);
        setChatInput("");
        connectChat(); // Try to reconnect
        return;
    }
    
    // Send message to backend - AI will decide via tool if form should be shown
    sendText(chatInput, threadId);
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text: chatInput }]);
    setChatInput("");
    setIsChatLoading(true);
    setIsToolProcessing(false);
  };
  
  // Handle assignment form submission
  const handleAssignmentSubmit = (messageId: string, data: AssignmentData) => {
    // Remove the form message
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
    
    // Send assignment creation request through chat
    const assignmentMessage = `Create an assignment with the following details:
Course ID: ${data.course_id}
Title: ${data.title}
Description: ${data.description || 'N/A'}
Due Date: ${data.due_date || 'N/A'}
Due Time: ${data.due_time || 'N/A'}
Max Points: ${data.max_points}
Work Type: ${data.work_type}`;
    
    sendText(assignmentMessage, threadId);
    setMessages(prev => [...prev, { 
      id: Date.now().toString(), 
      role: 'user', 
      text: `Creating assignment: ${data.title}` 
    }]);
    setIsChatLoading(true);
  };
  
  // Handle assignment form cancellation
  const handleAssignmentCancel = (messageId: string) => {
    console.log('❌ [FORM] Cancelling assignment form:', messageId);
    // Remove the form message and add cancellation message
    setMessages(prev => {
      const filtered = prev.filter(msg => msg.id !== messageId);
      console.log('📊 [FORM] Messages after cancel:', filtered.length);
      return [
        ...filtered,
      {
        id: Date.now().toString(),
        role: 'model',
        text: 'Assignment creation cancelled.'
      }
      ];
    });
  };
  
  // Handle course form submission
  const handleCourseSubmit = (messageId: string, data: CourseData) => {
    // Remove the form message
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
    
    // Send course creation request through chat
    const courseMessage = `Create a course with the following details:
Name: ${data.name}
Section: ${data.section || 'N/A'}
Description Heading: ${data.description_heading || 'N/A'}
Description: ${data.description || 'N/A'}
Room: ${data.room || 'N/A'}`;
    
    sendText(courseMessage, threadId);
    setMessages(prev => [...prev, { 
      id: Date.now().toString(), 
      role: 'user', 
      text: `Creating course: ${data.name}` 
    }]);
    setIsChatLoading(true);
  };
  
  const handleCourseCancel = (messageId: string) => {
    console.log('❌ [FORM] Cancelling course form:', messageId);
    // Remove the form message and add cancellation message
    setMessages(prev => {
      const filtered = prev.filter(msg => msg.id !== messageId);
      console.log('📊 [FORM] Messages after cancel:', filtered.length);
      return [
        ...filtered,
      {
        id: Date.now().toString(),
        role: 'model',
        text: 'Course creation cancelled.'
      }
      ];
    });
  };

  // Scroll to bottom when messages change or loading state changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isChatLoading, isToolProcessing]);

  // Voice mode removed

  // Chat View
    return (
      <div className="h-full bg-white text-gray-900 flex flex-col overflow-hidden">
        {/* Main Content - Scrollable Area */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden px-6 pt-6 pb-32">
          {messages.length === 0 ? (
            <div className="text-center max-w-2xl mx-auto mt-20">
              <h2 className="text-3xl font-medium text-gray-900 mb-4">
                Ask anything
              </h2>
              <p className="text-gray-500">
                I'm here and ready to help. Just let me know what you need.
              </p>
            </div>
          ) : (
            <div className="w-full max-w-3xl mx-auto space-y-6 pb-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-1`}>
                  {/* Tool Execution Steps - Left Aligned with AI Message */}
                  {msg.toolSteps && msg.toolSteps.length > 0 && msg.role === 'model' && (
                    <div className="max-w-[85%]">
                      <ToolExecutionSteps steps={msg.toolSteps} />
                    </div>
                  )}
                  
                  <div className={`max-w-[85%] rounded-2xl px-5 py-3 ${
                    msg.role === 'user' 
                      ? 'bg-gray-100 text-gray-900' 
                      : 'bg-white border border-gray-200 text-gray-900'
                  }`}>
                    {/* Thinking Steps - Inside bubble */}
                    {msg.thoughts && msg.thoughts.length > 0 && (
                      <div className="mb-4 w-full">
                        <ChainOfThought>
                          {msg.thoughts.map((thought, idx) => (
                            <ChainOfThoughtStep key={`thought-${thought.id}`}>
                              <ChainOfThoughtTrigger className="text-sm text-gray-700 font-medium">
                                💭 Thinking step {idx + 1}
                              </ChainOfThoughtTrigger>
                              <ChainOfThoughtContent>
                                <ChainOfThoughtItem>
                                  <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                                    {thought.thought}
                                  </div>
                                </ChainOfThoughtItem>
                              </ChainOfThoughtContent>
                            </ChainOfThoughtStep>
                          ))}
                        </ChainOfThought>
                      </div>
                    )}
                    
                    {/* Message Content - Markdown with proper formatting */}
                    {msg.text && !msg.showAssignmentForm && !msg.showCourseForm && (
                      msg.text.match(/https:\/\/docs\.google\.com\/(forms|document|spreadsheets)/) ? (
                        <MessageWithLinks text={msg.text} />
                      ) : (
                        <Markdown className="markdown-content">
                        {msg.text}
                      </Markdown>
                      )
                    )}
                    
                    {/* Assignment Form - Inline */}
                    {msg.showAssignmentForm && !msg.showCourseForm && (
                      <div className="w-full">
                        <AssignmentForm
                          courseId={msg.assignmentCourseId}
                          courses={msg.assignmentCourses}
                          onSubmit={(data) => handleAssignmentSubmit(msg.id, data)}
                          onCancel={() => handleAssignmentCancel(msg.id)}
                        />
                      </div>
                    )}
                    
                    {/* Course Form - Inline */}
                    {msg.showCourseForm && !msg.showAssignmentForm && (
                      <div className="w-full">
                        <CourseForm
                          onSubmit={(data) => handleCourseSubmit(msg.id, data)}
                          onCancel={() => handleCourseCancel(msg.id)}
                        />
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {isChatLoading && (
                <div className="flex items-center gap-3 ml-2">
                   <Loader variant="typing" size="sm" />
                   <span className="text-sm text-gray-500">Processing your request...</span>
                </div>
              )}
              
              {isToolProcessing && (
                <div className="flex items-center gap-3 ml-2">
                   <Loader variant="typing" size="sm" />
                   <span className="text-sm text-gray-500">Processing...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}
        </main>

        {/* Fixed Bottom Input */}
        <div className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-sm p-6">
          <div className="max-w-3xl mx-auto">
            <PromptInput
              value={chatInput}
              onValueChange={setChatInput}
              isLoading={isChatLoading}
              onSubmit={handleChatSubmit}
              className="w-full"
            >
              <PromptInputTextarea placeholder="Ask anything..." />
              <PromptInputActions className="justify-end pt-2 gap-2">
                <PromptInputAction
                  tooltip={isChatLoading ? "Thinking..." : "Send message"}
                >
                  <Button
                    variant="default"
                    size="icon"
                    className="h-8 w-8 rounded-full bg-gray-900 hover:bg-gray-800"
                    onClick={handleChatSubmit}
                    disabled={isChatLoading}
                  >
                    {isChatLoading ? (
                      <Square className="size-5 fill-current" />
                    ) : (
                      <ArrowUp className="size-5" />
                    )}
                  </Button>
                </PromptInputAction>
              </PromptInputActions>
            </PromptInput>
          </div>
      </div>
    </div>
  );
}
