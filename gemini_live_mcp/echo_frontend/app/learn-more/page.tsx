"use client";

import { useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import {
    Sparkles,
    Monitor,
    Terminal,
    Globe,
    Mic,
    Zap,
    Brain,
    Shield,
    Cpu,
    HardDrive,
    Wifi,
    ArrowLeft,
    Play,
    CheckCircle,
    Keyboard,
    MousePointer,
    MessageSquare
} from "lucide-react";

export default function LearnMorePage() {
    const router = useRouter();

    return (
        <div className="min-h-screen bg-white flex flex-col">
            {/* Header */}
            <header className="border-b border-gray-100 sticky top-0 bg-white/80 backdrop-blur-sm z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xl font-semibold text-gray-900">Echo</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <Button
                                onClick={() => router.push('/landing')}
                                variant="ghost"
                                className="text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                            >
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back
                            </Button>
                            <Button
                                onClick={() => router.push('/login')}
                                className="bg-gray-900 hover:bg-gray-800 text-white"
                            >
                                Try Web Version
                            </Button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 py-12 px-4 sm:px-6 lg:px-8">
                <div className="max-w-6xl mx-auto">

                    {/* Hero */}
                    <div className="text-center mb-16">
                        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
                            One AI. Three Interfaces.
                        </h1>
                        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                            Echo adapts to your workflow — whether you prefer voice control on desktop,
                            a terminal interface, or a web chat experience.
                        </p>
                    </div>

                    {/* Product Grid */}
                    <div className="grid lg:grid-cols-2 gap-8 mb-20">

                        {/* Desktop + TUI Combined Card */}
                        <div className="lg:col-span-1 bg-gradient-to-br from-purple-50 to-violet-50 rounded-3xl p-8 border border-purple-100 relative overflow-hidden">
                            <div className="absolute top-4 right-4">
                                <span className="bg-purple-600 text-white text-xs px-3 py-1 rounded-full font-medium">
                                    Windows Only
                                </span>
                            </div>

                            <div className="flex items-center gap-3 mb-6">
                                <div className="w-12 h-12 bg-purple-600 rounded-xl flex items-center justify-center">
                                    <Monitor className="w-6 h-6 text-white" />
                                </div>
                                <div className="w-12 h-12 bg-violet-600 rounded-xl flex items-center justify-center">
                                    <Terminal className="w-6 h-6 text-white" />
                                </div>
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-900">Desktop & TUI</h2>
                                    <p className="text-sm text-purple-600 font-medium">Voice-Controlled Desktop Automation</p>
                                </div>
                            </div>

                            <p className="text-gray-700 mb-6">
                                Control your Windows desktop with voice commands. Launch apps, automate tasks,
                                and diagnose system issues — all hands-free powered by Gemini Live.
                            </p>

                            {/* Video Placeholder */}
                            <div className="bg-gray-900 rounded-2xl aspect-video mb-6 flex items-center justify-center relative overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 to-violet-900/20"></div>
                                <div className="text-center z-10">
                                    <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-3 backdrop-blur-sm">
                                        <Play className="w-8 h-8 text-white ml-1" />
                                    </div>
                                    <p className="text-white/80 text-sm">Demo Video Coming Soon</p>
                                </div>
                                {/* TUI Preview Overlay */}
                                <div className="absolute bottom-4 left-4 right-4 bg-gray-950/90 rounded-lg p-3 font-mono text-xs">
                                    <div className="flex items-center gap-2 text-purple-400 mb-1">
                                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                                        🎙️ Listening...
                                    </div>
                                    <div className="text-gray-400">
                                        <span className="text-violet-400">User:</span> "Open Chrome and search for weather"
                                    </div>
                                </div>
                            </div>

                            {/* Key Features */}
                            <div className="space-y-3 mb-6">
                                <div className="flex items-start gap-3">
                                    <Mic className="w-5 h-5 text-purple-600 mt-0.5" />
                                    <div>
                                        <p className="font-medium text-gray-900">Real-time Voice Control</p>
                                        <p className="text-sm text-gray-600">Talk naturally with Gemini Live API. No wake words, just speak.</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3">
                                    <Brain className="w-5 h-5 text-purple-600 mt-0.5" />
                                    <div>
                                        <p className="font-medium text-gray-900">Intelligent Task Routing</p>
                                        <p className="text-sm text-gray-600">Simple tasks execute instantly. Complex tasks trigger multi-agent planning.</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3">
                                    <Zap className="w-5 h-5 text-purple-600 mt-0.5" />
                                    <div>
                                        <p className="font-medium text-gray-900">11 Desktop Automation Tools</p>
                                        <p className="text-sm text-gray-600">Launch apps, type text, click, scroll, run PowerShell, and more via Windows-MCP.</p>
                                    </div>
                                </div>
                            </div>

                            {/* Two Interface Options */}
                            <div className="grid grid-cols-2 gap-4 mb-6">
                                <div className="bg-white rounded-xl p-4 border border-purple-200">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Monitor className="w-5 h-5 text-purple-600" />
                                        <span className="font-medium text-gray-900">Electron App</span>
                                    </div>
                                    <ul className="text-sm text-gray-600 space-y-1">
                                        <li className="flex items-center gap-1">
                                            <CheckCircle className="w-3 h-3 text-green-500" />
                                            Alt+Space hotkey
                                        </li>
                                        <li className="flex items-center gap-1">
                                            <CheckCircle className="w-3 h-3 text-green-500" />
                                            Minimal floating UI
                                        </li>
                                        <li className="flex items-center gap-1">
                                            <CheckCircle className="w-3 h-3 text-green-500" />
                                            Mode toggle (Fast/Reasoning)
                                        </li>
                                    </ul>
                                </div>
                                <div className="bg-white rounded-xl p-4 border border-violet-200">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Terminal className="w-5 h-5 text-violet-600" />
                                        <span className="font-medium text-gray-900">TUI Mode</span>
                                    </div>
                                    <ul className="text-sm text-gray-600 space-y-1">
                                        <li className="flex items-center gap-1">
                                            <CheckCircle className="w-3 h-3 text-green-500" />
                                            Rich terminal UI
                                        </li>
                                        <li className="flex items-center gap-1">
                                            <CheckCircle className="w-3 h-3 text-green-500" />
                                            Split-pane layout
                                        </li>
                                        <li className="flex items-center gap-1">
                                            <CheckCircle className="w-3 h-3 text-green-500" />
                                            Real-time thinking trace
                                        </li>
                                    </ul>
                                </div>
                            </div>

                            {/* System Tools */}
                            <div className="bg-white/80 rounded-xl p-4 border border-purple-200">
                                <p className="text-sm font-medium text-gray-900 mb-3">+ System Diagnosis Tools (15 MCP Tools)</p>
                                <div className="flex flex-wrap gap-2">
                                    <span className="inline-flex items-center gap-1 text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
                                        <Cpu className="w-3 h-3" /> CPU Monitor
                                    </span>
                                    <span className="inline-flex items-center gap-1 text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
                                        <HardDrive className="w-3 h-3" /> Disk Usage
                                    </span>
                                    <span className="inline-flex items-center gap-1 text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
                                        <Wifi className="w-3 h-3" /> Network
                                    </span>
                                    <span className="inline-flex items-center gap-1 text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
                                        <Shield className="w-3 h-3" /> Security
                                    </span>
                                    <span className="text-xs text-gray-500">+11 more</span>
                                </div>
                            </div>
                        </div>

                        {/* Web Version Card */}
                        <div className="lg:col-span-1 bg-gradient-to-br from-gray-50 to-slate-50 rounded-3xl p-8 border border-gray-200 relative overflow-hidden">
                            <div className="absolute top-4 right-4">
                                <span className="bg-gray-900 text-white text-xs px-3 py-1 rounded-full font-medium">
                                    Cross-Platform
                                </span>
                            </div>

                            <div className="flex items-center gap-3 mb-6">
                                <div className="w-12 h-12 bg-gray-900 rounded-xl flex items-center justify-center">
                                    <Globe className="w-6 h-6 text-white" />
                                </div>
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-900">Web Version</h2>
                                    <p className="text-sm text-gray-600 font-medium">Google Classroom AI Assistant</p>
                                </div>
                            </div>

                            <p className="text-gray-700 mb-6">
                                Manage your Google Classroom with natural language. Create assignments,
                                organize courses, and check student progress through chat.
                            </p>

                            {/* Video Placeholder */}
                            <div className="bg-gray-900 rounded-2xl aspect-video mb-6 flex items-center justify-center relative overflow-hidden">
                                <div className="absolute inset-0 bg-gradient-to-br from-gray-800/20 to-slate-800/20"></div>
                                <div className="text-center z-10">
                                    <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-3 backdrop-blur-sm">
                                        <Play className="w-8 h-8 text-white ml-1" />
                                    </div>
                                    <p className="text-white/80 text-sm">Demo Video Coming Soon</p>
                                </div>
                                {/* Chat Preview */}
                                <div className="absolute bottom-4 left-4 right-4 bg-white/95 rounded-lg p-3 text-xs">
                                    <div className="flex items-start gap-2">
                                        <div className="w-6 h-6 bg-gray-900 rounded-full flex items-center justify-center flex-shrink-0">
                                            <Sparkles className="w-3 h-3 text-white" />
                                        </div>
                                        <div className="text-gray-700">
                                            Created assignment <span className="font-medium">"Math Quiz Ch.5"</span> in
                                            <span className="font-medium"> Algebra 101</span>, due Friday at 3pm.
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Key Features */}
                            <div className="space-y-3 mb-6">
                                <div className="flex items-start gap-3">
                                    <MessageSquare className="w-5 h-5 text-gray-700 mt-0.5" />
                                    <div>
                                        <p className="font-medium text-gray-900">Natural Language Chat</p>
                                        <p className="text-sm text-gray-600">Just type what you want: "Create an assignment for Math class due Friday"</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3">
                                    <Zap className="w-5 h-5 text-gray-700 mt-0.5" />
                                    <div>
                                        <p className="font-medium text-gray-900">Instant Classroom Actions</p>
                                        <p className="text-sm text-gray-600">Create courses, assignments, announcements — all through conversation.</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-3">
                                    <Shield className="w-5 h-5 text-gray-700 mt-0.5" />
                                    <div>
                                        <p className="font-medium text-gray-900">Secure OAuth Integration</p>
                                        <p className="text-sm text-gray-600">Connect your Google account securely. No passwords stored.</p>
                                    </div>
                                </div>
                            </div>

                            {/* CTA */}
                            <Button
                                onClick={() => router.push('/login')}
                                className="w-full bg-gray-900 hover:bg-gray-800 text-white py-6 rounded-xl"
                            >
                                Try Web Version Now
                            </Button>
                        </div>
                    </div>

                    {/* Architecture Section */}
                    <section className="mb-20">
                        <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">Shared Architecture</h2>
                        <div className="bg-gray-50 rounded-2xl p-8 border border-gray-200">
                            <div className="grid md:grid-cols-3 gap-6 text-center">
                                <div>
                                    <div className="w-14 h-14 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                        <Brain className="w-7 h-7 text-purple-600" />
                                    </div>
                                    <h3 className="font-semibold text-gray-900 mb-2">Gemini AI Core</h3>
                                    <p className="text-sm text-gray-600">
                                        Powered by Gemini 2.5 Flash for fast reasoning and Gemini Live for real-time voice.
                                    </p>
                                </div>
                                <div>
                                    <div className="w-14 h-14 bg-violet-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                        <Zap className="w-7 h-7 text-violet-600" />
                                    </div>
                                    <h3 className="font-semibold text-gray-900 mb-2">MCP Protocol</h3>
                                    <p className="text-sm text-gray-600">
                                        Model Context Protocol enables seamless tool integration for desktop and web actions.
                                    </p>
                                </div>
                                <div>
                                    <div className="w-14 h-14 bg-pink-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                        <Sparkles className="w-7 h-7 text-pink-600" />
                                    </div>
                                    <h3 className="font-semibold text-gray-900 mb-2">Multi-Agent Graph</h3>
                                    <p className="text-sm text-gray-600">
                                        LangGraph-powered planning for complex multi-step task execution.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Example Commands */}
                    <section className="mb-16">
                        <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">What You Can Say</h2>
                        <div className="grid md:grid-cols-2 gap-6">
                            <div className="bg-purple-50 rounded-2xl p-6 border border-purple-100">
                                <div className="flex items-center gap-2 mb-4">
                                    <Monitor className="w-5 h-5 text-purple-600" />
                                    <span className="font-semibold text-gray-900">Desktop & TUI</span>
                                </div>
                                <div className="space-y-3 font-mono text-sm">
                                    <div className="bg-white rounded-lg p-3 border border-purple-200">
                                        <span className="text-purple-600">"</span>Open Chrome and search for the weather<span className="text-purple-600">"</span>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-purple-200">
                                        <span className="text-purple-600">"</span>Why is my computer running slow?<span className="text-purple-600">"</span>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-purple-200">
                                        <span className="text-purple-600">"</span>Organize my downloads folder by file type<span className="text-purple-600">"</span>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-purple-200">
                                        <span className="text-purple-600">"</span>Check if my Windows is up to date<span className="text-purple-600">"</span>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-200">
                                <div className="flex items-center gap-2 mb-4">
                                    <Globe className="w-5 h-5 text-gray-700" />
                                    <span className="font-semibold text-gray-900">Web Version</span>
                                </div>
                                <div className="space-y-3 font-mono text-sm">
                                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                                        <span className="text-gray-500">"</span>Show all my courses<span className="text-gray-500">"</span>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                                        <span className="text-gray-500">"</span>Create an assignment for Math class due Friday<span className="text-gray-500">"</span>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                                        <span className="text-gray-500">"</span>Post an announcement to Science 101<span className="text-gray-500">"</span>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                                        <span className="text-gray-500">"</span>What assignments are due this week?<span className="text-gray-500">"</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* CTA */}
                    <section className="text-center bg-gradient-to-r from-purple-50 to-violet-50 rounded-3xl p-10 border border-purple-100">
                        <h2 className="text-2xl font-bold text-gray-900 mb-4">Ready to try Echo?</h2>
                        <p className="text-gray-600 mb-8 max-w-xl mx-auto">
                            Start with the Web version right now, or clone the repo to run Desktop/TUI locally.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <Button
                                onClick={() => router.push('/login')}
                                size="lg"
                                className="bg-gray-900 hover:bg-gray-800 text-white px-8 py-6 text-lg rounded-xl"
                            >
                                Try Web Version
                            </Button>
                            <Button
                                variant="outline"
                                size="lg"
                                onClick={() => window.open('https://github.com/Precision-Recall/Echo', '_blank')}
                                className="border-gray-300 text-gray-700 hover:bg-white px-8 py-6 text-lg rounded-xl"
                            >
                                View on GitHub
                            </Button>
                        </div>
                    </section>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-gray-100 py-8">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <p className="text-center text-gray-500 text-sm">
                        © 2025 Echo • Built by Precision-Recall • Powered by Gemini AI & MCP
                    </p>
                </div>
            </footer>
        </div>
    );
}
