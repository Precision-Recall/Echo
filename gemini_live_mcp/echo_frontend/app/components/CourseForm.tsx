"use client";

import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Users } from "lucide-react";

export interface CourseData {
  name: string;
  section: string;
  description_heading: string;
  description: string;
  room: string;
  student_list_id?: string;
}

interface StudentList {
  id: string;
  department_name: string;
  department_year: string;
  section: string;
  emails: string[];
}

interface CourseFormProps {
  onSubmit: (data: CourseData) => void;
  onCancel: () => void;
  studentLists?: StudentList[];
}

export function CourseForm({ onSubmit, onCancel, studentLists = [] }: CourseFormProps) {
  const [formData, setFormData] = useState<CourseData>({
    name: '',
    section: '',
    description_heading: '',
    description: '',
    room: '',
    student_list_id: undefined
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

        {/* Student List Selection */}
        {studentLists && studentLists.length > 0 && (
          <div>
            <label htmlFor="student_list" className="block text-xs font-medium text-gray-700 mb-1.5">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Send Invitations to Student List (Optional)
              </div>
            </label>
            <Select
              value={formData.student_list_id || undefined}
              onValueChange={(value) => setFormData(prev => ({ 
                ...prev, 
                student_list_id: value === "none" ? undefined : value 
              }))}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a student list (optional)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None - Don't send invitations</SelectItem>
                {studentLists.map((list) => (
                  <SelectItem key={list.id} value={list.id}>
                    {list.department_name} - {list.department_year} ({list.section}) • {list.emails.length} students
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-gray-500 mt-1">
              If selected, all students in the list will receive an email invitation with the course join link.
            </p>
          </div>
        )}

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

