"use client";

import { useState, useEffect, useRef, useCallback } from 'react';
import { useGeminiWebSocket, WebSocketMessage } from './hooks/useGeminiWebSocket';
import { PromptInput, PromptInputActions, PromptInputAction, PromptInputTextarea } from "@/components/ui/prompt-input";
import { Button } from "@/components/ui/button";
import { Loader } from "@/components/ui/loader";
import { Markdown } from "@/components/ui/markdown";
import { ArrowUp, Square, X, History, BookOpen, Plus, FileText, HelpCircle } from "lucide-react";
import { 
  ChainOfThought, 
  ChainOfThoughtContent, 
  ChainOfThoughtItem, 
  ChainOfThoughtStep, 
  ChainOfThoughtTrigger 
} from "@/components/ui/chain-of-thought";
import { AssignmentForm, AssignmentData } from "./components/AssignmentForm";
import { CourseForm, CourseData } from "./components/CourseForm";
import CourseworkForm from "./components/CourseworkForm";
import AnnouncementsForm from "./components/AnnouncementsForm";
import { MessageWithLinks } from "./components/LinkButton";
import { ToolExecutionSteps } from "./components/ToolExecutionSteps";
import { useAuth } from "./contexts/AuthContext";
import ConversationHistory from "./components/ConversationHistory";

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

interface StudentList {
  id: string;
  department_name: string;
  department_year: string;
  section: string;
  emails: string[];
}

interface Message {
  id: string;
  role: 'user' | 'model';
  text: string;
  toolSteps?: ToolStep[];
  thoughts?: ThoughtStep[];
  showAssignmentForm?: boolean;
  showCourseworkForm?: boolean;
  showAnnouncementsForm?: boolean;
  assignmentCourseId?: string;
  assignmentCourses?: Course[];
  courseworkCourses?: Course[];
  announcementsCourses?: Course[];
  showCourseForm?: boolean;
  studentLists?: StudentList[];
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
  
  // Conversation History State
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || 'http://localhost:8001';
  
  // Track saved messages to prevent duplicates
  const savedMessagesRef = useRef<Set<string>>(new Set());
  const savingInProgressRef = useRef<Set<string>>(new Set());
  
  
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
                const isError = Boolean(message.result?.error);
                steps[stepIndex] = { 
                  ...steps[stepIndex], 
                  result: message.result, 
                  status: isError ? 'error' : 'completed' 
                };
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
            
            console.log('✅ [FORM] Adding assignment form to existing message');
            
            // Update the last model message (which has the tool steps) to add the form
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'model') {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  showAssignmentForm: true,
                  assignmentCourseId: courseId,
                  assignmentCourses: courses
                }
              ];
            }
            
            // Fallback: create new message if no model message exists
            return [
              ...prev,
              {
                id: `form-${Date.now()}`,
                role: 'model',
                text: '',
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
          
          const studentLists = message.data?.student_lists || [];
          console.log(`📚 [FORM] Student lists available: ${studentLists.length}`);
          
          setMessages(prev => {
            // Check if ANY message already has a course form (prevent duplicates)
            const hasExistingForm = prev.some(msg => msg.showCourseForm);
            if (hasExistingForm) {
              console.warn('⚠️ [FORM] Course form already exists, skipping duplicate');
              return prev;
            }
            
            console.log('✅ [FORM] Adding course form to existing message');
            
            // Update the last model message (which has the tool steps) to add the form
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'model') {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  showCourseForm: true,
                  studentLists: studentLists
                }
              ];
            }
            
            // Fallback: create new message if no model message exists
            return [
              ...prev,
              {
                id: `form-${Date.now()}`,
                role: 'model',
                text: '',
                showCourseForm: true,
                studentLists: studentLists
              }
            ];
          });
          setIsChatLoading(false);
          setIsToolProcessing(false);
          break;
        
        case 'show_coursework_form':
          // AI has decided to show the coursework selection form
          console.log('📋 [FORM] Received show_coursework_form');
          
          const courseworkCourses = message.data?.courses || [];
          console.log(`📋 [FORM] Courses available: ${courseworkCourses.length}`);
          
          setMessages(prev => {
            // Check if ANY message already has a coursework form (prevent duplicates)
            const hasExistingForm = prev.some(msg => msg.showCourseworkForm);
            if (hasExistingForm) {
              console.warn('⚠️ [FORM] Coursework form already exists, skipping duplicate');
              return prev;
            }
            
            console.log('✅ [FORM] Adding coursework form to existing message');
            
            // Update the last model message (which has the tool steps) to add the form
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'model') {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  showCourseworkForm: true,
                  courseworkCourses: courseworkCourses
                }
              ];
            }
            
            // Fallback: create new message if no model message exists
            return [
              ...prev,
              {
                id: `form-${Date.now()}`,
                role: 'model',
                text: '',
                showCourseworkForm: true,
                courseworkCourses: courseworkCourses
              }
            ];
          });
          setIsChatLoading(false);
          setIsToolProcessing(false);
          break;
        
        case 'show_announcements_form':
          // AI has decided to show the announcements selection form
          console.log('📢 [FORM] Received show_announcements_form');
          
          const announcementsCourses = message.data?.courses || [];
          console.log(`📢 [FORM] Courses available: ${announcementsCourses.length}`);
          
          setMessages(prev => {
            // Check if ANY message already has an announcements form (prevent duplicates)
            const hasExistingForm = prev.some(msg => msg.showAnnouncementsForm);
            if (hasExistingForm) {
              console.warn('⚠️ [FORM] Announcements form already exists, skipping duplicate');
              return prev;
            }
            
            console.log('✅ [FORM] Adding announcements form to existing message');
            
            // Update the last model message (which has the tool steps) to add the form
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'model') {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  showAnnouncementsForm: true,
                  announcementsCourses: announcementsCourses
                }
              ];
            }
            
            // Fallback: create new message if no model message exists
            return [
              ...prev,
              {
                id: `form-${Date.now()}`,
                role: 'model',
                text: '',
                showAnnouncementsForm: true,
                announcementsCourses: announcementsCourses
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

  // Auto-save AI responses to conversation
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.role === 'model' && lastMessage.text && currentConversationId) {
      // Save assistant message (debounced to avoid saving partial responses)
      const timer = setTimeout(() => {
        saveMessageToConversation(currentConversationId, 'assistant', lastMessage.text);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [messages, currentConversationId]);

  // Voice mode removed

  // Conversation History Functions
  const createNewConversation = async () => {
    if (!user?.email) return null;
    
    try {
      const response = await fetch(
        `${TOKEN_SERVICE_URL}/api/conversations?email=${encodeURIComponent(user.email)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ title: 'New Conversation' }),
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        return data.id;
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
    return null;
  };

  const saveMessageToConversation = async (conversationId: string, role: 'user' | 'assistant', content: string) => {
    if (!user?.email) return;
    
    // Create unique key for this message
    const messageKey = `${conversationId}:${role}:${content}`;
    
    // Check if already saved or currently saving
    if (savedMessagesRef.current.has(messageKey) || savingInProgressRef.current.has(messageKey)) {
      console.log('⏭️ Message already saved or saving, skipping:', messageKey.substring(0, 50));
      return;
    }
    
    // Mark as saving
    savingInProgressRef.current.add(messageKey);
    
    try {
      await fetch(
        `${TOKEN_SERVICE_URL}/api/conversations/${conversationId}/messages?email=${encodeURIComponent(user.email)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ role, content }),
        }
      );
      
      // Mark as saved
      savedMessagesRef.current.add(messageKey);
      console.log('✅ Message saved:', messageKey.substring(0, 50));
    } catch (error) {
      console.error('Error saving message:', error);
    } finally {
      // Remove from saving set
      savingInProgressRef.current.delete(messageKey);
    }
  };

  const loadConversation = async (conversationId: string) => {
    if (!user?.email) return;
    
    try {
      const response = await fetch(
        `${TOKEN_SERVICE_URL}/api/conversations/${conversationId}?email=${encodeURIComponent(user.email)}`
      );
      
      if (response.ok) {
        const data = await response.json();
        
        // Convert conversation messages to our Message format
        const loadedMessages: Message[] = data.messages.map((msg: any) => ({
          id: msg.id,
          role: msg.role === 'user' ? 'user' : 'model',
          text: msg.content,
        }));
        
        setMessages(loadedMessages);
        setCurrentConversationId(conversationId);
        
        // Clear and rebuild saved messages tracking
        savedMessagesRef.current.clear();
        savingInProgressRef.current.clear();
        
        // Mark all loaded messages as already saved
        data.messages.forEach((msg: any) => {
          const messageKey = `${conversationId}:${msg.role}:${msg.content}`;
          savedMessagesRef.current.add(messageKey);
        });
        
        console.log(`✅ Loaded conversation ${conversationId} with ${loadedMessages.length} messages`);
      }
    } catch (error) {
      console.error('Error loading conversation:', error);
    }
  };

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
    
    const userMessage = chatInput;
    
    // Send message to backend immediately - NO BLOCKING
    sendText(userMessage, threadId);
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text: userMessage }]);
    setChatInput("");
    setIsChatLoading(true);
    setIsToolProcessing(false);
    
    // Save to conversation history in background (non-blocking)
    if (!currentConversationId && messages.length === 0) {
      // Create conversation and save message in background
      createNewConversation().then(newConvId => {
        if (newConvId) {
          setCurrentConversationId(newConvId);
          saveMessageToConversation(newConvId, 'user', userMessage);
        }
      });
    } else if (currentConversationId) {
      // Save user message to existing conversation in background
      saveMessageToConversation(currentConversationId, 'user', userMessage);
    }
  };
  
  // Handle assignment form submission
  const handleAssignmentSubmit = async (messageId: string, data: AssignmentData) => {
    // Remove the form message
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
    
    // Upload files first if present
    let uploadedFiles: any[] = [];
    if (data.files && data.files.length > 0 && user) {
      console.log(`📁 Uploading ${data.files.length} file(s) to backend...`);
      
      // Add upload progress card to the messages
      const uploadStep: ToolStep = {
        tool: 'upload_files',
        args: { count: data.files.length },
        status: 'running'
      };
      
      setMessages(prev => {
        const lastMsg = prev[prev.length - 1];
        // If last message is from model and has tool steps, append to it
        if (lastMsg && lastMsg.role === 'model' && lastMsg.toolSteps) {
          return [...prev.slice(0, -1), { 
            ...lastMsg, 
            toolSteps: [...lastMsg.toolSteps, uploadStep] 
          }];
        }
        // Otherwise create new message with the upload step
        return [...prev, {
          id: Date.now().toString(),
          role: 'model',
          text: '',
          toolSteps: [uploadStep]
        }];
      });
      
      try {
        const idToken = await user.getIdToken();
        const formData = new FormData();
        
        // Add all files to form data
        data.files.forEach((file, index) => {
          formData.append(`file_${index}`, file);
        });
        
        // Upload files via HTTP endpoint
        const response = await fetch('http://localhost:8000/api/upload-files', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${idToken}`,
            'X-User-Email': user.email || ''
          },
          body: formData
        });
        
        if (response.ok) {
          const result = await response.json();
          uploadedFiles = result.files || [];
          console.log(`✅ Uploaded ${uploadedFiles.length} file(s)`);
          
          // Update upload step to completed
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'model' && lastMsg.toolSteps) {
              const steps = [...lastMsg.toolSteps];
              const uploadStepIndex = steps.findIndex(s => s.tool === 'upload_files' && s.status === 'running');
              if (uploadStepIndex !== -1) {
                steps[uploadStepIndex] = {
                  ...steps[uploadStepIndex],
                  result: { files: uploadedFiles },
                  status: 'completed'
                };
                return [...prev.slice(0, -1), { ...lastMsg, toolSteps: steps }];
              }
            }
            return prev;
          });
        } else {
          console.error('❌ File upload failed:', await response.text());
          
          // Update upload step to error
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'model' && lastMsg.toolSteps) {
              const steps = [...lastMsg.toolSteps];
              const uploadStepIndex = steps.findIndex(s => s.tool === 'upload_files' && s.status === 'running');
              if (uploadStepIndex !== -1) {
                steps[uploadStepIndex] = {
                  ...steps[uploadStepIndex],
                  result: { error: 'Upload failed' },
                  status: 'error'
                };
                return [...prev.slice(0, -1), { ...lastMsg, toolSteps: steps }];
              }
            }
            return prev;
          });
        }
      } catch (error) {
        console.error('❌ Error uploading files:', error);
        
        // Update upload step to error
        setMessages(prev => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === 'model' && lastMsg.toolSteps) {
            const steps = [...lastMsg.toolSteps];
            const uploadStepIndex = steps.findIndex(s => s.tool === 'upload_files' && s.status === 'running');
            if (uploadStepIndex !== -1) {
              steps[uploadStepIndex] = {
                ...steps[uploadStepIndex],
                result: { error: String(error) },
                status: 'error'
              };
              return [...prev.slice(0, -1), { ...lastMsg, toolSteps: steps }];
            }
          }
          return prev;
        });
      }
    }
    
    // Send assignment creation request through chat with file IDs only
    let assignmentMessage = `Create an assignment with the following details:
Course ID: ${data.course_id}
Title: ${data.title}
Description: ${data.description || 'N/A'}
Due Date: ${data.due_date || 'N/A'}
Due Time: ${data.due_time || 'N/A'}
Max Points: ${data.max_points}
Work Type: ${data.work_type}`;

    if (uploadedFiles.length > 0) {
      // Only send file IDs, not the full content
      assignmentMessage += `\nFile IDs: ${uploadedFiles.map(f => f.id).join(',')}`;
    }
    
    sendText(assignmentMessage, threadId);
    // Don't add a user message - let the tool execution show the progress
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
    let courseMessage = `Create a course with the following details:
Name: ${data.name}
Section: ${data.section || 'N/A'}
Description Heading: ${data.description_heading || 'N/A'}
Description: ${data.description || 'N/A'}
Room: ${data.room || 'N/A'}`;

    if (data.student_list_id) {
      courseMessage += `\nStudent List ID: ${data.student_list_id}`;
    }
    
    sendText(courseMessage, threadId);
    setMessages(prev => [...prev, { 
      id: Date.now().toString(), 
      role: 'user', 
      text: `Creating course: ${data.name}${data.student_list_id ? ' (with student invitations)' : ''}` 
    }]);
    setIsChatLoading(true);
  };
  
  const handleCourseworkSubmit = (courseId: string) => {
    // Remove the form from UI
    setMessages(prev => prev.map(msg => {
      if (msg.showCourseworkForm) {
        // Remove the form but keep the message structure
        const { showCourseworkForm, courseworkCourses, ...rest } = msg;
        return rest;
      }
      return msg;
    }));
    
    // Send request to list coursework for the selected course
    const message = `List all coursework for course ID: ${courseId}`;
    sendText(message, threadId);
    
    // Set loading state
    setIsChatLoading(true);
  };

  const handleAnnouncementsSubmit = (courseId: string) => {
    // Remove the form from UI
    setMessages(prev => prev.map(msg => {
      if (msg.showAnnouncementsForm) {
        // Remove the form but keep the message structure
        const { showAnnouncementsForm, announcementsCourses, ...rest } = msg;
        return rest;
      }
      return msg;
    }));
    
    // Send request to list announcements for the selected course
    const message = `List all announcements for course ID: ${courseId}`;
    sendText(message, threadId);
    
    // Set loading state
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

  // New Chat Handler
  const handleNewChat = () => {
    setMessages([]);
    setCurrentConversationId(null);
    setChatInput("");
    setIsChatLoading(false);
    setIsToolProcessing(false);
    // Clear saved messages tracking for new conversation
    savedMessagesRef.current.clear();
    savingInProgressRef.current.clear();
  };

  // Handle suggestion click - automatically submit
  const handleSuggestionClick = (suggestion: string) => {
    setChatInput(suggestion);
    // Auto-submit the suggestion
    setTimeout(() => {
      handleChatSubmit();
    }, 100);
  };

  // Chat View
    return (
      <div className="h-full bg-white text-gray-900 flex flex-col w-full relative">
        {/* Conversation History Sidebar */}
        <ConversationHistory
          isOpen={isHistoryOpen}
          onClose={() => setIsHistoryOpen(false)}
          onLoadConversation={loadConversation}
        />

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Sticky Header - Transparent */}
          <div className="sticky top-0 z-20 px-6 py-3">
            <div className="flex items-center justify-between w-full">
              {/* New Chat Button - Far Left */}
              <button
                onClick={handleNewChat}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition-colors shadow-sm"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                New Chat
              </button>

              {/* History Button - Far Right (no background) */}
              <button
                onClick={() => setIsHistoryOpen(true)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Chat History"
              >
                <History className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>

          {/* Main Content - Scrollable Area */}
          <main className="flex-1 overflow-y-auto overflow-x-hidden px-6 pt-6 pb-48 w-full">


          {messages.length === 0 ? (
            <div className="text-center max-w-2xl mx-auto mt-20 w-full">
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
                <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} gap-3`}>
                  {/* Tool Execution Steps - Stacked cards, no bubble */}
                  {msg.toolSteps && msg.toolSteps.length > 0 && msg.role === 'model' && (
                    <div className="w-full max-w-[85%]">
                      <ToolExecutionSteps steps={msg.toolSteps} />
                    </div>
                  )}
                  
                  {/* User messages: keep bubble */}
                  {msg.role === 'user' && (
                    <div className="max-w-[85%] rounded-2xl px-5 py-3 bg-gray-100 text-gray-900">
                      <Markdown className="markdown-content">
                        {msg.text}
                      </Markdown>
                    </div>
                  )}
                  
                  {/* AI messages: NO bubble, just plain text */}
                  {msg.role === 'model' && (
                    <>
                      {/* Thinking Steps - Plain text with collapsible */}
                    {msg.thoughts && msg.thoughts.length > 0 && (
                        <div className="w-full max-w-[85%]">
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
                    
                      {/* AI Text - Plain, no bubble */}
                      {msg.text && !msg.showAssignmentForm && !msg.showCourseForm && !msg.showCourseworkForm && !msg.showAnnouncementsForm && (
                        <div className="w-full max-w-[85%] text-gray-900">
                          {msg.text.match(/https:\/\/docs\.google\.com\/(forms|document|spreadsheets)/) ? (
                        <MessageWithLinks text={msg.text} />
                      ) : (
                        <Markdown className="markdown-content">
                        {msg.text}
                      </Markdown>
                          )}
                        </div>
                    )}
                    
                      {/* Assignment Form - Plain container */}
                      {msg.showAssignmentForm && (
                        <div className="w-full max-w-[85%]">
                        <AssignmentForm
                          courseId={msg.assignmentCourseId}
                          courses={msg.assignmentCourses}
                          onSubmit={(data) => handleAssignmentSubmit(msg.id, data)}
                          onCancel={() => handleAssignmentCancel(msg.id)}
                        />
                      </div>
                    )}
                    
                      {/* Course Form - Plain container */}
                      {msg.showCourseForm && (
                        <div className="w-full max-w-[85%]">
                        <CourseForm
                          onSubmit={(data) => handleCourseSubmit(msg.id, data)}
                          onCancel={() => handleCourseCancel(msg.id)}
                            studentLists={msg.studentLists}
                          />
                        </div>
                      )}
                      
                      {/* Coursework Form - Plain container */}
                      {msg.showCourseworkForm && (
                        <div className="w-full max-w-[85%]">
                          <CourseworkForm
                            courses={msg.courseworkCourses || []}
                            onSubmit={handleCourseworkSubmit}
                        />
                      </div>
                    )}
                      
                      {/* Announcements Form - Plain container */}
                      {msg.showAnnouncementsForm && (
                        <div className="w-full max-w-[85%]">
                          <AnnouncementsForm
                            courses={msg.announcementsCourses || []}
                            onSubmit={handleAnnouncementsSubmit}
                          />
                  </div>
                      )}
                    </>
                  )}
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
              {/* Extra spacer to ensure content is visible above fixed input */}
              <div className="h-40" />
              <div ref={chatEndRef} />
            </div>
          )}
        </main>

        {/* Fixed Right Side Suggestions - Always visible */}
        <div className="fixed right-6 top-1/2 transform -translate-y-1/2 z-20 flex flex-col gap-3">
          <button
            onClick={() => handleSuggestionClick('List my courses')}
            className="flex items-center gap-2 px-4 py-3 rounded-full bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 hover:text-gray-800 transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md whitespace-nowrap"
            title="List my courses"
          >
            <BookOpen className="w-4 h-4" />
            List my courses
          </button>
          <button
            onClick={() => handleSuggestionClick('Create a course')}
            className="flex items-center gap-2 px-4 py-3 rounded-full bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 hover:text-gray-800 transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md whitespace-nowrap"
            title="Create a course"
          >
            <Plus className="w-4 h-4" />
            Create a course
          </button>
          <button
            onClick={() => handleSuggestionClick('Create an Assignment')}
            className="flex items-center gap-2 px-4 py-3 rounded-full bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 hover:text-gray-800 transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md whitespace-nowrap"
            title="Create an Assignment"
          >
            <FileText className="w-4 h-4" />
            Create an Assignment
          </button>
          <button
            onClick={() => handleSuggestionClick('What are you abilities?')}
            className="flex items-center gap-2 px-4 py-3 rounded-full bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 hover:text-gray-800 transition-all duration-200 text-sm font-medium shadow-sm hover:shadow-md whitespace-nowrap"
            title="What are you abilities?"
          >
            <HelpCircle className="w-4 h-4" />
            What are you abilities?
          </button>
        </div>

          {/* Fixed Bottom Input - Always at bottom, never expands */}
          <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-30 max-h-32">
            <div className="max-w-3xl mx-auto px-6 py-4">
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
      </div>
    );
}
