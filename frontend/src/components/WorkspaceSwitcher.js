import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
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
  ChevronDown, Building2, Plus, Check, Loader2, Flame 
} from 'lucide-react';
import AddCRMModal from './AddCRMModal';

const WorkspaceSwitcher = () => {
  const { workspaces, currentWorkspace, switchWorkspace, fetchWorkspaces, api } = useAuth();
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [localWorkspaces, setLocalWorkspaces] = useState([]);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    setLoading(true);
    try {
      const response = await api.get('/workspaces');
      setLocalWorkspaces(response.data.workspaces || []);
    } catch (err) {
      console.error('Failed to load workspaces:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSwitch = async (workspace) => {
    if (workspace.id === currentWorkspace?.id) return;
    if (workspace.status !== 'active') return;
    
    setLoading(true);
    const success = await switchWorkspace(workspace.id);
    if (success) {
      window.location.reload();
    }
    setLoading(false);
  };

  const handleWorkspaceCreated = (workspaceId) => {
    setShowAddModal(false);
    // Reload to switch to new workspace
    window.location.reload();
  };

  const displayWorkspaces = localWorkspaces.length > 0 ? localWorkspaces : workspaces;

  // If no workspaces exist, show "Add CRM" button
  if (!loading && displayWorkspaces.length === 0) {
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
          <Button variant="outline" className="min-w-[200px] justify-between" disabled={loading}>
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-orange-500" />
              <span className="truncate max-w-[140px]">
                {loading ? 'Loading...' : (currentWorkspace?.name || 'Select CRM')}
              </span>
            </div>
            <ChevronDown className="w-4 h-4 ml-2 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[280px]">
          {displayWorkspaces.map(workspace => (
            <DropdownMenuItem
              key={workspace.id}
              onClick={() => handleSwitch(workspace)}
              className={`cursor-pointer ${workspace.status !== 'active' ? 'opacity-50' : ''}`}
              disabled={workspace.status !== 'active'}
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-500" />
                  <div>
                    <span className="truncate">{workspace.name}</span>
                    {workspace.status !== 'active' && (
                      <Badge variant="outline" className="ml-2 text-xs">
                        {workspace.status}
                      </Badge>
                    )}
                  </div>
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
