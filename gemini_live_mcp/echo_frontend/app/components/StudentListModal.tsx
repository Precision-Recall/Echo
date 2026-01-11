"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog-1";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Mail, Loader2 } from "lucide-react";

interface StudentList {
  id: string;
  department_name: string;
  department_year: string;
  section: string;
  emails: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface StudentListModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  editingList: StudentList | null;
}

export function StudentListModal({
  open,
  onClose,
  onSuccess,
  editingList,
}: StudentListModalProps) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [departmentName, setDepartmentName] = useState("");
  const [departmentYear, setDepartmentYear] = useState("");
  const [section, setSection] = useState("");
  const [emailsText, setEmailsText] = useState("");
  const [emailCount, setEmailCount] = useState(0);

  const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || "http://localhost:8001";

  // Reset form when modal opens/closes or editing list changes
  useEffect(() => {
    if (open) {
      if (editingList) {
        // Editing mode
        setDepartmentName(editingList.department_name);
        setDepartmentYear(editingList.department_year);
        setSection(editingList.section);
        setEmailsText(editingList.emails.join("\n"));
      } else {
        // Create mode
        setDepartmentName("");
        setDepartmentYear("");
        setSection("");
        setEmailsText("");
      }
    }
  }, [open, editingList]);

  // Count emails as user types
  useEffect(() => {
    const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
    const matches = emailsText.match(emailPattern);
    const uniqueEmails = matches ? [...new Set(matches.map(e => e.toLowerCase()))] : [];
    setEmailCount(uniqueEmails.length);
  }, [emailsText]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    if (!departmentName || !departmentYear || !section || !emailsText) {
      alert("Please fill in all fields");
      return;
    }

    if (emailCount === 0) {
      alert("Please enter at least one valid email address");
      return;
    }

    setLoading(true);

    try {
      const idToken = await user.getIdToken();
      
      const url = editingList
        ? `${TOKEN_SERVICE_URL}/api/student-lists/${editingList.id}`
        : `${TOKEN_SERVICE_URL}/api/student-lists/create`;
      
      const method = editingList ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${idToken}`
        },
        body: JSON.stringify({
          department_name: departmentName,
          department_year: departmentYear,
          section: section,
          emails_text: emailsText
        })
      });

      if (response.ok) {
        onSuccess();
      } else {
        const error = await response.json();
        alert(error.detail || "Failed to save student list");
      }
    } catch (error) {
      console.error("Error saving student list:", error);
      alert("Error saving student list");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {editingList ? "Edit Student List" : "Create New Student List"}
          </DialogTitle>
          <DialogDescription>
            {editingList
              ? "Update the details of your student list"
              : "Add a new student list with department info and email addresses"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* Department Name */}
            <div className="grid gap-2">
              <Label htmlFor="department">Department Name</Label>
              <Input
                id="department"
                placeholder="e.g., Computer Science"
                value={departmentName}
                onChange={(e) => setDepartmentName(e.target.value)}
                required
              />
            </div>

            {/* Year and Section */}
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="year">Year</Label>
                <Input
                  id="year"
                  placeholder="e.g., 2024"
                  value={departmentYear}
                  onChange={(e) => setDepartmentYear(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="section">Section</Label>
                <Input
                  id="section"
                  placeholder="e.g., A"
                  value={section}
                  onChange={(e) => setSection(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* Emails */}
            <div className="grid gap-2">
              <Label htmlFor="emails">Student Emails</Label>
              <Textarea
                id="emails"
                placeholder="Paste student emails here (comma, space, or newline separated)&#10;Example:&#10;student1@example.com, student2@example.com&#10;student3@example.com"
                rows={8}
                value={emailsText}
                onChange={(e) => setEmailsText(e.target.value)}
                required
                className="font-mono text-sm"
              />
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Mail className="h-4 w-4" />
                <span>
                  {emailCount === 0 ? (
                    "No emails detected"
                  ) : (
                    <span className="text-green-600 font-medium">
                      {emailCount} email{emailCount !== 1 ? "s" : ""} detected
                    </span>
                  )}
                </span>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading || emailCount === 0}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {editingList ? "Updating..." : "Creating..."}
                </>
              ) : (
                <>{editingList ? "Update List" : "Create List"}</>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

