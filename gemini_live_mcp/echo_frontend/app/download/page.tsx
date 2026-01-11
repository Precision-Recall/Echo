"use client";

import { Button } from "@/components/ui/button";
import { Monitor, Terminal, Apple, ArrowLeft } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

// TODO: Replace these with your actual Google Drive direct download links
// To get direct download link: 
// 1. Upload file to Google Drive
// 2. Right click > Share > Anyone with link
// 3. Copy link, it looks like: https://drive.google.com/file/d/FILE_ID/view
// 4. Convert to direct download: https://drive.google.com/uc?export=download&id=FILE_ID

const DOWNLOAD_LINKS = {
    windows: "https://drive.google.com/uc?export=download&id=12CraNnmE0DSOci3ajSrYLAG0SflopMi2",
    linux: "https://drive.google.com/uc?export=download&id=YOUR_LINUX_FILE_ID",
    mac: "https://drive.google.com/uc?export=download&id=YOUR_MAC_FILE_ID",
};

export default function DownloadPage() {
    return (
        <div className="min-h-screen bg-white flex flex-col">
            {/* Header */}
            <header className="border-b border-gray-100">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center gap-3">
                            <Image
                                src="/logo.png"
                                alt="Echo Logo"
                                width={40}
                                height={40}
                                className="rounded-lg"
                            />
                            <span className="text-xl font-semibold text-gray-900">Echo</span>
                        </div>
                        <Link href="/landing">
                            <Button
                                variant="ghost"
                                className="text-gray-700 hover:text-gray-900 hover:bg-gray-50"
                            >
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back
                            </Button>
                        </Link>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 py-12">
                <div className="max-w-4xl mx-auto text-center">
                    <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
                        Download Echo Desktop
                    </h1>
                    <p className="text-lg text-gray-600 mb-12 max-w-2xl mx-auto">
                        Voice-controlled desktop automation powered by Gemini. Choose your platform below.
                    </p>

                    {/* Download Cards */}
                    <div className="grid md:grid-cols-3 gap-6">
                        {/* Windows */}
                        <div className="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:border-gray-300 transition-colors">
                            <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center mx-auto mb-6 border border-gray-200">
                                <Monitor className="w-8 h-8 text-gray-900" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Windows</h3>
                            <p className="text-gray-500 text-sm mb-6">Windows 10 or later</p>
                            <a href={DOWNLOAD_LINKS.windows} target="_blank" rel="noopener noreferrer">
                                <Button className="w-full bg-gray-900 hover:bg-gray-800 text-white rounded-xl">
                                    Download .exe
                                </Button>
                            </a>
                        </div>

                        {/* Linux */}
                        <div className="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:border-gray-300 transition-colors">
                            <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center mx-auto mb-6 border border-gray-200">
                                <Terminal className="w-8 h-8 text-gray-900" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">Linux</h3>
                            <p className="text-gray-500 text-sm mb-6">AppImage for all distros</p>
                            <a href={DOWNLOAD_LINKS.linux} target="_blank" rel="noopener noreferrer">
                                <Button className="w-full bg-gray-900 hover:bg-gray-800 text-white rounded-xl">
                                    Download .AppImage
                                </Button>
                            </a>
                        </div>

                        {/* macOS */}
                        <div className="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:border-gray-300 transition-colors">
                            <div className="w-16 h-16 bg-white rounded-xl flex items-center justify-center mx-auto mb-6 border border-gray-200">
                                <Apple className="w-8 h-8 text-gray-900" />
                            </div>
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">macOS</h3>
                            <p className="text-gray-500 text-sm mb-6">macOS 11 or later</p>
                            <a href={DOWNLOAD_LINKS.mac} target="_blank" rel="noopener noreferrer">
                                <Button className="w-full bg-gray-900 hover:bg-gray-800 text-white rounded-xl">
                                    Download .dmg
                                </Button>
                            </a>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-gray-100 py-8">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <p className="text-center text-gray-500 text-sm">
                        © 2025 Echo. Powered by Gemini AI.
                    </p>
                </div>
            </footer>
        </div>
    );
}
