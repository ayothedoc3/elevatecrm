import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
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

  // Create API instance
  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: `${API_URL}/api`,
    });
    
    // Add token to requests
    instance.interceptors.request.use((config) => {
      const currentToken = localStorage.getItem('crm_token');
      if (currentToken) {
        config.headers.Authorization = `Bearer ${currentToken}`;
      }
      return config;
    });
    
    return instance;
  }, []);

  // Logout function - defined first
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setCurrentWorkspace(null);
    setWorkspaces([]);
    localStorage.removeItem('crm_token');
    localStorage.removeItem('currentWorkspaceId');
    localStorage.removeItem('currentTenantId');
    localStorage.removeItem('crm_tenant');
  }, []);

  // Switch workspace function
  const switchWorkspace = useCallback(async (workspaceId) => {
    try {
      const response = await api.post(`/workspaces/${workspaceId}/switch`);
      const data = response.data;
      
      setCurrentWorkspace(prev => {
        const ws = workspaces.find(w => w.id === workspaceId) || prev;
        return ws ? { ...ws, tenant_id: data.tenant_id } : null;
      });
      setTenant(data.workspace_slug);
      
      localStorage.setItem('currentWorkspaceId', workspaceId);
      localStorage.setItem('currentTenantId', data.tenant_id);
      localStorage.setItem('crm_tenant', data.workspace_slug);
      
      return true;
    } catch (error) {
      console.error('Failed to switch workspace:', error);
      return false;
    }
  }, [api, workspaces]);

  // Fetch workspaces function
  const fetchWorkspaces = useCallback(async () => {
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
      
      // If we have active workspaces, switch to the first one
      const activeWs = ws.find(w => w.status === 'active');
      if (activeWs) {
        const switchResponse = await api.post(`/workspaces/${activeWs.id}/switch`);
        const switchData = switchResponse.data;
        
        setCurrentWorkspace({ ...activeWs, tenant_id: switchData.tenant_id });
        setTenant(switchData.workspace_slug);
        
        localStorage.setItem('currentWorkspaceId', activeWs.id);
        localStorage.setItem('currentTenantId', switchData.tenant_id);
        localStorage.setItem('crm_tenant', switchData.workspace_slug);
      }
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
    }
  }, [api]);

  // Initialize auth on mount
  useEffect(() => {
    const initAuth = async () => {
      const currentToken = localStorage.getItem('crm_token');
      if (currentToken) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
          await fetchWorkspaces();
        } catch (error) {
          console.error('Auth init error:', error);
          logout();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, [api, fetchWorkspaces, logout]);

  // Login function
  const login = async (email, password) => {
    try {
      const response = await axios.post(
        `${API_URL}/api/auth/login?tenant_slug=${tenant}`,
        { email, password }
      );
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('crm_token', access_token);
      
      // Fetch workspaces after login
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

  const value = useMemo(() => ({
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
  }), [user, token, tenant, currentWorkspace, workspaces, switchWorkspace, fetchWorkspaces, logout, loading, api]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
