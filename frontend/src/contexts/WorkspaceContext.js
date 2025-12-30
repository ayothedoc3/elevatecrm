import React, { useState, useEffect, createContext, useContext } from 'react';

// Workspace Context
const WorkspaceContext = createContext(null);

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceProvider');
  }
  return context;
};

export const WorkspaceProvider = ({ children }) => {
  const [workspaces, setWorkspaces] = useState([]);
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  // Load workspaces on mount
  useEffect(() => {
    fetchWorkspaces();
  }, []);

  // Restore last workspace from localStorage
  useEffect(() => {
    const savedWorkspaceId = localStorage.getItem('currentWorkspaceId');
    if (savedWorkspaceId && workspaces.length > 0) {
      const saved = workspaces.find(w => w.id === savedWorkspaceId);
      if (saved) {
        setCurrentWorkspace(saved);
      }
    }
  }, [workspaces]);

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
        
        // Set first workspace as current if none selected
        if (!currentWorkspace && data.workspaces.length > 0) {
          setCurrentWorkspace(data.workspaces[0]);
          localStorage.setItem('currentWorkspaceId', data.workspaces[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to fetch workspaces:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchWorkspace = async (workspaceId) => {
    try {
      const response = await fetch(`${backendUrl}/api/workspaces/${workspaceId}/switch`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const workspace = workspaces.find(w => w.id === workspaceId);
        setCurrentWorkspace({ ...workspace, tenant_id: data.tenant_id });
        localStorage.setItem('currentWorkspaceId', workspaceId);
        localStorage.setItem('currentTenantId', data.tenant_id);
        
        // Reload page to refresh all data
        window.location.reload();
      }
    } catch (err) {
      console.error('Failed to switch workspace:', err);
      setError(err.message);
    }
  };

  const createWorkspace = async (name, blueprintSlug, includeDemoData = false) => {
    try {
      const response = await fetch(`${backendUrl}/api/workspaces`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          name,
          blueprint_slug: blueprintSlug,
          include_demo_data: includeDemoData
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        return data;
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create workspace');
      }
    } catch (err) {
      console.error('Failed to create workspace:', err);
      throw err;
    }
  };

  const getProvisioningStatus = async (workspaceId) => {
    try {
      const response = await fetch(`${backendUrl}/api/workspaces/${workspaceId}/provisioning`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        return await response.json();
      }
      return null;
    } catch (err) {
      console.error('Failed to get provisioning status:', err);
      return null;
    }
  };

  const value = {
    workspaces,
    currentWorkspace,
    loading,
    error,
    fetchWorkspaces,
    switchWorkspace,
    createWorkspace,
    getProvisioningStatus
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
};

export default WorkspaceContext;
