"use client";

import { useState } from 'react';
import { Button } from "@/components/ui/button";

export interface CourseData {
  name: string;
  section: string;
  description_heading: string;
  description: string;
  room: string;
}

interface CourseFormProps {
  onSubmit: (data: CourseData) => void;
  onCancel: () => void;
}

export function CourseForm({ onSubmit, onCancel }: CourseFormProps) {
  const [formData, setFormData] = useState<CourseData>({
    name: '',
    section: '',
    description_heading: '',
    description: '',
    room: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="w-full max-w-2xl">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-base font-semibold text-gray-900 mb-1">Create Course</h3>
        <p className="text-xs text-gray-500">Fill in the course details below</p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Course Name */}
        <div>
          <label htmlFor="name" className="block text-xs font-medium text-gray-700 mb-1.5">
            Course Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            placeholder="e.g., Introduction to Python Programming"
          />
        </div>

        {/* Section */}
        <div>
          <label htmlFor="section" className="block text-xs font-medium text-gray-700 mb-1.5">
            Section
          </label>
          <input
            type="text"
            id="section"
            name="section"
            value={formData.section}
            onChange={handleChange}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            placeholder="e.g., Period 2, Section A"
          />
        </div>

        {/* Description Heading */}
        <div>
          <label htmlFor="description_heading" className="block text-xs font-medium text-gray-700 mb-1.5">
            Description Heading
          </label>
          <input
            type="text"
            id="description_heading"
            name="description_heading"
            value={formData.description_heading}
            onChange={handleChange}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            placeholder="e.g., Learn Python from scratch"
          />
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="block text-xs font-medium text-gray-700 mb-1.5">
            Description
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={4}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors resize-vertical"
            placeholder="Enter detailed course description..."
          />
        </div>

        {/* Room */}
        <div>
          <label htmlFor="room" className="block text-xs font-medium text-gray-700 mb-1.5">
            Room
          </label>
          <input
            type="text"
            id="room"
            name="room"
            value={formData.room}
            onChange={handleChange}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors"
            placeholder="e.g., Room 301, Lab A"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-2 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            className="text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            className="bg-gray-900 hover:bg-gray-800 text-white"
          >
            Create Course
          </Button>
        </div>
      </form>
    </div>
  );
}

