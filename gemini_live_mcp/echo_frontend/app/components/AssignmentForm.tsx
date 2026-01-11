"use client";

import { useState, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Upload, X, File, Sparkles, Loader2 } from "lucide-react";
import { useAuth } from '@/app/contexts/AuthContext';

interface Course {
  id: string;
  name: string;
  section?: string;
  descriptionHeading?: string;
}

interface AssignmentFormProps {
  courseId?: string;
  courses?: Course[];
  onSubmit: (data: AssignmentData) => void;
  onCancel: () => void;
}

export interface AssignmentData {
  course_id: string;
  title: string;
  description: string;
  due_date: string;
  due_time: string;
  max_points: number;
  work_type: string;
  files?: File[];
}

export function AssignmentForm({ courseId = '', courses = [], onSubmit, onCancel }: AssignmentFormProps) {
  const { user } = useAuth();
  const [formData, setFormData] = useState<AssignmentData>({
    course_id: courseId,
    title: '',
    description: '',
    due_date: '',
    due_time: '',
    max_points: 100,
    work_type: 'ASSIGNMENT',
    files: []
  });
  
  const [isDragging, setIsDragging] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'max_points' ? parseFloat(value) : value
    }));
  };

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    const newFiles = Array.from(files);
    setFormData(prev => ({
      ...prev,
      files: [...(prev.files || []), ...newFiles]
    }));
  };

  const handleFileRemove = (index: number) => {
    setFormData(prev => ({
      ...prev,
      files: prev.files?.filter((_, i) => i !== index) || []
    }));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const handleGenerateDescription = async () => {
    if (!formData.description.trim() || !user) {
      return;
    }

    setIsGenerating(true);
    try {
      const idToken = await user.getIdToken();
      const response = await fetch('http://localhost:8000/api/generate-description', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        },
        body: JSON.stringify({
          query: formData.description
        })
      });

      if (response.ok) {
        const result = await response.json();
        setFormData(prev => ({
          ...prev,
          description: result.description
        }));
      } else {
        console.error('Failed to generate description:', await response.text());
      }
    } catch (error) {
      console.error('Error generating description:', error);
    } finally {
      setIsGenerating(false);
    }
  };


  return (
    <div className="w-full max-w-2xl">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-base font-semibold text-gray-900 mb-1">Create Assignment</h3>
        <p className="text-xs text-gray-500">Fill in the details below</p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Course Selection */}
        <div>
          <label htmlFor="course_id" className="block text-xs font-medium text-gray-700 mb-1.5">
            Course <span className="text-red-500">*</span>
          </label>
          {courses.length > 0 ? (
            <select
              id="course_id"
              name="course_id"
              value={formData.course_id}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors bg-white"
            >
              <option value="">Select a course...</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>
                  {course.name} {course.section ? `(${course.section})` : ''}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              id="course_id"
              name="course_id"
              value={formData.course_id}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
              placeholder="e.g., 823993365562"
            />
          )}
        </div>

        {/* Title */}
        <div>
          <label htmlFor="title" className="block text-xs font-medium text-gray-700 mb-1.5">
            Assignment Title <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            placeholder="e.g., Lab Assignment 14"
          />
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="block text-xs font-medium text-gray-700 mb-1.5">
            Description
          </label>
          <div className="relative">
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={3}
              className="w-full px-3 py-2 pr-12 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors resize-none"
            placeholder="Enter assignment description..."
          />
            <button
              type="button"
              onClick={handleGenerateDescription}
              disabled={!formData.description.trim() || isGenerating}
              className="absolute right-2 top-2 p-2 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md"
              title="Enhance description with AI"
            >
              {isGenerating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            ✨ Click the sparkle button to enhance your description with AI (50-100 words)
          </p>
        </div>

        {/* Due Date and Time */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="due_date" className="block text-xs font-medium text-gray-700 mb-1.5">
              Due Date
            </label>
            <input
              type="date"
              id="due_date"
              name="due_date"
              value={formData.due_date}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            />
          </div>
          <div>
            <label htmlFor="due_time" className="block text-xs font-medium text-gray-700 mb-1.5">
              Due Time
            </label>
            <input
              type="time"
              id="due_time"
              name="due_time"
              value={formData.due_time}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            />
          </div>
        </div>

        {/* Max Points and Work Type */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="max_points" className="block text-xs font-medium text-gray-700 mb-1.5">
              Max Points
            </label>
            <input
              type="number"
              id="max_points"
              name="max_points"
              value={formData.max_points}
              onChange={handleChange}
              min="0"
              step="1"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            />
          </div>
          <div>
            <label htmlFor="work_type" className="block text-xs font-medium text-gray-700 mb-1.5">
              Work Type
            </label>
            <select
              id="work_type"
              name="work_type"
              value={formData.work_type}
              onChange={handleChange}
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            >
              <option value="ASSIGNMENT">Assignment</option>
              <option value="SHORT_ANSWER_QUESTION">Short Answer</option>
              <option value="MULTIPLE_CHOICE_QUESTION">Multiple Choice</option>
            </select>
          </div>
        </div>

        {/* File Upload */}
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1.5">
            Attach Files (Optional)
          </label>
          
          {/* Drag and Drop Area */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`
              relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
              ${isDragging 
                ? 'border-gray-900 bg-gray-50' 
                : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
              }
            `}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
              accept="*/*"
            />
            <Upload className="mx-auto h-8 w-8 text-gray-400 mb-2" />
            <p className="text-sm text-gray-600 mb-1">
              <span className="font-medium text-gray-900">Click to upload</span> or drag and drop
            </p>
            <p className="text-xs text-gray-500">
              Any file type supported
            </p>
          </div>

          {/* File List */}
          {formData.files && formData.files.length > 0 && (
            <div className="mt-3 space-y-2">
              {formData.files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <File className="h-4 w-4 text-gray-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 truncate">{file.name}</p>
                      <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleFileRemove(index)}
                    className="p-1 hover:bg-gray-200 rounded transition-colors flex-shrink-0"
                  >
                    <X className="h-4 w-4 text-gray-500" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            type="button"
            onClick={onCancel}
            variant="outline"
            className="flex-1 py-2 rounded-lg text-sm"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            className="flex-1 py-2 rounded-lg bg-gray-900 hover:bg-gray-800 text-white text-sm"
          >
            Create Assignment
          </Button>
        </div>
      </form>
    </div>
  );
}

