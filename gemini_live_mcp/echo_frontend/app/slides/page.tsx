"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/app/contexts/AuthContext';
import { ProtectedRoute } from '@/app/components/ProtectedRoute';
import { SidebarProvider, useSidebar } from "@/components/ui/sidebar";
import { AppSidebar } from "@/app/components/AppSidebar";
import { SidebarInset } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, Sparkles, Edit2, Presentation, ExternalLink, RefreshCw, GripVertical, X, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";

// Declare puter for TypeScript
declare global {
  interface Window {
    puter: any;
  }
}

interface SlideData {
  title: string;
  content: string;  // Points or summary text
  has_image: boolean;
  image_prompt?: string;
  layout_type: 'points' | 'summary';
}

interface OutlineData {
  title: string;
  subtitle: string;
  title_image_prompt?: string;
  slides: SlideData[];
}

function SlidesContentWrapper() {
  const { setOpen } = useSidebar();

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (e.clientX <= 80) {
        setOpen(true);
      } else if (e.clientX > 280) {
        setOpen(false);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [setOpen]);

  return (
    <SidebarInset>
      <SlidesContent />
    </SidebarInset>
  );
}

export default function SlidesPage() {
  const [isPuterLoaded, setIsPuterLoaded] = useState(false);

  useEffect(() => {
    // Check if Puter is already loaded
    if (window.puter) {
      console.log('✅ Puter.js already loaded');
      setIsPuterLoaded(true);
      return;
    }

    // Check if script is already being loaded
    const existingScript = document.querySelector('script[src="https://js.puter.com/v2/"]');
    if (existingScript) {
      console.log('⏳ Puter.js already loading...');
      existingScript.addEventListener('load', () => {
        console.log('✅ Puter.js loaded successfully');
        setIsPuterLoaded(true);
      });
      return;
    }

    // Load Puter.js dynamically
    console.log('📥 Loading Puter.js...');
    const script = document.createElement('script');
    script.src = 'https://js.puter.com/v2/';
    script.async = true;
    script.onload = () => {
      console.log('✅ Puter.js loaded successfully');
      setIsPuterLoaded(true);
    };
    script.onerror = () => {
      console.error('❌ Failed to load Puter.js');
      setIsPuterLoaded(false);
    };
    document.head.appendChild(script);

    // No cleanup - keep the script loaded for the session
  }, []);

  return (
    <ProtectedRoute>
      <SidebarProvider defaultOpen={false} style={{ "--sidebar-width": "16rem" } as React.CSSProperties}>
        <AppSidebar />
        <SlidesContentWrapper />
      </SidebarProvider>
    </ProtectedRoute>
  );
}

function SlidesContent() {
  const { user } = useAuth();
  const [step, setStep] = useState(1); // 1: Input, 2: Outline, 3: Generation
  const [topic, setTopic] = useState("");
  const [numSlides, setNumSlides] = useState("5");
  const [isGeneratingOutline, setIsGeneratingOutline] = useState(false);
  const [outline, setOutline] = useState<OutlineData | null>(null);
  const [isGeneratingPresentation, setIsGeneratingPresentation] = useState(false);
  const [generationProgress, setGenerationProgress] = useState("");
  const [presentationUrl, setPresentationUrl] = useState("");
  const [viewUrl, setViewUrl] = useState("");

  const handleGenerateOutline = async () => {
    if (!topic.trim() || !user?.email) return;

    setIsGeneratingOutline(true);
    try {
      const idToken = await user.getIdToken();
      const response = await fetch('http://localhost:8000/api/slides/generate-outline', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`,
          'X-User-Email': user.email,
        },
        body: JSON.stringify({
          topic: topic,
          num_slides: parseInt(numSlides),
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setOutline(data);
        setStep(2);
      } else {
        const errorData = await response.json();
        alert(`Failed to generate outline: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Error generating outline:', error);
      alert('Error generating outline');
    } finally {
      setIsGeneratingOutline(false);
    }
  };

  const handleGeneratePresentation = async () => {
    if (!outline || !user?.email) return;

    setIsGeneratingPresentation(true);
    setStep(3);
    
    try {
      let titleImageId: string | null = null;
      
      // Step 0: Generate title background image
      if (outline.title_image_prompt && window.puter?.ai?.txt2img) {
        setGenerationProgress('Generating title background...');
        try {
          console.log('🎨 Generating title background image');
          const titleImage = await window.puter.ai.txt2img(
            outline.title_image_prompt || "Abstract professional dark blue gradient background",
            { model: "black-forest-labs/FLUX.1-schnell" }
          );
          
          // Wait for image load with timeout
          if (titleImage && titleImage.complete === false) {
            await Promise.race([
              new Promise(resolve => { titleImage.onload = resolve; }),
              new Promise((_, reject) => setTimeout(() => reject(new Error('Image load timeout')), 30000))
            ]);
          }
          
          if (titleImage && (titleImage.naturalWidth || titleImage.width)) {
            const canvas = document.createElement('canvas');
            canvas.width = titleImage.naturalWidth || titleImage.width || 1920;
            canvas.height = titleImage.naturalHeight || titleImage.height || 1080;
            const ctx = canvas.getContext('2d');
            if (ctx) {
              ctx.drawImage(titleImage, 0, 0);
              const blob = await new Promise<Blob>((resolve, reject) => {
                canvas.toBlob(b => b ? resolve(b) : reject(new Error('Blob failed')), 'image/png');
              });
              
              const idToken = await user.getIdToken();
              const formData = new FormData();
              formData.append('title_bg', blob, 'title_background.png');
              
              const uploadResponse = await fetch('http://localhost:8000/api/upload-files', {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${idToken}`,
                  'X-User-Email': user.email,
                },
                body: formData,
              });
              
              if (uploadResponse.ok) {
                const uploadData = await uploadResponse.json();
                if (uploadData.files?.[0]?.id) {
                  titleImageId = uploadData.files[0].id;
                  console.log('✅ Title background uploaded:', titleImageId);
                }
              }
            }
          }
        } catch (error) {
          console.warn('⚠️ Skipping title background (generation failed):', error instanceof Error ? error.message : 'Unknown error');
          // Continue without title background image
        }
      }
      
      // Step 1: Generate images for slides that need them
      const slidesWithImages = outline.slides.filter(slide => slide.has_image);
      const imageFileIds: string[] = [];
      
      if (slidesWithImages.length > 0) {
        setGenerationProgress(`Generating images... (0/${slidesWithImages.length})`);
        
        for (let i = 0; i < slidesWithImages.length; i++) {
          const slide = slidesWithImages[i];
          
          try {
            // Check if Puter.js is loaded
            if (!window.puter || !window.puter.ai || !window.puter.ai.txt2img) {
              console.warn('⚠️ Puter.js not loaded, skipping image generation');
              setGenerationProgress(`Skipping images (Puter.js not available)...`);
              break; // Skip all image generation
            }
            
            // Generate image with Puter.js Flux
            console.log(`🎨 Generating image ${i + 1}/${slidesWithImages.length}: ${slide.image_prompt}`);
            const imageElement = await window.puter.ai.txt2img(
              slide.image_prompt || "Professional abstract background",
              { model: "black-forest-labs/FLUX.1-schnell" }
            );
            
            // Wait for image to load
            if (imageElement.complete === false) {
              await new Promise(resolve => {
                imageElement.onload = resolve;
              });
            }
            
            // Convert image to blob
            const canvas = document.createElement('canvas');
            canvas.width = imageElement.naturalWidth || imageElement.width;
            canvas.height = imageElement.naturalHeight || imageElement.height;
            const ctx = canvas.getContext('2d');
            if (!ctx) {
              console.error('Failed to get canvas context');
              continue;
            }
            ctx.drawImage(imageElement, 0, 0);
            
            const blob = await new Promise<Blob>((resolve, reject) => {
              canvas.toBlob((blob) => {
                if (blob) resolve(blob);
                else reject(new Error('Failed to create blob'));
              }, 'image/png');
            });
            
            // Upload to Google Drive
            const idToken = await user.getIdToken();
            const formData = new FormData();
            formData.append(`image_${i}`, blob, `slide_image_${i}.png`);
            
            const uploadResponse = await fetch('http://localhost:8000/api/upload-files', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${idToken}`,
                'X-User-Email': user.email,
              },
              body: formData,
            });
            
            if (uploadResponse.ok) {
              const uploadData = await uploadResponse.json();
              // Response format: { success: true, files: [{id, title, mimeType}], count }
              if (uploadData.files && uploadData.files.length > 0) {
                imageFileIds.push(uploadData.files[0].id);
                console.log(`✅ Image ${i + 1} uploaded: ${uploadData.files[0].id}`);
              }
              setGenerationProgress(`Generating images... (${i + 1}/${slidesWithImages.length})`);
            } else {
              console.error(`❌ Failed to upload image ${i + 1}:`, await uploadResponse.text());
            }
          } catch (error) {
            console.error(`Error generating image ${i}:`, error);
          }
        }
      }
      
      // Step 2: Create presentation
      setGenerationProgress('Creating slides...');
      
      const idToken = await user.getIdToken();
      const response = await fetch('http://localhost:8000/api/slides/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`,
          'X-User-Email': user.email,
        },
        body: JSON.stringify({
          title: outline.title,
          subtitle: outline.subtitle,
          slides: outline.slides,
          image_file_ids: imageFileIds,
          title_image_id: titleImageId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setPresentationUrl(data.url);
        setViewUrl(data.view_url);
        setGenerationProgress('');
      } else {
        const errorData = await response.json();
        alert(`Failed to create presentation: ${errorData.detail || response.statusText}`);
        setStep(2);
      }
    } catch (error) {
      console.error('Error generating presentation:', error);
      alert('Error generating presentation');
      setStep(2);
    } finally {
      setIsGeneratingPresentation(false);
    }
  };

  const handleEditSlide = (index: number, field: 'title' | 'content', value: any) => {
    if (!outline) return;
    
    const newSlides = [...outline.slides];
    if (field === 'title') {
      newSlides[index].title = value;
    } else if (field === 'content') {
      newSlides[index].content = value;
    }
    
    setOutline({ ...outline, slides: newSlides });
  };

  const handleNewPresentation = () => {
    setStep(1);
    setTopic("");
    setOutline(null);
    setPresentationUrl("");
    setViewUrl("");
    setGenerationProgress("");
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Step 1: Topic Input */}
      {step === 1 && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-2xl space-y-6">
            <div className="text-center space-y-2">
              <Presentation className="w-12 h-12 mx-auto text-indigo-400" />
              <h1 className="text-3xl font-bold">Create AI Presentation</h1>
              <p className="text-muted-foreground">Generate professional slides with Cornflower theme</p>
            </div>

            <div className="space-y-4">
              {/* Prompt Input */}
              <div className="space-y-2">
                <Label className="text-sm text-foreground">Presentation Topic</Label>
                <div className="relative">
                  <Textarea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    className="w-full rounded-md bg-muted px-4 py-3 pr-12 text-foreground outline-none focus:ring-2 focus:ring-indigo-400 min-h-[100px]"
                    placeholder="Enter your presentation topic... (e.g., AI in Healthcare, Climate Solutions)"
                    disabled={isGeneratingOutline}
                  />
                </div>
              </div>

              {/* Number of Slides */}
              <div className="space-y-2">
                <Label className="text-sm text-foreground">Number of Slides</Label>
                <Select value={numSlides} onValueChange={setNumSlides}>
                  <SelectTrigger className="bg-muted">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[5, 6, 7, 8, 9, 10].map(num => (
                      <SelectItem key={num} value={num.toString()}>
                        {num} slides
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Generate Button */}
              <Button
                onClick={handleGenerateOutline}
                disabled={isGeneratingOutline || !topic.trim()}
                className="w-full bg-indigo-500 hover:bg-indigo-600 h-11"
              >
                {isGeneratingOutline ? (
                  <>
                    <Spinner size={20} className="mr-2 text-white" />
                    Generating outline...
                  </>
                ) : (
                  <>
                    <RefreshCw size={20} className="mr-2" />
                    Generate Outline
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Outline Review */}
      {step === 2 && outline && (
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">{outline.title}</h1>
                <p className="text-muted-foreground mt-1">{outline.subtitle}</p>
              </div>
              <Button variant="outline" onClick={handleNewPresentation}>
                Start Over
              </Button>
            </div>

            {/* Outline Header */}
            <div className="flex items-center justify-between">
              <h2 className="text-sm text-foreground">Outline</h2>
              {isGeneratingOutline && (
                <span className="animate-pulse text-xs text-muted-foreground">
                  Generating outline...
                </span>
              )}
            </div>

            {/* Outline Items */}
            <div className="space-y-2">
              {outline.slides.map((slide, index) => (
                <div
                  key={index}
                  className="group flex items-center gap-4 rounded-md bg-muted p-4"
                >
                  <div className="cursor-move text-muted-foreground hover:text-foreground">
                    <GripVertical size={20} />
                  </div>
                  <span className="min-w-[1.5rem] text-indigo-400 font-medium">
                    {index + 1}
                  </span>
                  <div className="flex-1 space-y-2">
                    <input
                      type="text"
                      value={slide.title}
                      onChange={(e) => handleEditSlide(index, 'title', e.target.value)}
                      className="w-full bg-transparent text-foreground outline-none font-medium"
                      placeholder="Slide title"
                    />
                    <Textarea
                      value={slide.content}
                      onChange={(e) => handleEditSlide(index, 'content', e.target.value)}
                      className="w-full bg-transparent text-sm text-muted-foreground outline-none resize-none min-h-[80px]"
                      placeholder={slide.layout_type === 'points' ? "Point 1: ...\nPoint 2: ...\nPoint 3: ..." : "Summary paragraph..."}
                    />
                    <div className="flex items-center gap-2">
                      {slide.layout_type && (
                        <span className={`text-xs px-2 py-0.5 rounded-md ${
                          slide.layout_type === 'points' 
                            ? 'bg-blue-500/10 text-blue-400' 
                            : 'bg-purple-500/10 text-purple-400'
                        }`}>
                          {slide.layout_type === 'points' ? '🔢 Points' : '📝 Summary'}
                        </span>
                      )}
                      {slide.has_image && (
                        <span className="text-xs px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" />
                          Image
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Loading Skeletons */}
            {isGeneratingOutline && (
              <div className="space-y-2">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            )}

            {/* Stats */}
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>{outline.slides.length} slides total</span>
            </div>

            {/* Generate Button */}
            <div className="sticky bottom-6 bg-background/95 backdrop-blur rounded-lg border p-4 space-y-3">
              {!window.puter && (
                <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-sm text-yellow-600 dark:text-yellow-400">
                  ⚠️ Image generation unavailable (Puter.js not loaded)
                </div>
              )}
              <Button
                onClick={handleGeneratePresentation}
                disabled={isGeneratingPresentation}
                className="w-full bg-indigo-500 hover:bg-indigo-600 h-11"
              >
                {isGeneratingPresentation ? (
                  <>
                    <Spinner size={20} className="mr-2 text-white" />
                    Generating presentation...
                  </>
                ) : (
                  <>
                    <Presentation size={20} className="mr-2" />
                    Generate Presentation
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Generation Progress / Success */}
      {step === 3 && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-md">
            {generationProgress ? (
              /* Loading State - Matching presentation-ai design */
              <div className="text-center space-y-6">
                <div className="relative">
                  <Spinner className="h-16 w-16 text-indigo-400 mx-auto" size={64} />
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold">Creating Presentation</h2>
                  <p className="text-muted-foreground">{generationProgress}</p>
                </div>
              </div>
            ) : presentationUrl ? (
              /* Success State */
              <div className="space-y-6">
                <div className="text-center space-y-3">
                  <div className="w-16 h-16 mx-auto bg-green-500/10 rounded-full flex items-center justify-center">
                    <Presentation className="w-8 h-8 text-green-500" />
                  </div>
                  <h2 className="text-2xl font-bold">Presentation Ready!</h2>
                  <p className="text-muted-foreground">
                    Your AI-generated Cornflower presentation is ready
                  </p>
                </div>

                <div className="space-y-3">
                  <Button
                    onClick={() => window.open(presentationUrl, '_blank')}
                    className="w-full bg-indigo-500 hover:bg-indigo-600 h-11"
                  >
                    <Edit2 className="w-5 h-5 mr-2" />
                    Open in Google Slides
                  </Button>
                  <Button
                    onClick={() => window.open(viewUrl, '_blank')}
                    variant="outline"
                    className="w-full h-11"
                  >
                    <ExternalLink className="w-5 h-5 mr-2" />
                    Present Now
                  </Button>
                  <Button
                    onClick={handleNewPresentation}
                    variant="ghost"
                    className="w-full h-11"
                  >
                    Create Another
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

