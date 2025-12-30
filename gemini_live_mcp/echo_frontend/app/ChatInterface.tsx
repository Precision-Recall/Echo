"use client";

import { useState, useEffect, useRef } from 'react';
import { useGeminiWebSocket, WebSocketMessage } from './hooks/useGeminiWebSocket';
import { useAudioCapture } from './hooks/useAudioCapture';
import { useAudioPlayback } from './hooks/useAudioPlayback';
import { PromptInput, PromptInputActions, PromptInputAction, PromptInputTextarea } from "@/components/ui/prompt-input";
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import { Markdown } from "@/components/ui/markdown";
import { ArrowUp, Square, Mic, X } from "lucide-react";
import { 
  ChainOfThought, 
  ChainOfThoughtContent, 
  ChainOfThoughtItem, 
  ChainOfThoughtStep, 
  ChainOfThoughtTrigger 
} from "@/components/ui/chain-of-thought";
import { AssignmentForm, AssignmentData } from "./components/AssignmentForm";
import { CourseForm, CourseData } from "./components/CourseForm";
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
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [statusText, setStatusText] = useState('I\'m here and ready to help. Just let me know what you need.');
  
  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isToolProcessing, setIsToolProcessing] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  
  
  // Thread ID for conversation memory
  const [threadId] = useState(() => `thread_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);

  // --- 1. LIVE AUDIO CONNECTION ---
  const { 
    connectionState: liveConnectionState, 
    sendAudio, 
    connect: connectLive, 
    disconnect: disconnectLive 
  } = useGeminiWebSocket('/ws/live', (message) => {
      switch (message.type) {
        case 'audio':
          if (message.data) {
            setStatusText('Gemini is speaking...');
            playAudio(message.data);
          }
          break;
        case 'connected':
          setStatusText('Connected. Tap microphone to speak.');
          break;
        case 'error':
          const friendlyError = getUserFriendlyError(message.data || 'Unknown error');
          setStatusText(friendlyError);
          break;
        case 'turn_complete':
          setStatusText('Gemini finished speaking.');
          break;
      }
  });

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
          console.log('📝 Received courses for dropdown:', courses.length, courses);
          
          setMessages(prev => {
            // Check if last message already has form (prevent duplicates)
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.showAssignmentForm) {
              console.warn('Form already shown, skipping duplicate');
              return prev;
            }
            
            // If last message is from model, update it to include form
            if (lastMsg && lastMsg.role === 'model' && !lastMsg.text) {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  text: '📝 Please select a course and fill in the assignment details below:',
                  showAssignmentForm: true,
                  assignmentCourseId: courseId,
                  assignmentCourses: courses
                }
              ];
            }
            
            // Otherwise create new message
            return [
              ...prev,
              {
                id: Date.now().toString(),
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
          console.log('📚 Showing course creation form');
          
          setMessages(prev => {
            // Check if last message already has form (prevent duplicates)
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.showCourseForm) {
              console.warn('Course form already shown, skipping duplicate');
              return prev;
            }
            
            // If last message is from model, update it to include form
            if (lastMsg && lastMsg.role === 'model' && !lastMsg.text) {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  text: '📚 Let me help you create a new course. Please fill in the details below:',
                  showCourseForm: true
                }
              ];
            }
            
            // Otherwise create new message
            return [
              ...prev,
              {
                id: Date.now().toString(),
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

  // Audio playback
  const { playAudio, isPlaying, error: playbackError } = useAudioPlayback();

  // Audio capture
  const { isRecording, startRecording, stopRecording, error: captureError } = useAudioCapture(
    (audioData: string) => {
      sendAudio(audioData, false);
    }
  );

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
    // Remove the form message and add cancellation message
    setMessages(prev => [
      ...prev.filter(msg => msg.id !== messageId),
      {
        id: Date.now().toString(),
        role: 'model',
        text: 'Assignment creation cancelled.'
      }
    ]);
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
    // Remove the form message and add cancellation message
    setMessages(prev => [
      ...prev.filter(msg => msg.id !== messageId),
      {
        id: Date.now().toString(),
        role: 'model',
        text: 'Course creation cancelled.'
      }
    ]);
  };

  // Scroll to bottom when messages change or loading state changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isChatLoading, isToolProcessing]);

  // Handle LIVE session toggle
  const handleLiveSessionToggle = async () => {
    if (liveConnectionState === 'connected') {
      stopRecording();
      disconnectLive();
      setStatusText('Disconnected');
    } else {
      connectLive();
      setStatusText('Connecting...');
    }
  };

  // Auto-start recording when LIVE connected
  useEffect(() => {
    if (liveConnectionState === 'connected' && !isRecording) {
      startRecording();
      setStatusText('Listening...');
    }
  }, [liveConnectionState, isRecording]);

  // Cleanup
  useEffect(() => {
    return () => {
      stopRecording();
      disconnectLive();
      // Chat stays connected typically, but we can disconnect on unmount
    };
  }, []);

  // Chat View (Default)
  if (!isVoiceMode) {
    return (
      <div className="min-h-screen bg-white text-gray-900 flex flex-col">
        {/* Header */}
        <header className="fixed top-0 left-0 right-0 bg-white/80 backdrop-blur-sm border-b border-gray-200 z-50">
          <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600" />
              <h1 className="text-xl font-semibold text-gray-900">Echo</h1>
            </div>
            
            <Button
              onClick={() => {
                setIsVoiceMode(true);
                handleLiveSessionToggle();
              }}
              className="bg-gray-100 hover:bg-gray-200 text-gray-900 rounded-full px-4 py-2 flex items-center gap-2 transition-colors"
              variant="ghost"
            >
              <Mic className="w-4 h-4" />
              Voice Mode
            </Button>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 flex flex-col items-center justify-center px-6 pt-20 pb-32">
          {messages.length === 0 ? (
            <div className="text-center max-w-2xl">
              <h2 className="text-3xl font-medium text-gray-900 mb-4">
                Ask anything
              </h2>
              <p className="text-gray-500">
                I'm here and ready to help. Just let me know what you need.
              </p>
            </div>
          ) : (
            <div className="w-full max-w-3xl space-y-6 overflow-y-auto">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-1`}>
                  {/* Tool Call Dropdown - Outside bubble, small font */}
                  {msg.toolSteps && msg.toolSteps.length > 0 && msg.role === 'model' && (
                    <div className="px-2">
                      <ChainOfThought>
                        <ChainOfThoughtStep>
                          <ChainOfThoughtTrigger className="text-xs text-gray-500 font-medium">
                            🔧 Tool used: <span className="font-mono text-blue-600">{msg.toolSteps[0].tool}</span>
                          </ChainOfThoughtTrigger>
                          <ChainOfThoughtContent>
                            {msg.toolSteps.map((step, idx) => (
                              <div key={idx} className="space-y-2">
                                <ChainOfThoughtItem>
                                  <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Input</span>
                                  <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto border border-gray-200">
                                    {JSON.stringify(step.args, null, 2)}
                                  </pre>
                                </ChainOfThoughtItem>
                                {step.result && (
                                  <ChainOfThoughtItem>
                                    <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Result</span>
                                    <pre className="text-xs bg-green-50 p-2 rounded mt-1 overflow-x-auto border border-green-200 text-green-800">
                                      {JSON.stringify(step.result, null, 2)}
                                    </pre>
                                  </ChainOfThoughtItem>
                                )}
                              </div>
                            ))}
                          </ChainOfThoughtContent>
                        </ChainOfThoughtStep>
                      </ChainOfThought>
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
                    
                    {/* Message Content with Markdown */}
                    {msg.text && !msg.showAssignmentForm && !msg.showCourseForm && (
                      <Markdown 
                        className="prose prose-sm max-w-none prose-headings:font-semibold prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-p:text-gray-900 prose-li:text-gray-900 prose-strong:text-gray-900"
                      >
                        {msg.text}
                      </Markdown>
                    )}
                    
                    {/* Assignment Form - Inline */}
                    {msg.showAssignmentForm && (
                      <div className="space-y-3">
                        {msg.text && (
                          <p className="text-sm text-gray-700 mb-3">{msg.text}</p>
                        )}
                        <AssignmentForm
                          courseId={msg.assignmentCourseId}
                          courses={msg.assignmentCourses}
                          onSubmit={(data) => handleAssignmentSubmit(msg.id, data)}
                          onCancel={() => handleAssignmentCancel(msg.id)}
                        />
                      </div>
                    )}
                    
                    {/* Course Form - Inline */}
                    {msg.showCourseForm && (
                      <div className="space-y-3">
                        {msg.text && (
                          <p className="text-sm text-gray-700 mb-3">{msg.text}</p>
                        )}
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
              <PromptInputActions className="justify-end pt-2">
                <PromptInputAction
                  tooltip={isChatLoading ? "Thinking..." : "Send message"}
                >
                  <Button
                    variant="default"
                    size="icon"
                    className="h-8 w-8 rounded-full"
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

  // Voice View
  return (
    <div className="min-h-screen bg-white text-gray-900 flex flex-col items-center justify-center relative">
      {/* Settings Icon */}
      <button className="absolute top-6 right-6 w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors">
        <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center space-y-8 px-6">
        <p className="text-xl text-gray-600 text-center max-w-2xl">
          {statusText}
        </p>

        {/* Animated Circle */}
        <div className="relative flex items-center justify-center">
          <div className={`absolute inset-0 rounded-full transition-all duration-500 ${
            isRecording || isPlaying 
              ? 'bg-gradient-to-br from-blue-200 to-purple-200 blur-3xl opacity-60 scale-150' 
              : 'bg-gray-100 blur-2xl opacity-40'
          } w-80 h-80`} />
          
          <div className={`relative z-10 w-64 h-64 rounded-full border-4 transition-all duration-500 flex items-center justify-center ${
            isRecording || isPlaying
              ? 'border-blue-400 bg-gradient-to-br from-blue-50 to-purple-50 scale-105' 
              : 'border-gray-300 bg-white'
          }`}>
            <div className={`w-48 h-48 rounded-full transition-all duration-700 ${
              isRecording || isPlaying
                ? 'bg-gradient-to-br from-blue-100 to-purple-100 animate-pulse' 
                : 'bg-gray-50'
            }`} />
          </div>
        </div>

        {/* End Session Button */}
        <Button
          onClick={() => {
            handleLiveSessionToggle();
            setIsVoiceMode(false);
          }}
          className="bg-gray-900 hover:bg-gray-800 text-white px-6 py-2 rounded-full"
        >
          End Session
        </Button>
      </div>

      {/* Bottom Controls */}
      <div className="pb-8 flex items-center gap-4">
        <button 
          onClick={() => {
            handleLiveSessionToggle();
            setIsVoiceMode(false);
          }}
          className="w-12 h-12 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
        >
          <X className="w-5 h-5 text-gray-700" />
        </button>
        
        <button 
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
            liveConnectionState === 'connected'
              ? 'bg-blue-500 hover:bg-blue-600 text-white scale-110' 
              : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
          }`}
        >
          <Mic className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
