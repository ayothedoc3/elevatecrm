import React, { createContext, useContext, useState, useEffect } from 'react';
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

  // Create API instance with interceptor
  const api = axios.create({
    baseURL: `${API_URL}/api`,
  });
  
  // Add token to requests
  api.interceptors.request.use((config) => {
    const currentToken = localStorage.getItem('crm_token');
    if (currentToken) {
      config.headers.Authorization = `Bearer ${currentToken}`;
    }
    return config;
  });

  // Initialize auth on mount
  useEffect(() => {
    const initAuth = async () => {
      const currentToken = localStorage.getItem('crm_token');
      if (currentToken) {
        try {
          const response = await api.get('/auth/me');
          setUser(response.data);
          
          // Fetch and set workspaces
          try {
            const wsResponse = await api.get('/workspaces');
            const ws = wsResponse.data.workspaces || [];
            setWorkspaces(ws);
            
            const savedWorkspaceId = localStorage.getItem('currentWorkspaceId');
            const savedTenantId = localStorage.getItem('currentTenantId');
            
            if (savedWorkspaceId && savedTenantId) {
              const found = ws.find(w => w.id === savedWorkspaceId);
              if (found) {
                setCurrentWorkspace({ ...found, tenant_id: savedTenantId });
                setTenant(found.slug);
              }
            } else if (ws.length > 0) {
              const activeWs = ws.find(w => w.status === 'active');
              if (activeWs) {
                const switchRes = await api.post(`/workspaces/${activeWs.id}/switch`);
                setCurrentWorkspace({ ...activeWs, tenant_id: switchRes.data.tenant_id });
                setTenant(switchRes.data.workspace_slug);
                localStorage.setItem('currentWorkspaceId', activeWs.id);
                localStorage.setItem('currentTenantId', switchRes.data.tenant_id);
                localStorage.setItem('crm_tenant', switchRes.data.workspace_slug);
              }
            }
          } catch (wsError) {
            console.error('Failed to fetch workspaces:', wsError);
          }
        } catch (error) {
          console.error('Auth init error:', error);
          setToken(null);
          setUser(null);
          localStorage.removeItem('crm_token');
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

  const logout = () => {
    setToken(null);
    setUser(null);
    setCurrentWorkspace(null);
    setWorkspaces([]);
    localStorage.removeItem('crm_token');
    localStorage.removeItem('currentWorkspaceId');
    localStorage.removeItem('currentTenantId');
    localStorage.removeItem('crm_tenant');
  };

  const switchWorkspace = async (workspaceId) => {
    try {
      const response = await api.post(`/workspaces/${workspaceId}/switch`);
      const data = response.data;
      
      const ws = workspaces.find(w => w.id === workspaceId);
      if (ws) {
        setCurrentWorkspace({ ...ws, tenant_id: data.tenant_id });
      }
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

  const fetchWorkspaces = async () => {
    try {
      const response = await api.get('/workspaces');
      setWorkspaces(response.data.workspaces || []);
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
    }
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
