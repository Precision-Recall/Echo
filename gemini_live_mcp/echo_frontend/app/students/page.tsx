"use client";

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { ProtectedRoute } from "../components/ProtectedRoute";
import { AppSidebar } from "../components/AppSidebar";
import { SidebarProvider, SidebarInset, useSidebar } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Plus, Users } from "lucide-react";
import { StudentListModal } from "../components/StudentListModal";
import { StudentListCard } from "../components/StudentListCard";

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

export default function StudentsPage() {
  const { user } = useAuth();
  const [studentLists, setStudentLists] = useState<StudentList[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingList, setEditingList] = useState<StudentList | null>(null);

  const TOKEN_SERVICE_URL = process.env.NEXT_PUBLIC_TOKEN_SERVICE_URL || "http://localhost:8001";

  // Fetch student lists
  const fetchStudentLists = async () => {
    if (!user) return;

    try {
      setLoading(true);
      const idToken = await user.getIdToken();
      
      const response = await fetch(`${TOKEN_SERVICE_URL}/api/student-lists`, {
        headers: {
          'Authorization': `Bearer ${idToken}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setStudentLists(data);
      } else {
        console.error("Failed to fetch student lists");
      }
    } catch (error) {
      console.error("Error fetching student lists:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudentLists();
  }, [user]);

  const handleCreate = () => {
    setEditingList(null);
    setShowModal(true);
  };

  const handleEdit = (list: StudentList) => {
    setEditingList(list);
    setShowModal(true);
  };

  const handleDelete = async (listId: string) => {
    if (!user) return;
    if (!confirm("Are you sure you want to delete this student list?")) return;

    try {
      const idToken = await user.getIdToken();
      
      const response = await fetch(`${TOKEN_SERVICE_URL}/api/student-lists/${listId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${idToken}`
        }
      });

      if (response.ok) {
        // Remove from local state
        setStudentLists(prev => prev.filter(list => list.id !== listId));
      } else {
        alert("Failed to delete student list");
      }
    } catch (error) {
      console.error("Error deleting student list:", error);
      alert("Error deleting student list");
    }
  };

  const handleModalSuccess = () => {
    setShowModal(false);
    setEditingList(null);
    fetchStudentLists(); // Refresh the list
  };

  return (
    <ProtectedRoute>
      <SidebarProvider defaultOpen={false} style={{ "--sidebar-width": "16rem" } as React.CSSProperties}>
        <AppSidebar />
        <StudentsContent
          studentLists={studentLists}
          loading={loading}
          handleCreate={handleCreate}
          handleEdit={handleEdit}
          handleDelete={handleDelete}
          showModal={showModal}
          setShowModal={setShowModal}
          editingList={editingList}
          setEditingList={setEditingList}
          handleModalSuccess={handleModalSuccess}
        />
        
        {/* Create/Edit Modal */}
        <StudentListModal
          open={showModal}
          onClose={() => {
            setShowModal(false);
            setEditingList(null);
          }}
          onSuccess={handleModalSuccess}
          editingList={editingList}
        />
      </SidebarProvider>
    </ProtectedRoute>
  );
}

function StudentsContent({
  studentLists,
  loading,
  handleCreate,
  handleEdit,
  handleDelete,
  showModal,
  setShowModal,
  editingList,
  setEditingList,
  handleModalSuccess
}: any) {
  const { setOpen } = useSidebar();

  // Handle hover to expand sidebar
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Expand sidebar when mouse is within 80px of left edge (hovering over collapsed sidebar)
      if (e.clientX <= 80) {
        setOpen(true);
      }
      // Collapse sidebar when mouse moves away (beyond 280px from left)
      else if (e.clientX > 280) {
        setOpen(false);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [setOpen]);

  return (
    <SidebarInset>
        <div className="flex h-screen flex-col">
          {/* Main Content */}
          <div className="flex-1 overflow-auto">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading student lists...</p>
                  </div>
                </div>
              ) : (
                <div className="container mx-auto p-6 max-w-7xl">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-8">
                    <div>
                      <h2 className="text-3xl font-bold flex items-center gap-2">
                        <Users className="h-8 w-8" />
                        Student Lists
                      </h2>
                      <p className="text-gray-600 mt-1">
                        Manage your student lists by department and section
                      </p>
                    </div>
                    <Button onClick={handleCreate} size="lg" className="gap-2">
                      <Plus className="h-5 w-5" />
                      New List
                    </Button>
                  </div>

                  {/* Student Lists Grid */}
                  {studentLists.length === 0 ? (
                    // Empty State
                    <div className="flex flex-col items-center justify-center py-20 text-center">
                      <div className="rounded-full bg-gray-100 p-6 mb-4">
                        <Users className="h-16 w-16 text-gray-400" />
                      </div>
                      <h3 className="text-2xl font-semibold mb-2">No student lists yet</h3>
                      <p className="text-gray-600 mb-6 max-w-md">
                        Create your first student list to organize students by department, year, and section.
                      </p>
                      <Button onClick={handleCreate} size="lg" className="gap-2">
                        <Plus className="h-5 w-5" />
                        Create Your First List
                      </Button>
                    </div>
                  ) : (
                    // Grid of Student Lists
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {studentLists.map((list) => (
                        <StudentListCard
                          key={list.id}
                          list={list}
                          onEdit={() => handleEdit(list)}
                          onDelete={() => handleDelete(list.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
      </SidebarInset>
  );
}

