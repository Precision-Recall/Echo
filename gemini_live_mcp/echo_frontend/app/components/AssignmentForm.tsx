"use client";

import { useState } from 'react';
import { Button } from "@/components/ui/button";

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
}

export function AssignmentForm({ courseId = '', courses = [], onSubmit, onCancel }: AssignmentFormProps) {
  const [formData, setFormData] = useState<AssignmentData>({
    course_id: courseId,
    title: '',
    description: '',
    due_date: '',
    due_time: '',
    max_points: 100,
    work_type: 'ASSIGNMENT'
  });

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

  return (
    <div className="mb-4">
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
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={3}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-gray-400 focus:border-gray-400 transition-colors resize-none"
            placeholder="Enter assignment description..."
          />
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

