"use client";

import { useState, useEffect, useRef } from 'react';
import { useGeminiWebSocket, WebSocketMessage } from './hooks/useGeminiWebSocket';
import { useAudioCapture } from './hooks/useAudioCapture';
import { useAudioPlayback } from './hooks/useAudioPlayback';
import { PromptInput, PromptInputActions, PromptInputAction, PromptInputTextarea } from "@/components/ui/prompt-input";
import { Button } from "@/components/ui/button";
import { ArrowUp, Square, Mic, X } from "lucide-react";
import { 
  ChainOfThought, 
  ChainOfThoughtContent, 
  ChainOfThoughtItem, 
  ChainOfThoughtStep, 
  ChainOfThoughtTrigger 
} from "@/components/ui/chain-of-thought";

interface ToolStep {
  tool: string;
  args?: any;
  result?: any;
  status: 'running' | 'completed' | 'error';
}

interface Message {
  id: string;
  role: 'user' | 'model';
  text: string;
  toolSteps?: ToolStep[];
}

export default function Home() {
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [statusText, setStatusText] = useState('I\'m here and ready to help. Just let me know what you need.');
  
  // Chat State
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

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
          setStatusText(`Error: ${message.data}`);
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
        case 'text_chunk':
          setIsChatLoading(false);
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
           setMessages(prev => [...prev, { id: Date.now().toString(), role: 'model', text: `Error: ${message.text || 'Unknown error'}` }]);
           setIsChatLoading(false);
           break;
      }
  });

  // Auto-connect Chat on mount
  useEffect(() => {
    connectChat();
  }, [connectChat]);

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
        connectChat();
        // Maybe wait or show error? For now, we try to send. 
        // Ideally wait for connect. But simple UX:
        setTimeout(() => sendText(chatInput), 500); 
    } else {
        sendText(chatInput);
    }
    
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text: chatInput }]);
    setChatInput("");
    setIsChatLoading(true);
  };

  // Scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
                <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-5 py-3 ${
                    msg.role === 'user' 
                      ? 'bg-gray-100 text-gray-900' 
                      : 'bg-white border border-gray-200 text-gray-900'
                  }`}>
                    {msg.toolSteps && msg.toolSteps.length > 0 && (
                      <div className="mb-4 w-full">
                        <ChainOfThought>
                          {msg.toolSteps.map((step, idx) => (
                            <ChainOfThoughtStep key={idx} status={step.status}>
                               <ChainOfThoughtTrigger className="text-xs text-gray-700">
                                  {step.status === 'running' ? 'Executing' : 'Used'} tool: <span className="font-mono text-blue-600">{step.tool}</span>
                               </ChainOfThoughtTrigger>
                               <ChainOfThoughtContent>
                                  <ChainOfThoughtItem>
                                    <span className="text-xs font-mono text-gray-600">Input:</span>
                                    <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto border border-gray-200">
                                      {JSON.stringify(step.args, null, 2)}
                                    </pre>
                                  </ChainOfThoughtItem>
                                  {step.result && (
                                    <ChainOfThoughtItem>
                                      <span className="text-xs font-mono text-gray-600">Result:</span>
                                      <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-x-auto border border-gray-200 text-green-700">
                                        {JSON.stringify(step.result, null, 2)}
                                      </pre>
                                    </ChainOfThoughtItem>
                                  )}
                               </ChainOfThoughtContent>
                            </ChainOfThoughtStep>
                          ))}
                        </ChainOfThought>
                      </div>
                    )}
                    
                    <div className="whitespace-pre-wrap leading-relaxed">
                      {msg.text}
                    </div>
                  </div>
                </div>
              ))}
              
              {isChatLoading && (
                <div className="flex items-start">
                   <div className="bg-white border border-gray-200 rounded-2xl px-5 py-3 flex items-center space-x-2">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                   </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          )}
        </main>

        {/* Fixed Bottom Input */}
        <div className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-sm border-t border-gray-200 p-6">
          <div className="max-w-3xl mx-auto">
            <PromptInput
              value={chatInput}
              onValueChange={setChatInput}
              isLoading={isChatLoading}
              onSubmit={handleChatSubmit}
              className="w-full"
            >
              <PromptInputTextarea 
                placeholder="Ask anything..." 
                className="bg-white border-gray-300 text-gray-900 placeholder-gray-400 min-h-[60px] focus:border-gray-400 focus:ring-0"
              />
              <PromptInputActions className="justify-end pt-2">
                <PromptInputAction
                  tooltip={isChatLoading ? "Thinking..." : "Send message"}
                >
                  <Button
                    variant="default"
                    size="icon"
                    className="h-8 w-8 rounded-full bg-gray-900 hover:bg-gray-800 text-white"
                    onClick={handleChatSubmit}
                    disabled={isChatLoading}
                  >
                    {isChatLoading ? (
                      <Square className="size-4 fill-current" />
                    ) : (
                      <ArrowUp className="size-4" />
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
