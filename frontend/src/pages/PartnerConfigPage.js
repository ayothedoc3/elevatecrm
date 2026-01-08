/**
 * Partner Configuration Page
 * 
 * Per Elev8 PRD Section 12:
 * - Partner-specific pipeline configurations
 * - Partner-specific required fields
 * - Partner KPI targets and tracking
 * - Compliance rules management
 */

import React, { useState, useEffect } from 'react';
import {
  Building2, Settings, Target, FileText, Shield, BarChart3,
  ChevronRight, Loader2, RefreshCw, Save, AlertTriangle,
  Check, Plus, X, Edit, TrendingUp, TrendingDown, Minus
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { Alert, AlertDescription } from '../components/ui/alert';
import { useToast } from '../hooks/use-toast';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const formatCurrency = (value) => {
  if (!value) return '$0';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
};

const formatPercent = (value) => {
  if (value === null || value === undefined) return '0%';
  return `${value.toFixed(1)}%`;
};

const PartnerConfigPage = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Data state
  const [partners, setPartners] = useState([]);
  const [selectedPartner, setSelectedPartner] = useState(null);
  const [partnerConfig, setPartnerConfig] = useState(null);
  const [partnerKpis, setPartnerKpis] = useState(null);
  const [complianceCheck, setComplianceCheck] = useState(null);
  
  // Edit state
  const [activeTab, setActiveTab] = useState('kpis');
  const [editMode, setEditMode] = useState(false);
  const [editedConfig, setEditedConfig] = useState(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  const loadPartners = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/partners?page_size=100`, {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setPartners(data.partners || []);
      }
    } catch (error) {
      console.error('Error loading partners:', error);
      toast({ title: "Error", description: "Failed to load partners", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const loadPartnerData = async (partnerId) => {
    try {
      const [configRes, kpisRes, complianceRes] = await Promise.all([
        fetch(`${API_URL}/api/elev8/partners/${partnerId}/config`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/partners/${partnerId}/kpis?period=month`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/partners/${partnerId}/compliance-check`, { headers: getAuthHeaders() })
      ]);
      
      if (configRes.ok) {
        const config = await configRes.json();
        setPartnerConfig(config);
        setEditedConfig(JSON.parse(JSON.stringify(config)));
      }
      if (kpisRes.ok) setPartnerKpis(await kpisRes.json());
      if (complianceRes.ok) setComplianceCheck(await complianceRes.json());
    } catch (error) {
      console.error('Error loading partner data:', error);
    }
  };

  useEffect(() => {
    loadPartners();
  }, []);

  const handleSelectPartner = async (partner) => {
    setSelectedPartner(partner);
    setPartnerConfig(null);
    setPartnerKpis(null);
    setEditMode(false);
    await loadPartnerData(partner.id);
  };

  const handleSaveConfig = async () => {
    if (!selectedPartner || !editedConfig) return;
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/partners/${selectedPartner.id}/config`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          pipeline_config: editedConfig.pipeline_config,
          field_config: editedConfig.field_config,
          kpi_config: editedConfig.kpi_config,
          compliance_config: editedConfig.compliance_config
        })
      });
      
      if (response.ok) {
        toast({ title: "Success", description: "Configuration saved" });
        setEditMode(false);
        await loadPartnerData(selectedPartner.id);
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to save", variant: "destructive" });
      }
    } catch (error) {
      console.error('Error saving config:', error);
      toast({ title: "Error", description: "Failed to save configuration", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  // Performance indicator
  const getPerformanceIndicator = (value) => {
    if (value > 0) return { icon: TrendingUp, color: 'text-green-600', bg: 'bg-green-100' };
    if (value < 0) return { icon: TrendingDown, color: 'text-red-600', bg: 'bg-red-100' };
    return { icon: Minus, color: 'text-gray-600', bg: 'bg-gray-100' };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="partner-config-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Partner Configuration</h1>
          <p className="text-muted-foreground">Manage partner-specific settings and KPIs</p>
        </div>
        <Button variant="outline" onClick={loadPartners}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Partner List */}
        <div className="col-span-4">
          <Card className="h-[650px] flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Partners</CardTitle>
              <CardDescription>Select a partner to view configuration</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden p-0">
              <ScrollArea className="h-full p-4">
                <div className="space-y-2">
                  {partners.length > 0 ? partners.map(partner => (
                    <div
                      key={partner.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedPartner?.id === partner.id 
                          ? 'border-primary bg-primary/5' 
                          : 'hover:bg-muted/50'
                      }`}
                      onClick={() => handleSelectPartner(partner)}
                      data-testid={`partner-item-${partner.id}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-slate-100 rounded-lg">
                          <Building2 className="w-4 h-4 text-slate-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-sm truncate">{partner.name}</h4>
                          <p className="text-xs text-muted-foreground capitalize">
                            {partner.partner_type?.replace('_', ' ')}
                          </p>
                        </div>
                        <Badge 
                          variant="secondary" 
                          className={partner.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}
                        >
                          {partner.status}
                        </Badge>
                      </div>
                    </div>
                  )) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Building2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No partners found</p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Configuration Panel */}
        <div className="col-span-8">
          <Card className="h-[650px] flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">
                    {selectedPartner ? selectedPartner.name : 'Select a Partner'}
                  </CardTitle>
                  {selectedPartner && (
                    <CardDescription>
                      {selectedPartner.partner_type?.replace('_', ' ')} Partner
                    </CardDescription>
                  )}
                </div>
                {selectedPartner && partnerConfig && (
                  <div className="flex gap-2">
                    {editMode ? (
                      <>
                        <Button variant="outline" onClick={() => {
                          setEditMode(false);
                          setEditedConfig(JSON.parse(JSON.stringify(partnerConfig)));
                        }}>
                          Cancel
                        </Button>
                        <Button onClick={handleSaveConfig} disabled={saving}>
                          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                          Save
                        </Button>
                      </>
                    ) : (
                      <Button variant="outline" onClick={() => setEditMode(true)} data-testid="edit-config-btn">
                        <Edit className="w-4 h-4 mr-2" />
                        Edit Config
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {!selectedPartner ? (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Select a partner to view configuration</p>
                  </div>
                </div>
              ) : !partnerConfig ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList className="grid grid-cols-4 w-full">
                    <TabsTrigger value="kpis" data-testid="kpis-tab">
                      <BarChart3 className="w-4 h-4 mr-2" />
                      KPIs
                    </TabsTrigger>
                    <TabsTrigger value="pipeline" data-testid="pipeline-tab">
                      <Target className="w-4 h-4 mr-2" />
                      Pipeline
                    </TabsTrigger>
                    <TabsTrigger value="fields" data-testid="fields-tab">
                      <FileText className="w-4 h-4 mr-2" />
                      Fields
                    </TabsTrigger>
                    <TabsTrigger value="compliance" data-testid="compliance-tab">
                      <Shield className="w-4 h-4 mr-2" />
                      Compliance
                    </TabsTrigger>
                  </TabsList>

                  {/* KPIs Tab */}
                  <TabsContent value="kpis" className="mt-4 space-y-4">
                    {partnerKpis && (
                      <>
                        {/* Performance Cards */}
                        <div className="grid grid-cols-3 gap-4">
                          <Card>
                            <CardContent className="pt-4">
                              <p className="text-xs text-muted-foreground">Win Rate</p>
                              <p className="text-2xl font-bold">{formatPercent(partnerKpis.metrics?.win_rate)}</p>
                              <div className="flex items-center gap-1 mt-1">
                                {(() => {
                                  const perf = getPerformanceIndicator(partnerKpis.performance?.win_rate_vs_target);
                                  const Icon = perf.icon;
                                  return (
                                    <>
                                      <span className={`p-1 rounded ${perf.bg}`}>
                                        <Icon className={`w-3 h-3 ${perf.color}`} />
                                      </span>
                                      <span className={`text-xs ${perf.color}`}>
                                        {partnerKpis.performance?.win_rate_vs_target > 0 ? '+' : ''}
                                        {partnerKpis.performance?.win_rate_vs_target?.toFixed(1)}% vs target
                                      </span>
                                    </>
                                  );
                                })()}
                              </div>
                            </CardContent>
                          </Card>

                          <Card>
                            <CardContent className="pt-4">
                              <p className="text-xs text-muted-foreground">Avg Deal Size</p>
                              <p className="text-2xl font-bold">{formatCurrency(partnerKpis.metrics?.avg_deal_size)}</p>
                              <div className="flex items-center gap-1 mt-1">
                                {(() => {
                                  const perf = getPerformanceIndicator(partnerKpis.performance?.deal_size_vs_target);
                                  const Icon = perf.icon;
                                  return (
                                    <>
                                      <span className={`p-1 rounded ${perf.bg}`}>
                                        <Icon className={`w-3 h-3 ${perf.color}`} />
                                      </span>
                                      <span className={`text-xs ${perf.color}`}>
                                        {formatCurrency(partnerKpis.performance?.deal_size_vs_target)} vs target
                                      </span>
                                    </>
                                  );
                                })()}
                              </div>
                            </CardContent>
                          </Card>

                          <Card>
                            <CardContent className="pt-4">
                              <p className="text-xs text-muted-foreground">Qualification Rate</p>
                              <p className="text-2xl font-bold">{formatPercent(partnerKpis.metrics?.qualification_rate)}</p>
                              <div className="flex items-center gap-1 mt-1">
                                {(() => {
                                  const perf = getPerformanceIndicator(partnerKpis.performance?.qualification_vs_target);
                                  const Icon = perf.icon;
                                  return (
                                    <>
                                      <span className={`p-1 rounded ${perf.bg}`}>
                                        <Icon className={`w-3 h-3 ${perf.color}`} />
                                      </span>
                                      <span className={`text-xs ${perf.color}`}>
                                        {partnerKpis.performance?.qualification_vs_target > 0 ? '+' : ''}
                                        {partnerKpis.performance?.qualification_vs_target?.toFixed(1)}% vs target
                                      </span>
                                    </>
                                  );
                                })()}
                              </div>
                            </CardContent>
                          </Card>
                        </div>

                        {/* Metrics Summary */}
                        <Card>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm">Performance Summary</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 gap-4">
                              <div className="space-y-3">
                                <div className="flex justify-between items-center py-2 border-b">
                                  <span className="text-sm text-muted-foreground">Leads Created</span>
                                  <span className="font-medium">{partnerKpis.metrics?.leads_created || 0}</span>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b">
                                  <span className="text-sm text-muted-foreground">Leads Qualified</span>
                                  <span className="font-medium">{partnerKpis.metrics?.leads_qualified || 0}</span>
                                </div>
                                <div className="flex justify-between items-center py-2">
                                  <span className="text-sm text-muted-foreground">Open Deals</span>
                                  <span className="font-medium">{partnerKpis.metrics?.deals_open || 0}</span>
                                </div>
                              </div>
                              <div className="space-y-3">
                                <div className="flex justify-between items-center py-2 border-b">
                                  <span className="text-sm text-muted-foreground">Deals Won</span>
                                  <span className="font-medium text-green-600">{partnerKpis.metrics?.deals_won || 0}</span>
                                </div>
                                <div className="flex justify-between items-center py-2 border-b">
                                  <span className="text-sm text-muted-foreground">Deals Lost</span>
                                  <span className="font-medium text-red-600">{partnerKpis.metrics?.deals_lost || 0}</span>
                                </div>
                                <div className="flex justify-between items-center py-2">
                                  <span className="text-sm text-muted-foreground">Pipeline Value</span>
                                  <span className="font-medium">{formatCurrency(partnerKpis.metrics?.pipeline_value)}</span>
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>

                        {/* KPI Targets - Editable */}
                        {editMode && editedConfig && (
                          <Card>
                            <CardHeader className="pb-2">
                              <CardTitle className="text-sm">KPI Targets</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              <div className="grid grid-cols-2 gap-4">
                                <div>
                                  <label className="text-sm font-medium">Target Win Rate (%)</label>
                                  <Input
                                    type="number"
                                    value={editedConfig.kpi_config?.target_win_rate || ''}
                                    onChange={(e) => setEditedConfig({
                                      ...editedConfig,
                                      kpi_config: {
                                        ...editedConfig.kpi_config,
                                        target_win_rate: parseFloat(e.target.value) || 0
                                      }
                                    })}
                                  />
                                </div>
                                <div>
                                  <label className="text-sm font-medium">Target Deal Size ($)</label>
                                  <Input
                                    type="number"
                                    value={editedConfig.kpi_config?.target_deal_size || ''}
                                    onChange={(e) => setEditedConfig({
                                      ...editedConfig,
                                      kpi_config: {
                                        ...editedConfig.kpi_config,
                                        target_deal_size: parseFloat(e.target.value) || 0
                                      }
                                    })}
                                  />
                                </div>
                                <div>
                                  <label className="text-sm font-medium">Target Qualification Rate (%)</label>
                                  <Input
                                    type="number"
                                    value={editedConfig.kpi_config?.target_qualification_rate || ''}
                                    onChange={(e) => setEditedConfig({
                                      ...editedConfig,
                                      kpi_config: {
                                        ...editedConfig.kpi_config,
                                        target_qualification_rate: parseFloat(e.target.value) || 0
                                      }
                                    })}
                                  />
                                </div>
                                <div>
                                  <label className="text-sm font-medium">Target Cycle Days</label>
                                  <Input
                                    type="number"
                                    value={editedConfig.kpi_config?.target_cycle_days || ''}
                                    onChange={(e) => setEditedConfig({
                                      ...editedConfig,
                                      kpi_config: {
                                        ...editedConfig.kpi_config,
                                        target_cycle_days: parseInt(e.target.value) || 0
                                      }
                                    })}
                                  />
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </>
                    )}
                  </TabsContent>

                  {/* Pipeline Tab */}
                  <TabsContent value="pipeline" className="mt-4 space-y-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Stage Mappings</CardTitle>
                        <CardDescription>Map universal stages to partner-specific names</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {editMode && editedConfig ? (
                          <div className="space-y-3">
                            <p className="text-sm text-muted-foreground">
                              Configure custom stage names for this partner (leave blank to use defaults)
                            </p>
                            {/* Stage mapping inputs would go here */}
                            <div className="p-4 bg-muted/50 rounded-lg text-center text-sm text-muted-foreground">
                              Stage mapping configuration coming soon
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {Object.keys(partnerConfig.pipeline_config?.stage_mappings || {}).length > 0 ? (
                              Object.entries(partnerConfig.pipeline_config.stage_mappings).map(([key, value]) => (
                                <div key={key} className="flex items-center justify-between py-2 border-b last:border-0">
                                  <span className="text-sm">{key}</span>
                                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                                  <span className="text-sm font-medium">{value}</span>
                                </div>
                              ))
                            ) : (
                              <p className="text-sm text-muted-foreground text-center py-4">
                                Using default stage names
                              </p>
                            )}
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Skipped Stages</CardTitle>
                        <CardDescription>Stages not applicable for this partner</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {partnerConfig.pipeline_config?.skip_stages?.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {partnerConfig.pipeline_config.skip_stages.map(stage => (
                              <Badge key={stage} variant="secondary">
                                {stage}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground text-center py-4">
                            No stages skipped - using full pipeline
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  </TabsContent>

                  {/* Fields Tab */}
                  <TabsContent value="fields" className="mt-4 space-y-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Required Fields by Stage</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {[
                          { key: 'required_at_qualification', label: 'At Qualification' },
                          { key: 'required_at_discovery', label: 'At Discovery' },
                          { key: 'required_at_proposal', label: 'At Proposal' },
                          { key: 'required_at_close', label: 'At Close' }
                        ].map(stage => (
                          <div key={stage.key} className="border-b pb-3 last:border-0 last:pb-0">
                            <p className="font-medium text-sm mb-2">{stage.label}</p>
                            <div className="flex flex-wrap gap-2">
                              {(partnerConfig.field_config?.[stage.key] || []).map(field => (
                                <Badge key={field} variant="outline">
                                  {field.replace(/_/g, ' ')}
                                </Badge>
                              ))}
                              {(partnerConfig.field_config?.[stage.key] || []).length === 0 && (
                                <span className="text-sm text-muted-foreground">No specific requirements</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>

                    {partnerConfig.field_config?.custom_fields?.length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">Custom Fields</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            {partnerConfig.field_config.custom_fields.map((field, idx) => (
                              <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
                                <span className="text-sm">{field.name || field}</span>
                                <Badge variant="secondary">{field.type || 'text'}</Badge>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </TabsContent>

                  {/* Compliance Tab */}
                  <TabsContent value="compliance" className="mt-4 space-y-4">
                    {/* Compliance Check Results */}
                    {complianceCheck && (
                      <Alert className={complianceCheck.is_compliant ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
                        {complianceCheck.is_compliant ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-red-600" />
                        )}
                        <AlertDescription className={complianceCheck.is_compliant ? 'text-green-700' : 'text-red-700'}>
                          {complianceCheck.is_compliant 
                            ? 'Partner is compliant with all rules' 
                            : 'Compliance issues detected'
                          }
                        </AlertDescription>
                      </Alert>
                    )}

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Compliance Rules</CardTitle>
                      </CardHeader>
                      <CardContent>
                        {(partnerConfig.compliance_config?.rules || []).length > 0 ? (
                          <ul className="space-y-2">
                            {partnerConfig.compliance_config.rules.map((rule, idx) => (
                              <li key={idx} className="flex items-start gap-2 text-sm">
                                <Shield className="w-4 h-4 text-blue-500 mt-0.5" />
                                {rule}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-muted-foreground text-center py-4">
                            No custom compliance rules
                          </p>
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Approval Thresholds</CardTitle>
                      </CardHeader>
                      <CardContent>
                        {Object.keys(partnerConfig.compliance_config?.approval_thresholds || {}).length > 0 ? (
                          <div className="space-y-2">
                            {Object.entries(partnerConfig.compliance_config.approval_thresholds).map(([key, value]) => (
                              <div key={key} className="flex items-center justify-between py-2 border-b last:border-0">
                                <span className="text-sm capitalize">{key.replace(/_/g, ' ')}</span>
                                <span className="font-medium text-sm">
                                  {typeof value === 'number' && key.includes('value') 
                                    ? formatCurrency(value) 
                                    : `${value}%`
                                  }
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground text-center py-4">
                            No approval thresholds configured
                          </p>
                        )}
                      </CardContent>
                    </Card>

                    {(partnerConfig.compliance_config?.required_certifications || []).length > 0 && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">Required Certifications</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex flex-wrap gap-2">
                            {partnerConfig.compliance_config.required_certifications.map((cert, idx) => (
                              <Badge key={idx} variant="outline">
                                {cert}
                              </Badge>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </TabsContent>
                </Tabs>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default PartnerConfigPage;
