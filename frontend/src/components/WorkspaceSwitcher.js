import React, { useState, useEffect } from 'react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { 
  ChevronDown, Building2, Plus, Check, Settings, Loader2 
} from 'lucide-react';
import AddCRMModal from './AddCRMModal';

const WorkspaceSwitcher = () => {
  const [workspaces, setWorkspaces] = useState([]);
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const fetchWorkspaces = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/workspaces`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setWorkspaces(data.workspaces);
        
        // Find current workspace from localStorage or use first
        const savedId = localStorage.getItem('currentWorkspaceId');
        const current = savedId 
          ? data.workspaces.find(w => w.id === savedId) 
          : data.workspaces[0];
        
        if (current) {
          setCurrentWorkspace(current);
        }
      }
    } catch (err) {
      console.error('Failed to fetch workspaces:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitch = async (workspace) => {
    if (workspace.id === currentWorkspace?.id) return;
    
    try {
      const response = await fetch(`${backendUrl}/api/workspaces/${workspace.id}/switch`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('currentWorkspaceId', workspace.id);
        localStorage.setItem('currentTenantId', data.tenant_id);
        window.location.reload();
      }
    } catch (err) {
      console.error('Failed to switch workspace:', err);
    }
  };

  const handleWorkspaceCreated = (workspaceId) => {
    setShowAddModal(false);
    localStorage.setItem('currentWorkspaceId', workspaceId);
    window.location.reload();
  };

  if (loading) {
    return (
      <Button variant="outline" disabled className="min-w-[180px]">
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        Loading...
      </Button>
    );
  }

  // If no workspaces exist, show "Add CRM" button
  if (workspaces.length === 0) {
    return (
      <>
        <Button 
          variant="outline"
          onClick={() => setShowAddModal(true)}
          className="min-w-[180px]"
        >
          <Plus className="w-4 h-4 mr-2" />
          Add CRM
        </Button>
        <AddCRMModal 
          open={showAddModal} 
          onClose={() => setShowAddModal(false)}
          onSuccess={handleWorkspaceCreated}
        />
      </>
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="min-w-[180px] justify-between">
            <div className="flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              <span className="truncate max-w-[120px]">
                {currentWorkspace?.name || 'Select CRM'}
              </span>
            </div>
            <ChevronDown className="w-4 h-4 ml-2 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[250px]">
          {workspaces.map(workspace => (
            <DropdownMenuItem
              key={workspace.id}
              onClick={() => handleSwitch(workspace)}
              className="cursor-pointer"
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  <span className="truncate">{workspace.name}</span>
                </div>
                {workspace.id === currentWorkspace?.id && (
                  <Check className="w-4 h-4 text-primary" />
                )}
              </div>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem 
            onClick={() => setShowAddModal(true)}
            className="cursor-pointer"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add CRM
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      
      <AddCRMModal 
        open={showAddModal} 
        onClose={() => setShowAddModal(false)}
        onSuccess={handleWorkspaceCreated}
      />
    </>
  );
};

export default WorkspaceSwitcher;
