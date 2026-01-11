"use client";

import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Edit, Trash2, Users, Calendar, BookOpen } from "lucide-react";

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

interface StudentListCardProps {
  list: StudentList;
  onEdit: () => void;
  onDelete: () => void;
}

export function StudentListCard({ list, onEdit, onDelete }: StudentListCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  return (
    <Card className="hover:shadow-lg transition-shadow duration-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-blue-600" />
              {list.department_name}
            </h3>
            <div className="flex items-center gap-2 mt-1 text-sm text-gray-600">
              <Calendar className="h-4 w-4" />
              <span>{list.department_year} • Section {list.section}</span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg">
          <Users className="h-5 w-5 text-blue-600" />
          <div>
            <p className="text-2xl font-bold text-blue-600">{list.emails.length}</p>
            <p className="text-xs text-gray-600">Students</p>
          </div>
        </div>

        <div className="mt-3 text-xs text-gray-500">
          Created {formatDate(list.created_at)}
        </div>
      </CardContent>

      <CardFooter className="flex gap-2 pt-3 border-t">
        <Button
          variant="outline"
          size="sm"
          className="flex-1 gap-2"
          onClick={onEdit}
        >
          <Edit className="h-4 w-4" />
          Edit
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
          onClick={onDelete}
        >
          <Trash2 className="h-4 w-4" />
          Delete
        </Button>
      </CardFooter>
    </Card>
  );
}

