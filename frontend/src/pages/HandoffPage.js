/**
 * Handoff to Delivery Page
 * 
 * Per Elev8 PRD Section 11:
 * - Manage handoff process for Closed Won deals
 * - Track required artifacts (SPICED, Gap Analysis, Proposal, Contract, etc.)
 * - Assign delivery owners and schedule kickoffs
 */

import React, { useState, useEffect } from 'react';
import {
  Send, CheckCircle2, Clock, FileText, User, Calendar,
  AlertTriangle, ChevronRight, Loader2, RefreshCw, Search,
  Eye, Package, Briefcase, Award, XCircle, Info, Check
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

// Artifact icons
const artifactIcons = {
  spiced_summary: FileText,
  gap_analysis: Eye,
  proposal: Package,
  contract: FileText,
  risk_notes: AlertTriangle,
  kickoff_checklist: CheckCircle2
};

const formatCurrency = (value) => {
  if (!value) return '$0';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const HandoffPage = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending');
  
  // Data state
  const [handoffs, setHandoffs] = useState([]);
  const [wonDeals, setWonDeals] = useState([]);
  const [users, setUsers] = useState([]);
  
  // Selected deal state
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [handoffStatus, setHandoffStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  
  // Dialog state
  const [showInitiateDialog, setShowInitiateDialog] = useState(false);
  const [showArtifactDialog, setShowArtifactDialog] = useState(false);
  const [showCompleteDialog, setShowCompleteDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [initiateForm, setInitiateForm] = useState({
    delivery_owner_id: '',
    kickoff_date: '',
    notes: ''
  });
  
  const [artifactForm, setArtifactForm] = useState({
    artifact_type: '',
    title: '',
    content: '',
    completed: false
  });

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [handoffsRes, dealsRes, usersRes] = await Promise.all([
        fetch(`${API_URL}/api/elev8/handoffs`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/deals?status=won&page_size=100`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/users`, { headers: getAuthHeaders() })
      ]);
      
      if (handoffsRes.ok) {
        const data = await handoffsRes.json();
        setHandoffs(data.handoffs || []);
      }
      if (dealsRes.ok) {
        const data = await dealsRes.json();
        setWonDeals(data.deals || []);
      }
      if (usersRes.ok) {
        const data = await usersRes.json();
        setUsers(data.users || []);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      toast({ title: "Error", description: "Failed to load data", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadHandoffStatus = async (dealId) => {
    setLoadingStatus(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/deals/${dealId}/handoff-status`, {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setHandoffStatus(data);
      }
    } catch (error) {
      console.error('Error loading handoff status:', error);
    } finally {
      setLoadingStatus(false);
    }
  };

  const handleSelectDeal = async (deal) => {
    setSelectedDeal(deal);
    await loadHandoffStatus(deal.id);
  };

  const handleInitiateHandoff = async () => {
    if (!selectedDeal || !initiateForm.delivery_owner_id) {
      toast({ title: "Error", description: "Please select a delivery owner", variant: "destructive" });
      return;
    }
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/deals/${selectedDeal.id}/handoff/initiate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(initiateForm)
      });
      
      if (response.ok) {
        toast({ title: "Success", description: "Handoff initiated successfully" });
        setShowInitiateDialog(false);
        setInitiateForm({ delivery_owner_id: '', kickoff_date: '', notes: '' });
        await loadHandoffStatus(selectedDeal.id);
        loadData();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to initiate handoff", variant: "destructive" });
      }
    } catch (error) {
      console.error('Error initiating handoff:', error);
      toast({ title: "Error", description: "Failed to initiate handoff", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateArtifact = async () => {
    if (!selectedDeal || !artifactForm.artifact_type) return;
    
    setSaving(true);
    try {
      const response = await fetch(
        `${API_URL}/api/elev8/deals/${selectedDeal.id}/handoff/artifact?artifact_type=${artifactForm.artifact_type}`,
        {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            title: artifactForm.title,
            content: artifactForm.content,
            completed: artifactForm.completed
          })
        }
      );
      
      if (response.ok) {
        toast({ title: "Success", description: "Artifact updated" });
        setShowArtifactDialog(false);
        setArtifactForm({ artifact_type: '', title: '', content: '', completed: false });
        await loadHandoffStatus(selectedDeal.id);
      } else {
        toast({ title: "Error", description: "Failed to update artifact", variant: "destructive" });
      }
    } catch (error) {
      console.error('Error updating artifact:', error);
      toast({ title: "Error", description: "Failed to update artifact", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleCompleteHandoff = async () => {
    if (!selectedDeal) return;
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/deals/${selectedDeal.id}/handoff/complete`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        toast({ title: "Success", description: "Handoff completed! Sales stages are now locked." });
        setShowCompleteDialog(false);
        await loadHandoffStatus(selectedDeal.id);
        loadData();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to complete handoff", variant: "destructive" });
      }
    } catch (error) {
      console.error('Error completing handoff:', error);
      toast({ title: "Error", description: "Failed to complete handoff", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  // Get deals without handoffs initiated
  const dealsWithoutHandoff = wonDeals.filter(
    deal => !handoffs.some(h => h.deal_id === deal.id)
  );
  
  // Get in-progress and completed handoffs
  const inProgressHandoffs = handoffs.filter(h => !h.completed);
  const completedHandoffs = handoffs.filter(h => h.completed);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="handoff-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Handoff to Delivery</h1>
          <p className="text-muted-foreground">Manage Closed Won deal handoffs</p>
        </div>
        <Button variant="outline" onClick={loadData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Awaiting Handoff</p>
                <p className="text-2xl font-bold text-orange-600">{dealsWithoutHandoff.length}</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-full">
                <Clock className="w-5 h-5 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">In Progress</p>
                <p className="text-2xl font-bold text-blue-600">{inProgressHandoffs.length}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <Send className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="text-2xl font-bold text-green-600">{completedHandoffs.length}</p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <CheckCircle2 className="w-5 h-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Won Deals Value</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(wonDeals.reduce((sum, d) => sum + (d.amount || 0), 0))}
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <Award className="w-5 h-5 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel - Deal List */}
        <div className="col-span-5">
          <Card className="h-[600px] flex flex-col">
            <CardHeader className="pb-2">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid grid-cols-3 w-full">
                  <TabsTrigger value="pending" data-testid="pending-tab">
                    Pending ({dealsWithoutHandoff.length})
                  </TabsTrigger>
                  <TabsTrigger value="in-progress" data-testid="in-progress-tab">
                    Active ({inProgressHandoffs.length})
                  </TabsTrigger>
                  <TabsTrigger value="completed" data-testid="completed-tab">
                    Done ({completedHandoffs.length})
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden p-0">
              <ScrollArea className="h-full p-4">
                {activeTab === 'pending' && (
                  <div className="space-y-2">
                    {dealsWithoutHandoff.length > 0 ? dealsWithoutHandoff.map(deal => (
                      <div
                        key={deal.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                          selectedDeal?.id === deal.id 
                            ? 'border-primary bg-primary/5' 
                            : 'hover:bg-muted/50'
                        }`}
                        onClick={() => handleSelectDeal(deal)}
                        data-testid={`deal-item-${deal.id}`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-sm">{deal.name}</h4>
                            <p className="text-xs text-muted-foreground">{deal.company_name}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium text-sm">{formatCurrency(deal.amount)}</p>
                            <Badge variant="secondary" className="bg-green-100 text-green-700">
                              Won
                            </Badge>
                          </div>
                        </div>
                      </div>
                    )) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <CheckCircle2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No deals pending handoff</p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'in-progress' && (
                  <div className="space-y-2">
                    {inProgressHandoffs.length > 0 ? inProgressHandoffs.map(handoff => (
                      <div
                        key={handoff.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                          selectedDeal?.id === handoff.deal_id 
                            ? 'border-primary bg-primary/5' 
                            : 'hover:bg-muted/50'
                        }`}
                        onClick={() => handleSelectDeal({ id: handoff.deal_id, name: handoff.deal_name, amount: handoff.deal_amount })}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-sm">{handoff.deal_name}</h4>
                            <p className="text-xs text-muted-foreground">
                              Owner: {handoff.delivery_owner_name}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium text-sm">{formatCurrency(handoff.deal_amount)}</p>
                            <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                              In Progress
                            </Badge>
                          </div>
                        </div>
                      </div>
                    )) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <Send className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No active handoffs</p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'completed' && (
                  <div className="space-y-2">
                    {completedHandoffs.length > 0 ? completedHandoffs.map(handoff => (
                      <div
                        key={handoff.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                          selectedDeal?.id === handoff.deal_id 
                            ? 'border-primary bg-primary/5' 
                            : 'hover:bg-muted/50'
                        }`}
                        onClick={() => handleSelectDeal({ id: handoff.deal_id, name: handoff.deal_name, amount: handoff.deal_amount })}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-sm">{handoff.deal_name}</h4>
                            <p className="text-xs text-muted-foreground">
                              Completed: {formatDate(handoff.completed_at)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium text-sm">{formatCurrency(handoff.deal_amount)}</p>
                            <Badge variant="secondary" className="bg-green-100 text-green-700">
                              Complete
                            </Badge>
                          </div>
                        </div>
                      </div>
                    )) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <Award className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No completed handoffs</p>
                      </div>
                    )}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Handoff Details */}
        <div className="col-span-7">
          <Card className="h-[600px] flex flex-col">
            <CardHeader>
              <CardTitle className="text-lg">
                {selectedDeal ? selectedDeal.name : 'Select a Deal'}
              </CardTitle>
              {selectedDeal && (
                <CardDescription>
                  {formatCurrency(selectedDeal.amount)} • Handoff Progress
                </CardDescription>
              )}
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              {!selectedDeal ? (
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  <div className="text-center">
                    <Briefcase className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Select a deal to view or manage handoff</p>
                  </div>
                </div>
              ) : loadingStatus ? (
                <div className="h-full flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
                </div>
              ) : handoffStatus ? (
                <div className="space-y-6">
                  {/* Handoff Status */}
                  {!handoffStatus.handoff_initiated ? (
                    <Alert>
                      <Info className="w-4 h-4" />
                      <AlertDescription>
                        Handoff has not been initiated for this deal. Click below to start the handoff process.
                      </AlertDescription>
                    </Alert>
                  ) : handoffStatus.handoff_completed ? (
                    <Alert className="border-green-200 bg-green-50">
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                      <AlertDescription className="text-green-700">
                        Handoff completed! Sales stages are locked.
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Readiness</span>
                        <span className="text-sm font-bold">{handoffStatus.readiness_percentage}%</span>
                      </div>
                      <Progress value={handoffStatus.readiness_percentage} className="h-2" />
                      <p className="text-xs text-muted-foreground">
                        Complete all required artifacts to finish handoff
                      </p>
                    </div>
                  )}

                  {/* Delivery Owner & Kickoff */}
                  {handoffStatus.handoff_initiated && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-muted/50 rounded-lg">
                        <p className="text-xs text-muted-foreground">Delivery Owner</p>
                        <p className="font-medium text-sm flex items-center gap-2">
                          <User className="w-4 h-4" />
                          {users.find(u => u.id === handoffStatus.delivery_owner_id)?.first_name || 'Not assigned'}
                        </p>
                      </div>
                      <div className="p-3 bg-muted/50 rounded-lg">
                        <p className="text-xs text-muted-foreground">Kickoff Date</p>
                        <p className="font-medium text-sm flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          {handoffStatus.kickoff_date ? formatDate(handoffStatus.kickoff_date) : 'Not scheduled'}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* SPICED Status */}
                  <div className="p-3 border rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-purple-500" />
                        <span className="font-medium text-sm">SPICED Summary</span>
                      </div>
                      {handoffStatus.has_spiced ? (
                        <Badge className="bg-green-100 text-green-700">
                          <Check className="w-3 h-3 mr-1" />
                          Complete
                        </Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700">
                          <XCircle className="w-3 h-3 mr-1" />
                          Missing
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Required Artifacts */}
                  <div>
                    <h4 className="font-medium text-sm mb-3">Required Artifacts</h4>
                    <div className="space-y-2">
                      {handoffStatus.required_artifacts?.filter(a => a.type !== 'spiced_summary').map(artifact => {
                        const existing = handoffStatus.artifacts?.find(a => a.artifact_type === artifact.type);
                        const Icon = artifactIcons[artifact.type] || FileText;
                        const isComplete = existing?.completed;
                        
                        return (
                          <div 
                            key={artifact.type}
                            className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                            onClick={() => {
                              if (!handoffStatus.handoff_completed && handoffStatus.handoff_initiated) {
                                setArtifactForm({
                                  artifact_type: artifact.type,
                                  title: existing?.title || artifact.name,
                                  content: existing?.content || '',
                                  completed: existing?.completed || false
                                });
                                setShowArtifactDialog(true);
                              }
                            }}
                          >
                            <div className="flex items-center gap-3">
                              <div className={`p-2 rounded-lg ${isComplete ? 'bg-green-100' : 'bg-slate-100'}`}>
                                <Icon className={`w-4 h-4 ${isComplete ? 'text-green-600' : 'text-slate-600'}`} />
                              </div>
                              <div>
                                <p className="font-medium text-sm">{artifact.name}</p>
                                <p className="text-xs text-muted-foreground">
                                  {artifact.required ? 'Required' : 'Optional'}
                                </p>
                              </div>
                            </div>
                            {isComplete ? (
                              <Badge className="bg-green-100 text-green-700">
                                <Check className="w-3 h-3 mr-1" />
                                Complete
                              </Badge>
                            ) : (
                              <ChevronRight className="w-4 h-4 text-muted-foreground" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 pt-4 border-t">
                    {!handoffStatus.handoff_initiated ? (
                      <Button 
                        className="flex-1" 
                        onClick={() => setShowInitiateDialog(true)}
                        data-testid="initiate-handoff-btn"
                      >
                        <Send className="w-4 h-4 mr-2" />
                        Initiate Handoff
                      </Button>
                    ) : !handoffStatus.handoff_completed ? (
                      <Button 
                        className="flex-1"
                        onClick={() => setShowCompleteDialog(true)}
                        disabled={!handoffStatus.can_complete}
                        data-testid="complete-handoff-btn"
                      >
                        <CheckCircle2 className="w-4 h-4 mr-2" />
                        Complete Handoff
                      </Button>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Initiate Handoff Dialog */}
      <Dialog open={showInitiateDialog} onOpenChange={setShowInitiateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Initiate Handoff</DialogTitle>
            <DialogDescription>
              Start the handoff process for {selectedDeal?.name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Delivery Owner *</label>
              <Select 
                value={initiateForm.delivery_owner_id} 
                onValueChange={(v) => setInitiateForm({ ...initiateForm, delivery_owner_id: v })}
              >
                <SelectTrigger data-testid="delivery-owner-select">
                  <SelectValue placeholder="Select delivery owner" />
                </SelectTrigger>
                <SelectContent>
                  {users.map(user => (
                    <SelectItem key={user.id} value={user.id}>
                      {user.first_name} {user.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium">Kickoff Date</label>
              <Input
                type="date"
                value={initiateForm.kickoff_date}
                onChange={(e) => setInitiateForm({ ...initiateForm, kickoff_date: e.target.value })}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium">Notes</label>
              <Textarea
                placeholder="Any notes for the delivery team..."
                value={initiateForm.notes}
                onChange={(e) => setInitiateForm({ ...initiateForm, notes: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowInitiateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleInitiateHandoff} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Initiate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Artifact Dialog */}
      <Dialog open={showArtifactDialog} onOpenChange={setShowArtifactDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Artifact</DialogTitle>
            <DialogDescription>
              {artifactForm.title || artifactForm.artifact_type?.replace('_', ' ')}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Title</label>
              <Input
                value={artifactForm.title}
                onChange={(e) => setArtifactForm({ ...artifactForm, title: e.target.value })}
              />
            </div>
            
            <div>
              <label className="text-sm font-medium">Content / Notes</label>
              <Textarea
                placeholder="Enter artifact content or notes..."
                value={artifactForm.content}
                onChange={(e) => setArtifactForm({ ...artifactForm, content: e.target.value })}
                rows={6}
              />
            </div>
            
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="artifact-complete"
                checked={artifactForm.completed}
                onChange={(e) => setArtifactForm({ ...artifactForm, completed: e.target.checked })}
                className="rounded"
              />
              <label htmlFor="artifact-complete" className="text-sm">
                Mark as complete
              </label>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowArtifactDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateArtifact} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete Handoff Dialog */}
      <Dialog open={showCompleteDialog} onOpenChange={setShowCompleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Complete Handoff</DialogTitle>
            <DialogDescription>
              Are you sure you want to complete the handoff for {selectedDeal?.name}?
            </DialogDescription>
          </DialogHeader>
          
          <Alert className="border-amber-200 bg-amber-50">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <AlertDescription className="text-amber-700">
              This action will lock the deal&apos;s sales stages. This cannot be undone.
            </AlertDescription>
          </Alert>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCompleteDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCompleteHandoff} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
              Complete Handoff
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default HandoffPage;
