import React, { useState, useEffect } from 'react';
import {
  Settings, Key, Bot, Globe, Users, Shield, AlertCircle,
  CheckCircle, XCircle, Eye, EyeOff, RefreshCw, Trash2,
  Plus, Save, ExternalLink, Zap, MessageSquare, CreditCard,
  Clock, Activity, ChevronRight, Info, Loader2, UserPlus, Pencil
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { useToast } from '../hooks/use-toast';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';
const DEFAULT_SLA_CONFIG = { speed_to_lead_minutes: 15, lead_cadence_hours: 24, deal_cadence_hours: 72 };

const SettingsPage = () => {
  const { user } = useAuth();
  const { isDark } = useTheme();
  const { toast } = useToast();
  
  const [activeTab, setActiveTab] = useState('workspace');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Workspace settings state
  const [workspaceSettings, setWorkspaceSettings] = useState({
    name: '',
    description: '',
    logo_url: '',
    primary_color: '#6366F1',
    timezone: 'UTC',
    currency: 'USD',
    sla_config: { ...DEFAULT_SLA_CONFIG }
  });
  
  // AI config state
  const [aiConfig, setAiConfig] = useState({
    default_provider: 'openai',
    default_model: 'gpt-4o',
    features_enabled: {},
    usage_limits: { daily_requests: 1000, monthly_requests: 25000 }
  });
  const [aiUsageStats, setAiUsageStats] = useState(null);
  
  // Integrations state
  const [integrations, setIntegrations] = useState([]);
  const [providers, setProviders] = useState(null);
  
  // Affiliate settings state
  const [affiliateSettings, setAffiliateSettings] = useState({
    enabled: true,
    default_currency: 'USD',
    default_attribution_window_days: 30,
    approval_mode: 'manual',
    min_payout_threshold: 50
  });
  
  // Audit logs state
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotal, setAuditTotal] = useState(0);
  
  // Team management state
  const [teamMembers, setTeamMembers] = useState([]);
  const [showAddMember, setShowAddMember] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [newMember, setNewMember] = useState({
    email: '', password: '', first_name: '', last_name: '', role: 'viewer', phone: ''
  });

  // Partner pipeline config state
  const [partnersList, setPartnersList] = useState([]);
  const [pipelinesList, setPipelinesList] = useState([]);
  const [savingPartnerId, setSavingPartnerId] = useState(null);
  const [cloningPartnerId, setCloningPartnerId] = useState(null);

  // Dialog state
  const [showAddIntegration, setShowAddIntegration] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [newApiKey, setNewApiKey] = useState('');
  const [providerConfig, setProviderConfig] = useState({});
  const [showKey, setShowKey] = useState(false);
  const [testing, setTesting] = useState(false);
  
  // Get auth token
  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };
  
  // Load all settings data
  useEffect(() => {
    loadAllSettings();
  }, []);
  
  const loadAllSettings = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadWorkspaceSettings(),
        loadAIConfig(),
        loadIntegrations(),
        loadProviders(),
        loadAffiliateSettings(),
        loadAuditLogs(),
        loadTeamMembers(),
        loadPartnersList(),
        loadPipelinesList()
      ]);
    } catch (error) {
      console.error('Error loading settings:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const loadWorkspaceSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/workspace`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setWorkspaceSettings({
          ...data,
          sla_config: { ...DEFAULT_SLA_CONFIG, ...(data.sla_config || {}) }
        });
      }
    } catch (error) {
      console.error('Error loading workspace settings:', error);
    }
  };
  
  const loadAIConfig = async () => {
    try {
      const [configResponse, usageResponse] = await Promise.all([
        fetch(`${API_URL}/api/settings/ai`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/settings/ai/usage?days=30`, { headers: getAuthHeaders() })
      ]);
      
      if (configResponse.ok) {
        const data = await configResponse.json();
        setAiConfig(data);
      }
      
      if (usageResponse.ok) {
        const data = await usageResponse.json();
        setAiUsageStats(data);
      }
    } catch (error) {
      console.error('Error loading AI config:', error);
    }
  };
  
  const loadIntegrations = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/integrations`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setIntegrations(data.integrations || []);
      }
    } catch (error) {
      console.error('Error loading integrations:', error);
    }
  };
  
  const loadProviders = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/providers`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setProviders(data);
      }
    } catch (error) {
      console.error('Error loading providers:', error);
    }
  };
  
  const loadAffiliateSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/api/settings/affiliates`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setAffiliateSettings(data);
      }
    } catch (error) {
      console.error('Error loading affiliate settings:', error);
    }
  };
  
  const loadAuditLogs = async (page = 1) => {
    try {
      const response = await fetch(`${API_URL}/api/settings/audit-logs?page=${page}&page_size=20`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setAuditLogs(data.logs || []);
        setAuditTotal(data.total || 0);
        setAuditPage(page);
      }
    } catch (error) {
      console.error('Error loading audit logs:', error);
    }
  };

  const loadTeamMembers = async () => {
    try {
      const response = await fetch(`${API_URL}/api/users`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setTeamMembers(data.users || []);
      }
    } catch (error) {
      console.error('Error loading team members:', error);
    }
  };

  const loadPartnersList = async () => {
    try {
      const response = await fetch(`${API_URL}/api/partners`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setPartnersList(data.partners || []);
      }
    } catch (error) {
      console.error('Error loading partners:', error);
    }
  };

  const loadPipelinesList = async () => {
    try {
      const response = await fetch(`${API_URL}/api/pipelines`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setPipelinesList(data.pipelines || []);
      }
    } catch (error) {
      console.error('Error loading pipelines:', error);
    }
  };

  const updatePartnerDefaultPipeline = async (partnerId, pipelineId) => {
    setSavingPartnerId(partnerId);
    try {
      const response = await fetch(`${API_URL}/api/partners/${partnerId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ default_pipeline_id: pipelineId || '' })
      });

      if (response.ok) {
        const updated = await response.json();
        setPartnersList(prev => prev.map(p => p.id === partnerId ? { ...p, ...updated } : p));
        toast({ title: 'Saved', description: 'Partner pipeline updated' });
      } else {
        const err = await response.json().catch(() => ({}));
        toast({ title: 'Error', description: err.detail || 'Failed to update partner pipeline', variant: 'destructive' });
      }
    } catch (error) {
      console.error('Error updating partner pipeline:', error);
      toast({ title: 'Error', description: 'Failed to update partner pipeline', variant: 'destructive' });
    } finally {
      setSavingPartnerId(null);
    }
  };

  const cloneDefaultPipelineForPartner = async (partner) => {
    const basePipeline = pipelinesList.find(p => p.is_default) || pipelinesList[0];
    if (!basePipeline) {
      toast({ title: 'No pipelines', description: 'Create a pipeline first', variant: 'destructive' });
      return;
    }

    setCloningPartnerId(partner.id);
    try {
      const response = await fetch(`${API_URL}/api/pipelines/${basePipeline.id}/clone`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: `${partner.name} Pipeline`,
          description: `Partner-specific pipeline for ${partner.name}`,
          is_default: false
        })
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        toast({ title: 'Error', description: err.detail || 'Failed to clone pipeline', variant: 'destructive' });
        return;
      }

      const cloned = await response.json();
      const newPipelineId = cloned.id;
      await loadPipelinesList();
      await updatePartnerDefaultPipeline(partner.id, newPipelineId);
    } catch (error) {
      console.error('Error cloning pipeline:', error);
      toast({ title: 'Error', description: 'Failed to clone pipeline', variant: 'destructive' });
    } finally {
      setCloningPartnerId(null);
    }
  };

  const createTeamMember = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/users`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(newMember)
      });
      if (response.ok) {
        toast({ title: "Success", description: "Team member added successfully" });
        setShowAddMember(false);
        setNewMember({ email: '', password: '', first_name: '', last_name: '', role: 'viewer', phone: '' });
        loadTeamMembers();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to add team member", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to add team member", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const updateTeamMember = async (userId, updates) => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/users/${userId}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(updates)
      });
      if (response.ok) {
        toast({ title: "Updated", description: "Team member updated successfully" });
        setEditingMember(null);
        loadTeamMembers();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to update", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to update team member", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const toggleMemberActive = async (userId, isActive) => {
    try {
      const response = await fetch(`${API_URL}/api/users/${userId}/active`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ is_active: isActive })
      });
      if (response.ok) {
        toast({ title: "Updated", description: `Account ${isActive ? 'activated' : 'deactivated'}` });
        loadTeamMembers();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to update", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to update team member", variant: "destructive" });
    }
  };

  const saveWorkspaceSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/settings/workspace`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(workspaceSettings)
      });
      
      if (response.ok) {
        toast({ title: "Settings saved", description: "Workspace settings updated successfully" });
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to save settings", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to save settings", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };
  
  const saveAIConfig = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/settings/ai`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          default_provider: aiConfig.default_provider,
          default_model: aiConfig.default_model,
          features_enabled: aiConfig.features_enabled,
          usage_limits: aiConfig.usage_limits
        })
      });
      
      if (response.ok) {
        toast({ title: "Settings saved", description: "AI configuration updated successfully" });
        loadAIConfig();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to save AI config", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to save AI config", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };
  
  const saveAffiliateSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/settings/affiliates`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(affiliateSettings)
      });
      
      if (response.ok) {
        toast({ title: "Settings saved", description: "Affiliate settings updated successfully" });
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to save settings", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to save settings", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const cleanProviderConfig = () => {
    const out = {};
    Object.entries(providerConfig || {}).forEach(([key, value]) => {
      const normalized = (value ?? '').toString().trim();
      if (normalized) out[key] = normalized;
    });
    return out;
  };

  const isProviderConfigValid = () => {
    if (!selectedProvider) return false;
    const type = selectedProvider.type;
    const cfg = cleanProviderConfig();
    if (type === 'sendgrid') return !!cfg.from_email;
    if (type === 'twilio') return !!cfg.account_sid && !!cfg.from_number;
    return true;
  };
  
  const addIntegration = async () => {
    if (!selectedProvider || !newApiKey) {
      toast({ title: "Error", description: "Please select a provider and enter a credential", variant: "destructive" });
      return;
    }
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/settings/integrations`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          provider_type: selectedProvider.type,
          api_key: newApiKey,
          config: cleanProviderConfig()
        })
      });
      
      if (response.ok) {
        toast({ title: "Success", description: `${selectedProvider.name} integration added successfully` });
        setShowAddIntegration(false);
        setSelectedProvider(null);
        setNewApiKey('');
        loadIntegrations();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to add integration", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to add integration", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };
  
  const testConnection = async () => {
    if (!selectedProvider) return;
    
    setTesting(true);
    try {
      const response = await fetch(`${API_URL}/api/settings/integrations/test`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          provider_type: selectedProvider.type,
          api_key: newApiKey || null,
          config: cleanProviderConfig()
        })
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast({ 
          title: "Connection successful", 
          description: `Connected to ${selectedProvider.name} in ${result.response_time_ms}ms` 
        });
      } else {
        toast({ 
          title: "Connection failed", 
          description: result.error || "Unable to connect to provider", 
          variant: "destructive" 
        });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to test connection", variant: "destructive" });
    } finally {
      setTesting(false);
    }
  };
  
  const toggleIntegration = async (providerType, enabled) => {
    try {
      const response = await fetch(`${API_URL}/api/settings/integrations/${providerType}/toggle`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ enabled })
      });
      
      if (response.ok) {
        toast({ title: "Updated", description: `Integration ${enabled ? 'enabled' : 'disabled'}` });
        loadIntegrations();
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to update integration", variant: "destructive" });
    }
  };
  
  const revokeIntegration = async (providerType) => {
    if (!window.confirm(`Are you sure you want to revoke the ${providerType} integration? This will permanently delete the stored credential.`)) {
      return;
    }
    
    try {
      const response = await fetch(`${API_URL}/api/settings/integrations/${providerType}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        toast({ title: "Revoked", description: "Integration removed successfully" });
        loadIntegrations();
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to revoke integration", variant: "destructive" });
    }
  };
  
  const getProviderIcon = (type) => {
    const icons = {
      openai: <Bot className="w-5 h-5" />,
      anthropic: <Bot className="w-5 h-5" />,
      openrouter: <Bot className="w-5 h-5" />,
      twilio: <MessageSquare className="w-5 h-5" />,
      sendgrid: <MessageSquare className="w-5 h-5" />,
      mailgun: <MessageSquare className="w-5 h-5" />,
      discord: <MessageSquare className="w-5 h-5" />,
      stripe: <CreditCard className="w-5 h-5" />,
      wise: <CreditCard className="w-5 h-5" />,
      paypal: <CreditCard className="w-5 h-5" />
    };
    return icons[type] || <Key className="w-5 h-5" />;
  };
  
  const formatTimestamp = (ts) => {
    if (!ts) return 'Never';
    return new Date(ts).toLocaleString();
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground">Manage your workspace configuration and integrations</p>
        </div>
      </div>
      
      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-6 lg:w-auto lg:inline-grid">
          <TabsTrigger value="workspace" className="flex items-center gap-2">
            <Globe className="w-4 h-4" />
            <span className="hidden sm:inline">Workspace</span>
          </TabsTrigger>
          <TabsTrigger value="ai" className="flex items-center gap-2">
            <Bot className="w-4 h-4" />
            <span className="hidden sm:inline">AI & Intelligence</span>
          </TabsTrigger>
          <TabsTrigger value="integrations" className="flex items-center gap-2">
            <Key className="w-4 h-4" />
            <span className="hidden sm:inline">Integrations</span>
          </TabsTrigger>
          <TabsTrigger value="affiliates" className="flex items-center gap-2">
            <Users className="w-4 h-4" />
            <span className="hidden sm:inline">Affiliates</span>
          </TabsTrigger>
          {(user?.role === 'admin' || user?.role === 'manager') && (
            <TabsTrigger value="team" className="flex items-center gap-2">
              <UserPlus className="w-4 h-4" />
              <span className="hidden sm:inline">Team</span>
            </TabsTrigger>
          )}
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            <span className="hidden sm:inline">Security</span>
          </TabsTrigger>
        </TabsList>
        
        {/* Workspace Tab */}
        <TabsContent value="workspace" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Workspace Settings</CardTitle>
              <CardDescription>Configure your workspace branding and defaults</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="workspace-name">Workspace Name</Label>
                  <Input
                    id="workspace-name"
                    value={workspaceSettings.name}
                    onChange={(e) => setWorkspaceSettings({...workspaceSettings, name: e.target.value})}
                    placeholder="My Workspace"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="primary-color">Primary Color</Label>
                  <div className="flex gap-2">
                    <Input
                      id="primary-color"
                      type="color"
                      value={workspaceSettings.primary_color}
                      onChange={(e) => setWorkspaceSettings({...workspaceSettings, primary_color: e.target.value})}
                      className="w-16 h-10 p-1"
                    />
                    <Input
                      value={workspaceSettings.primary_color}
                      onChange={(e) => setWorkspaceSettings({...workspaceSettings, primary_color: e.target.value})}
                      placeholder="#6366F1"
                    />
                  </div>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={workspaceSettings.description}
                  onChange={(e) => setWorkspaceSettings({...workspaceSettings, description: e.target.value})}
                  placeholder="A brief description of your workspace"
                />
              </div>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Select 
                    value={workspaceSettings.timezone} 
                    onValueChange={(v) => setWorkspaceSettings({...workspaceSettings, timezone: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select timezone" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="UTC">UTC</SelectItem>
                      <SelectItem value="America/New_York">Eastern Time</SelectItem>
                      <SelectItem value="America/Chicago">Central Time</SelectItem>
                      <SelectItem value="America/Denver">Mountain Time</SelectItem>
                      <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                      <SelectItem value="Europe/London">London</SelectItem>
                      <SelectItem value="Europe/Paris">Paris</SelectItem>
                      <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="currency">Default Currency</Label>
                  <Select 
                    value={workspaceSettings.currency} 
                    onValueChange={(v) => setWorkspaceSettings({...workspaceSettings, currency: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select currency" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USD">USD ($)</SelectItem>
                      <SelectItem value="EUR">EUR (€)</SelectItem>
                      <SelectItem value="GBP">GBP (£)</SelectItem>
                      <SelectItem value="CAD">CAD ($)</SelectItem>
                      <SelectItem value="AUD">AUD ($)</SelectItem>
                      <SelectItem value="JPY">JPY (¥)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
                <div className="flex justify-end">
                  <Button onClick={saveWorkspaceSettings} disabled={saving}>
                    {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  Sales SLAs
                </CardTitle>
                <CardDescription>
                  Configure speed-to-lead and cadence windows used for SLA alerts in Leads and Pipeline.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Speed-to-Lead (minutes)</Label>
                  <Input
                    type="number"
                    min={1}
                    value={workspaceSettings.sla_config?.speed_to_lead_minutes ?? DEFAULT_SLA_CONFIG.speed_to_lead_minutes}
                    onChange={(e) =>
                      setWorkspaceSettings({
                        ...workspaceSettings,
                        sla_config: {
                          ...(workspaceSettings.sla_config || {}),
                          speed_to_lead_minutes: e.target.value === '' ? '' : Number(e.target.value)
                        }
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Time from lead creation to first touchpoint.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Lead Cadence (hours)</Label>
                  <Input
                    type="number"
                    min={1}
                    value={workspaceSettings.sla_config?.lead_cadence_hours ?? DEFAULT_SLA_CONFIG.lead_cadence_hours}
                    onChange={(e) =>
                      setWorkspaceSettings({
                        ...workspaceSettings,
                        sla_config: {
                          ...(workspaceSettings.sla_config || {}),
                          lead_cadence_hours: e.target.value === '' ? '' : Number(e.target.value)
                        }
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Max time allowed without a touchpoint on a lead.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Deal Cadence (hours)</Label>
                  <Input
                    type="number"
                    min={1}
                    value={workspaceSettings.sla_config?.deal_cadence_hours ?? DEFAULT_SLA_CONFIG.deal_cadence_hours}
                    onChange={(e) =>
                      setWorkspaceSettings({
                        ...workspaceSettings,
                        sla_config: {
                          ...(workspaceSettings.sla_config || {}),
                          deal_cadence_hours: e.target.value === '' ? '' : Number(e.target.value)
                        }
                      })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Max time allowed without a touchpoint on an open deal.
                  </p>
                </div>
              </CardContent>
            </Card>

            {(user?.role === 'admin' || user?.role === 'manager') && (
              <Card>
                <CardHeader>
                  <CardTitle>Partner Pipelines</CardTitle>
                  <CardDescription>
                    Assign a default pipeline per Partner Sales partner (used when pushing a Partner Sales lead to the pipeline).
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {partnersList.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No partners found. Create a partner by creating a Partner Sales lead.</p>
                  ) : pipelinesList.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No pipelines found. Create one in the Pipelines API or seed data.</p>
                  ) : (
                    <div className="rounded-lg border overflow-hidden">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Partner</TableHead>
                            <TableHead>Default Pipeline</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {partnersList.map((partner) => (
                            <TableRow key={partner.id}>
                              <TableCell className="font-medium">{partner.name}</TableCell>
                              <TableCell>
                                <Select
                                  value={partner.default_pipeline_id || 'default'}
                                  onValueChange={(v) =>
                                    updatePartnerDefaultPipeline(partner.id, v === 'default' ? '' : v)
                                  }
                                  disabled={savingPartnerId === partner.id}
                                >
                                  <SelectTrigger className="w-[260px]">
                                    <SelectValue placeholder="Select pipeline" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="default">Workspace Default (no override)</SelectItem>
                                    {pipelinesList.map((p) => (
                                      <SelectItem key={p.id} value={p.id}>
                                        {p.name}{p.is_default ? ' (Default)' : ''}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </TableCell>
                              <TableCell className="text-right">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => cloneDefaultPipelineForPartner(partner)}
                                  disabled={cloningPartnerId === partner.id}
                                >
                                  {cloningPartnerId === partner.id ? (
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                  ) : (
                                    <Plus className="w-4 h-4 mr-2" />
                                  )}
                                  Clone Default & Assign
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>
          
          {/* AI & Intelligence Tab */}
          <TabsContent value="ai" className="space-y-6">
            {/* AI Status Alert */}
          {aiConfig.configured_providers?.length === 0 && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>AI Not Configured</AlertTitle>
              <AlertDescription>
                No AI provider is configured. Please add an API key in the Integrations tab to enable AI features.
                A fallback key may be available from the platform.
              </AlertDescription>
            </Alert>
          )}
          
          {/* AI Provider Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>AI Provider Configuration</CardTitle>
              <CardDescription>Configure your default AI provider and model for all AI features</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Default Provider</Label>
                  <Select 
                    value={aiConfig.default_provider} 
                    onValueChange={(v) => setAiConfig({...aiConfig, default_provider: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
                      <SelectItem value="openrouter">OpenRouter</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Default Model</Label>
                  <Select 
                    value={aiConfig.default_model} 
                    onValueChange={(v) => setAiConfig({...aiConfig, default_model: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {aiConfig.default_provider === 'openai' && (
                        <>
                          <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                          <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                          <SelectItem value="gpt-5.2">GPT-5.2</SelectItem>
                        </>
                      )}
                      {aiConfig.default_provider === 'anthropic' && (
                        <>
                          <SelectItem value="claude-4-sonnet-20250514">Claude Sonnet 4</SelectItem>
                          <SelectItem value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</SelectItem>
                        </>
                      )}
                      {aiConfig.default_provider === 'openrouter' && (
                        <SelectItem value="auto">Auto (Best Available)</SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Configured Providers */}
              <div className="space-y-2">
                <Label>Configured Providers</Label>
                <div className="flex flex-wrap gap-2">
                  {aiConfig.configured_providers?.length > 0 ? (
                    aiConfig.configured_providers.map(p => (
                      <Badge key={p.provider_type} variant="secondary" className="flex items-center gap-1">
                        <CheckCircle className="w-3 h-3 text-green-500" />
                        {p.provider_type}
                        {p.key_hint && <span className="text-muted-foreground ml-1">{p.key_hint}</span>}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-muted-foreground text-sm">No providers configured. Add keys in Integrations tab.</span>
                  )}
                </div>
              </div>
              
              <div className="flex justify-end">
                <Button onClick={saveAIConfig} disabled={saving}>
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save AI Config
                </Button>
              </div>
            </CardContent>
          </Card>
          
          {/* AI Features */}
          <Card>
            <CardHeader>
              <CardTitle>AI Features</CardTitle>
              <CardDescription>Enable or disable AI features across the platform</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { key: 'page_builder', name: 'AI Page Builder', description: 'Generate landing pages with AI' },
                  { key: 'lead_scoring', name: 'Lead Scoring', description: 'AI-powered lead qualification' },
                  { key: 'deal_analysis', name: 'Deal Analysis', description: 'Analyze deal potential and risks' },
                  { key: 'contact_analysis', name: 'Contact Analysis', description: 'Analyze contact profiles' },
                  { key: 'workflow_ai', name: 'Workflow AI', description: 'AI-assisted workflow automation' },
                  { key: 'general_assistant', name: 'General Assistant', description: 'AI assistant for general tasks' }
                ].map(feature => (
                  <div key={feature.key} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="font-medium">{feature.name}</p>
                      <p className="text-sm text-muted-foreground">{feature.description}</p>
                    </div>
                    <Switch
                      checked={aiConfig.features_enabled?.[feature.key] ?? true}
                      onCheckedChange={(checked) => {
                        setAiConfig({
                          ...aiConfig,
                          features_enabled: {
                            ...aiConfig.features_enabled,
                            [feature.key]: checked
                          }
                        });
                      }}
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          
          {/* Usage Stats */}
          {aiUsageStats && (
            <Card>
              <CardHeader>
                <CardTitle>AI Usage (Last 30 Days)</CardTitle>
                <CardDescription>Monitor your AI usage and limits</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-muted-foreground">Daily Usage</span>
                      <Badge variant={aiUsageStats.current_usage?.daily?.remaining > 100 ? 'secondary' : 'destructive'}>
                        {aiUsageStats.current_usage?.daily?.remaining || 0} remaining
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-muted rounded-full h-2">
                        <div 
                          className="bg-primary rounded-full h-2 transition-all"
                          style={{ 
                            width: `${Math.min(100, (aiUsageStats.current_usage?.daily?.used || 0) / (aiUsageStats.current_usage?.daily?.limit || 1000) * 100)}%`
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {aiUsageStats.current_usage?.daily?.used || 0} / {aiUsageStats.current_usage?.daily?.limit || 1000}
                      </span>
                    </div>
                  </div>
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-muted-foreground">Monthly Usage</span>
                      <Badge variant={aiUsageStats.current_usage?.monthly?.remaining > 1000 ? 'secondary' : 'destructive'}>
                        {aiUsageStats.current_usage?.monthly?.remaining || 0} remaining
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-muted rounded-full h-2">
                        <div 
                          className="bg-primary rounded-full h-2 transition-all"
                          style={{ 
                            width: `${Math.min(100, (aiUsageStats.current_usage?.monthly?.used || 0) / (aiUsageStats.current_usage?.monthly?.limit || 25000) * 100)}%`
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {aiUsageStats.current_usage?.monthly?.used || 0} / {aiUsageStats.current_usage?.monthly?.limit || 25000}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
        
        {/* Integrations Tab */}
        <TabsContent value="integrations" className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold">Integrations</h2>
              <p className="text-sm text-muted-foreground">Manage your API keys and service connections</p>
            </div>
            <Button onClick={() => setShowAddIntegration(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Integration
            </Button>
          </div>
          
          {/* Security Warning */}
          <Alert>
            <Shield className="h-4 w-4" />
            <AlertTitle>Security Notice</AlertTitle>
            <AlertDescription>
              API keys are encrypted and stored securely. Keys are never displayed after initial entry.
              All API calls are executed server-side - keys are never exposed to the browser.
            </AlertDescription>
          </Alert>
          
          {/* AI Providers */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="w-5 h-5" />
                AI Providers
              </CardTitle>
              <CardDescription>Configure AI model providers for intelligent features</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {providers?.providers?.ai?.map(provider => {
                  const integration = integrations.find(i => i.provider_type === provider.type);
                  return (
                    <div key={provider.type} className={`p-4 border rounded-lg ${integration ? 'border-green-500/30 bg-green-500/5' : ''}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getProviderIcon(provider.type)}
                          <div>
                            <p className="font-medium">{provider.name}</p>
                            <p className="text-sm text-muted-foreground">{provider.description}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {integration ? (
                            <>
                              <Badge variant="secondary" className="flex items-center gap-1">
                                <CheckCircle className="w-3 h-3 text-green-500" />
                                Configured
                              </Badge>
                              <span className="text-sm text-muted-foreground">{integration.key_hint}</span>
                              <Switch
                                checked={integration.enabled}
                                onCheckedChange={(checked) => toggleIntegration(provider.type, checked)}
                              />
                              <Button variant="ghost" size="sm" onClick={() => revokeIntegration(provider.type)}>
                                <Trash2 className="w-4 h-4 text-destructive" />
                              </Button>
                            </>
                          ) : (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                setSelectedProvider(provider);
                                setShowAddIntegration(true);
                              }}
                            >
                              <Plus className="w-4 h-4 mr-1" />
                              Add Key
                            </Button>
                          )}
                        </div>
                      </div>
                      {integration?.last_used_at && (
                        <p className="text-xs text-muted-foreground mt-2">
                          Last used: {formatTimestamp(integration.last_used_at)}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
          
          {/* Communication Providers */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                Communications
              </CardTitle>
              <CardDescription>Email and SMS service providers</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {providers?.providers?.communication?.map(provider => {
                  const integration = integrations.find(i => i.provider_type === provider.type);
                  return (
                    <div key={provider.type} className={`p-4 border rounded-lg ${integration ? 'border-green-500/30 bg-green-500/5' : ''}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getProviderIcon(provider.type)}
                          <div>
                            <p className="font-medium">{provider.name}</p>
                            <p className="text-sm text-muted-foreground">{provider.description}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {integration ? (
                            <>
                              <Badge variant="secondary" className="flex items-center gap-1">
                                <CheckCircle className="w-3 h-3 text-green-500" />
                                Configured
                              </Badge>
                              <Button variant="ghost" size="sm" onClick={() => revokeIntegration(provider.type)}>
                                <Trash2 className="w-4 h-4 text-destructive" />
                              </Button>
                            </>
                          ) : (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                setSelectedProvider(provider);
                                setShowAddIntegration(true);
                              }}
                            >
                              <Plus className="w-4 h-4 mr-1" />
                              {provider.type === 'discord' ? 'Add Webhook' : 'Add Key'}
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
          
          {/* Payment Providers */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                Payments
              </CardTitle>
              <CardDescription>Payment processing and payout services</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {providers?.providers?.payment?.map(provider => {
                  const integration = integrations.find(i => i.provider_type === provider.type);
                  return (
                    <div key={provider.type} className={`p-4 border rounded-lg ${integration ? 'border-green-500/30 bg-green-500/5' : ''}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getProviderIcon(provider.type)}
                          <div>
                            <p className="font-medium">{provider.name}</p>
                            <p className="text-sm text-muted-foreground">{provider.description}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {integration ? (
                            <>
                              <Badge variant="secondary" className="flex items-center gap-1">
                                <CheckCircle className="w-3 h-3 text-green-500" />
                                Configured
                              </Badge>
                              <Button variant="ghost" size="sm" onClick={() => revokeIntegration(provider.type)}>
                                <Trash2 className="w-4 h-4 text-destructive" />
                              </Button>
                            </>
                          ) : (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                setSelectedProvider(provider);
                                setShowAddIntegration(true);
                              }}
                            >
                              <Plus className="w-4 h-4 mr-1" />
                              Add Key
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Affiliates Tab */}
        <TabsContent value="affiliates" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Affiliate System Settings</CardTitle>
              <CardDescription>Configure your affiliate program defaults</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between py-2 border-b">
                <div>
                  <p className="font-medium">Enable Affiliate System</p>
                  <p className="text-sm text-muted-foreground">Allow affiliate registrations and tracking</p>
                </div>
                <Switch
                  checked={affiliateSettings.enabled}
                  onCheckedChange={(checked) => setAffiliateSettings({...affiliateSettings, enabled: checked})}
                />
              </div>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Default Currency</Label>
                  <Select 
                    value={affiliateSettings.default_currency} 
                    onValueChange={(v) => setAffiliateSettings({...affiliateSettings, default_currency: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select currency" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USD">USD ($)</SelectItem>
                      <SelectItem value="EUR">EUR (€)</SelectItem>
                      <SelectItem value="GBP">GBP (£)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Attribution Window (Days)</Label>
                  <Input
                    type="number"
                    value={affiliateSettings.default_attribution_window_days}
                    onChange={(e) => setAffiliateSettings({...affiliateSettings, default_attribution_window_days: parseInt(e.target.value) || 30})}
                    min={1}
                    max={365}
                  />
                </div>
              </div>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Approval Mode</Label>
                  <Select 
                    value={affiliateSettings.approval_mode} 
                    onValueChange={(v) => setAffiliateSettings({...affiliateSettings, approval_mode: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual">Manual Approval</SelectItem>
                      <SelectItem value="auto">Auto-Approve</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Minimum Payout Threshold</Label>
                  <Input
                    type="number"
                    value={affiliateSettings.min_payout_threshold}
                    onChange={(e) => setAffiliateSettings({...affiliateSettings, min_payout_threshold: parseFloat(e.target.value) || 50})}
                    min={0}
                  />
                </div>
              </div>
              
              <div className="flex justify-end">
                <Button onClick={saveAffiliateSettings} disabled={saving}>
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        {/* Team Management Tab */}
        {(user?.role === 'admin' || user?.role === 'manager') && (
        <TabsContent value="team" className="space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold">Team Members</h2>
              <p className="text-sm text-muted-foreground">
                Manage your team's accounts and permissions
              </p>
            </div>
            <Button onClick={() => setShowAddMember(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Member
            </Button>
          </div>

          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Joined</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {teamMembers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground">
                        No team members yet
                      </TableCell>
                    </TableRow>
                  ) : (
                    teamMembers.map(member => (
                      <TableRow key={member.id}>
                        <TableCell className="font-medium">
                          {member.full_name || `${member.first_name} ${member.last_name}`}
                        </TableCell>
                        <TableCell>{member.email}</TableCell>
                        <TableCell>
                          <Badge variant={
                            member.role === 'admin' ? 'default' :
                            member.role === 'manager' ? 'secondary' :
                            'outline'
                          }>
                            {member.role}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={member.is_active ? 'secondary' : 'destructive'}>
                            {member.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatTimestamp(member.created_at)}</TableCell>
                        <TableCell className="text-right">
                          {member.id !== user?.id && (
                            <div className="flex justify-end items-center gap-2">
                              <Button
                                variant="ghost" size="sm"
                                onClick={() => setEditingMember({...member})}
                              >
                                <Pencil className="w-3 h-3 mr-1" />
                                Edit
                              </Button>
                              <Switch
                                checked={member.is_active}
                                onCheckedChange={(checked) =>
                                  toggleMemberActive(member.id, checked)
                                }
                              />
                            </div>
                          )}
                          {member.id === user?.id && (
                            <span className="text-xs text-muted-foreground">You</span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
        )}

        {/* Security & Audit Tab */}
        <TabsContent value="security" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Audit Log</CardTitle>
              <CardDescription>Track all settings and integration changes</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Action</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.length > 0 ? (
                    auditLogs.map(log => (
                      <TableRow key={log.id}>
                        <TableCell>
                          <Badge variant={
                            log.action.includes('add') ? 'default' :
                            log.action.includes('revoke') ? 'destructive' :
                            'secondary'
                          }>
                            {log.action.replace(/_/g, ' ')}
                          </Badge>
                        </TableCell>
                        <TableCell>{log.provider_type || '-'}</TableCell>
                        <TableCell>{log.actor_name || 'System'}</TableCell>
                        <TableCell>{formatTimestamp(log.timestamp)}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground">
                        No audit logs yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              
              {auditTotal > 20 && (
                <div className="flex justify-center gap-2 mt-4">
                  <Button 
                    variant="outline" 
                    size="sm"
                    disabled={auditPage === 1}
                    onClick={() => loadAuditLogs(auditPage - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground self-center">
                    Page {auditPage} of {Math.ceil(auditTotal / 20)}
                  </span>
                  <Button 
                    variant="outline" 
                    size="sm"
                    disabled={auditPage >= Math.ceil(auditTotal / 20)}
                    onClick={() => loadAuditLogs(auditPage + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Security Best Practices</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium">Keys Encrypted at Rest</p>
                  <p className="text-sm text-muted-foreground">All API keys are encrypted using AES-256 before storage</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium">Server-Side Execution</p>
                  <p className="text-sm text-muted-foreground">All AI and integration calls are made from the server - keys are never exposed to browsers</p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 bg-muted rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
                <div>
                  <p className="font-medium">Audit Trail</p>
                  <p className="text-sm text-muted-foreground">All key additions, rotations, and revocations are logged for compliance</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
      
      {/* Add Integration Dialog */}
      <Dialog
        open={showAddIntegration}
        onOpenChange={(open) => {
          setShowAddIntegration(open);
          if (!open) {
            setSelectedProvider(null);
            setNewApiKey('');
            setProviderConfig({});
            setShowKey(false);
            setTesting(false);
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {selectedProvider ? `Configure ${selectedProvider.name}` : 'Add Integration'}
            </DialogTitle>
            <DialogDescription>
              {selectedProvider?.description || 'Select a provider and enter your API key'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {!selectedProvider && (
              <div className="space-y-2">
                <Label>Select Provider</Label>
                <Select onValueChange={(v) => {
                  const allProviders = [
                    ...(providers?.providers?.ai || []),
                    ...(providers?.providers?.communication || []),
                    ...(providers?.providers?.payment || [])
                  ];
                  const provider = allProviders.find(p => p.type === v);
                  setSelectedProvider(provider);
                  setProviderConfig({});
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a provider" />
                  </SelectTrigger>
                  <SelectContent>
                    {[
                      ...(providers?.providers?.ai || []),
                      ...(providers?.providers?.communication || []),
                      ...(providers?.providers?.payment || [])
                    ].map((p) => (
                      <SelectItem key={p.type} value={p.type}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            
            {selectedProvider && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="api-key">{selectedProvider.type === 'discord' ? 'Webhook URL' : 'API Key'}</Label>
                  <div className="relative">
                    <Input
                      id="api-key"
                      type={showKey ? 'text' : 'password'}
                      value={newApiKey}
                      onChange={(e) => setNewApiKey(e.target.value)}
                      placeholder={
                        selectedProvider.type === 'discord'
                          ? 'https://discord.com/api/webhooks/...'
                          : `Enter your ${selectedProvider.name} API key`
                      }
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowKey(!showKey)}
                    >
                      {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {selectedProvider.type === 'discord' ? (
                      <>
                        Create a Discord webhook for your channel and paste the URL here.{' '}
                        {selectedProvider.key_url && (
                          <a href={selectedProvider.key_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                            Learn how <ExternalLink className="w-3 h-3 inline" />
                          </a>
                        )}
                      </>
                    ) : (
                      <>
                        Get your key from{' '}
                        {selectedProvider.key_url ? (
                          <a href={selectedProvider.key_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                            {selectedProvider.name} Dashboard <ExternalLink className="w-3 h-3 inline" />
                          </a>
                        ) : (
                          `${selectedProvider.name} dashboard`
                        )}
                      </>
                    )}
                  </p>
                </div>

                {selectedProvider.type === 'sendgrid' && (
                  <div className="grid grid-cols-1 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="sendgrid-from-email">From Email</Label>
                      <Input
                        id="sendgrid-from-email"
                        type="email"
                        value={providerConfig.from_email || ''}
                        onChange={(e) => setProviderConfig((prev) => ({ ...prev, from_email: e.target.value }))}
                        placeholder="noreply@yourdomain.com"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="sendgrid-from-name">From Name (optional)</Label>
                      <Input
                        id="sendgrid-from-name"
                        value={providerConfig.from_name || ''}
                        onChange={(e) => setProviderConfig((prev) => ({ ...prev, from_name: e.target.value }))}
                        placeholder="Elev8 CRM"
                      />
                    </div>
                  </div>
                )}

                {selectedProvider.type === 'twilio' && (
                  <div className="grid grid-cols-1 gap-3">
                    <div className="space-y-2">
                      <Label htmlFor="twilio-account-sid">Account SID</Label>
                      <Input
                        id="twilio-account-sid"
                        value={providerConfig.account_sid || ''}
                        onChange={(e) => setProviderConfig((prev) => ({ ...prev, account_sid: e.target.value }))}
                        placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="twilio-from-number">From Number</Label>
                      <Input
                        id="twilio-from-number"
                        value={providerConfig.from_number || ''}
                        onChange={(e) => setProviderConfig((prev) => ({ ...prev, from_number: e.target.value }))}
                        placeholder="+15551234567"
                      />
                    </div>
                  </div>
                )}
                
                <Alert>
                  <Shield className="h-4 w-4" />
                  <AlertDescription className="text-xs">
                    Your key will be encrypted immediately and never displayed again.
                  </AlertDescription>
                </Alert>
              </>
            )}
          </div>
          
          <DialogFooter className="flex gap-2">
            {selectedProvider && (
              <Button variant="outline" onClick={testConnection} disabled={testing || !newApiKey || !isProviderConfigValid()}>
                {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
                Test Connection
              </Button>
            )}
            <Button onClick={addIntegration} disabled={saving || !selectedProvider || !newApiKey || !isProviderConfigValid()}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Save Integration
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Team Member Dialog */}
      <Dialog open={showAddMember} onOpenChange={setShowAddMember}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add Team Member</DialogTitle>
            <DialogDescription>
              Create a new account for a team member
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label>First Name</Label>
                <Input value={newMember.first_name}
                  onChange={(e) => setNewMember({...newMember, first_name: e.target.value})}
                  placeholder="Jane" />
              </div>
              <div className="space-y-2">
                <Label>Last Name</Label>
                <Input value={newMember.last_name}
                  onChange={(e) => setNewMember({...newMember, last_name: e.target.value})}
                  placeholder="Doe" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input type="email" value={newMember.email}
                onChange={(e) => setNewMember({...newMember, email: e.target.value})}
                placeholder="jane@company.com" />
            </div>
            <div className="space-y-2">
              <Label>Password</Label>
              <Input type="password" value={newMember.password}
                onChange={(e) => setNewMember({...newMember, password: e.target.value})}
                placeholder="Minimum 6 characters" />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={newMember.role}
                onValueChange={(v) => setNewMember({...newMember, role: v})}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="manager">Manager</SelectItem>
                  <SelectItem value="sales">Sales</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Phone (optional)</Label>
              <Input value={newMember.phone}
                onChange={(e) => setNewMember({...newMember, phone: e.target.value})}
                placeholder="+1 (555) 000-0000" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddMember(false)}>Cancel</Button>
            <Button onClick={createTeamMember} disabled={saving ||
              !newMember.email || !newMember.password ||
              !newMember.first_name || !newMember.last_name}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Add Member
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Team Member Dialog */}
      <Dialog open={!!editingMember} onOpenChange={(open) => !open && setEditingMember(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Team Member</DialogTitle>
            <DialogDescription>
              Update {editingMember?.full_name || 'team member'}'s account
            </DialogDescription>
          </DialogHeader>
          {editingMember && (
            <div className="space-y-4 py-4">
              <div className="grid gap-4 grid-cols-2">
                <div className="space-y-2">
                  <Label>First Name</Label>
                  <Input value={editingMember.first_name}
                    onChange={(e) => setEditingMember({...editingMember, first_name: e.target.value})} />
                </div>
                <div className="space-y-2">
                  <Label>Last Name</Label>
                  <Input value={editingMember.last_name}
                    onChange={(e) => setEditingMember({...editingMember, last_name: e.target.value})} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={editingMember.email} disabled className="bg-muted" />
                <p className="text-xs text-muted-foreground">Email cannot be changed</p>
              </div>
              <div className="space-y-2">
                <Label>Role</Label>
                <Select value={editingMember.role}
                  onValueChange={(v) => setEditingMember({...editingMember, role: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="manager">Manager</SelectItem>
                    <SelectItem value="sales">Sales</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input value={editingMember.phone || ''}
                  onChange={(e) => setEditingMember({...editingMember, phone: e.target.value})} />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingMember(null)}>Cancel</Button>
            <Button onClick={() => updateTeamMember(editingMember.id, {
              first_name: editingMember.first_name,
              last_name: editingMember.last_name,
              role: editingMember.role,
              phone: editingMember.phone
            })} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SettingsPage;
