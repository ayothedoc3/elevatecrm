import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('crm_token'));
  const [loading, setLoading] = useState(true);
  const [tenant, setTenant] = useState(localStorage.getItem('crm_tenant') || 'demo');
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);

  const api = axios.create({
    baseURL: `${API_URL}/api`,
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });

  // Update axios headers when token changes
  useEffect(() => {
    if (token) {
      api.defaults.headers.Authorization = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.Authorization;
    }
  }, [token]);

  // Fetch workspaces when authenticated
  const fetchWorkspaces = useCallback(async () => {
    if (!token) return;
    
    try {
      const response = await api.get('/workspaces');
      const ws = response.data.workspaces || [];
      setWorkspaces(ws);
      
      // Check if we have a saved workspace
      const savedWorkspaceId = localStorage.getItem('currentWorkspaceId');
      const savedTenantId = localStorage.getItem('currentTenantId');
      
      if (savedWorkspaceId && savedTenantId) {
        const found = ws.find(w => w.id === savedWorkspaceId);
        if (found) {
          setCurrentWorkspace({ ...found, tenant_id: savedTenantId });
          setTenant(found.slug);
          return;
        }
      }
      
      // If we have workspaces, switch to the first one
      if (ws.length > 0 && ws[0].status === 'active') {
        await switchWorkspace(ws[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
    }
  }, [token]);

  // Switch workspace and update tenant
  const switchWorkspace = async (workspaceId) => {
    try {
      const response = await api.post(`/workspaces/${workspaceId}/switch`);
      const data = response.data;
      
      const workspace = workspaces.find(w => w.id === workspaceId) || {
        id: workspaceId,
        name: data.workspace_name,
        slug: data.workspace_slug
      };
      
      setCurrentWorkspace({ ...workspace, tenant_id: data.tenant_id });
      setTenant(data.workspace_slug);
      
      localStorage.setItem('currentWorkspaceId', workspaceId);
      localStorage.setItem('currentTenantId', data.tenant_id);
      localStorage.setItem('crm_tenant', data.workspace_slug);
      
      return true;
    } catch (error) {
      console.error('Failed to switch workspace:', error);
      return false;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
          // Fetch workspaces after auth
          await fetchWorkspaces();
        } catch (error) {
          console.error('Auth init error:', error);
          logout();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await axios.post(
        `${API_URL}/api/auth/login?tenant_slug=${tenant}`,
        { email, password }
      );
      const { access_token, user } = response.data;
      setToken(access_token);
      setUser(user);
      localStorage.setItem('crm_token', access_token);
      
      // Fetch workspaces after login
      api.defaults.headers.Authorization = `Bearer ${access_token}`;
      
      // Get workspaces and switch to first active one
      try {
        const wsResponse = await api.get('/workspaces');
        const ws = wsResponse.data.workspaces || [];
        setWorkspaces(ws);
        
        if (ws.length > 0) {
          const activeWorkspace = ws.find(w => w.status === 'active') || ws[0];
          if (activeWorkspace.status === 'active') {
            const switchResponse = await api.post(`/workspaces/${activeWorkspace.id}/switch`);
            const switchData = switchResponse.data;
            
            setCurrentWorkspace({ ...activeWorkspace, tenant_id: switchData.tenant_id });
            setTenant(switchData.workspace_slug);
            
            localStorage.setItem('currentWorkspaceId', activeWorkspace.id);
            localStorage.setItem('currentTenantId', switchData.tenant_id);
            localStorage.setItem('crm_tenant', switchData.workspace_slug);
          }
        }
      } catch (wsError) {
        console.error('Failed to fetch/switch workspaces:', wsError);
      }
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setCurrentWorkspace(null);
    setWorkspaces([]);
    localStorage.removeItem('crm_token');
    localStorage.removeItem('currentWorkspaceId');
    localStorage.removeItem('currentTenantId');
  };

  const value = {
    user,
    token,
    tenant,
    setTenant,
    currentWorkspace,
    workspaces,
    switchWorkspace,
    fetchWorkspaces,
    login,
    logout,
    loading,
    api,
    isAdmin: user?.role === 'admin',
    isManager: user?.role === 'manager' || user?.role === 'admin',
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
