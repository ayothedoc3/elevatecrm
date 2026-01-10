import React, { useState, useEffect } from 'react';
import {
  Settings, Key, Bot, Globe, Users, Shield, AlertCircle,
  CheckCircle, XCircle, Eye, EyeOff, RefreshCw, Trash2,
  Plus, Save, ExternalLink, Zap, MessageSquare, CreditCard,
  Clock, Activity, ChevronRight, Info, Loader2
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
    currency: 'USD'
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
  
  // External API state
  const [apiKeys, setApiKeys] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [showCreateApiKey, setShowCreateApiKey] = useState(false);
  const [showCreateWebhook, setShowCreateWebhook] = useState(false);
  const [newApiKeyName, setNewApiKeyName] = useState('');
  const [createdApiKey, setCreatedApiKey] = useState(null);
  const [newWebhook, setNewWebhook] = useState({ url: '', events: [] });
  
  // Dialog state
  const [showAddIntegration, setShowAddIntegration] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [newApiKey, setNewApiKey] = useState('');
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
        loadExternalApiData()
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
        setWorkspaceSettings(data);
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
  
  const addIntegration = async () => {
    if (!selectedProvider || !newApiKey) {
      toast({ title: "Error", description: "Please select a provider and enter an API key", variant: "destructive" });
      return;
    }
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/settings/integrations`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          provider_type: selectedProvider.type,
          api_key: newApiKey
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
          api_key: newApiKey || null
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
    if (!window.confirm(`Are you sure you want to revoke the ${providerType} integration? This will permanently delete the API key.`)) {
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
        <TabsList className="grid w-full grid-cols-5 lg:w-auto lg:inline-grid">
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
      <Dialog open={showAddIntegration} onOpenChange={setShowAddIntegration}>
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
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a provider" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
                    <SelectItem value="openrouter">OpenRouter</SelectItem>
                    <SelectItem value="twilio">Twilio</SelectItem>
                    <SelectItem value="sendgrid">SendGrid</SelectItem>
                    <SelectItem value="stripe">Stripe</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            
            {selectedProvider && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="api-key">API Key</Label>
                  <div className="relative">
                    <Input
                      id="api-key"
                      type={showKey ? 'text' : 'password'}
                      value={newApiKey}
                      onChange={(e) => setNewApiKey(e.target.value)}
                      placeholder={`Enter your ${selectedProvider.name} API key`}
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
                    Get your key from{' '}
                    <a href={selectedProvider.key_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                      {selectedProvider.name} Dashboard <ExternalLink className="w-3 h-3 inline" />
                    </a>
                  </p>
                </div>
                
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
              <Button variant="outline" onClick={testConnection} disabled={testing || !newApiKey}>
                {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
                Test Connection
              </Button>
            )}
            <Button onClick={addIntegration} disabled={saving || !selectedProvider || !newApiKey}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Save Integration
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SettingsPage;
