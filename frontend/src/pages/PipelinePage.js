import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Skeleton } from '../components/ui/skeleton';
import { ScrollArea } from '../components/ui/scroll-area';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '../components/ui/sheet';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import {
  DollarSign, User, Clock, CheckCircle2, AlertTriangle, X,
  ChevronRight, ChevronLeft, GripVertical, MoreHorizontal, Plus, RefreshCw,
  Calculator, Phone, Mail, MessageSquare, Calendar, FileText, 
  TrendingUp, Package, Loader2, AlertCircle, ArrowRight, Target,
  Users, Building2, Filter, Zap, Star, ClipboardList, Sparkles
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import AIAssistantPanel from '../components/AIAssistantPanel';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Tier colors for lead scoring visualization
const tierColors = {
  A: 'bg-green-500',
  B: 'bg-blue-500',
  C: 'bg-yellow-500',
  D: 'bg-gray-400'
};

const PipelinePage = () => {
  const { api, currentWorkspace } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  
  // Pipeline state
  const [elev8Pipelines, setElev8Pipelines] = useState({ qualification: null, sales: null });
  const [activePipelineType, setActivePipelineType] = useState('sales');
  const [selectedPipeline, setSelectedPipeline] = useState(null);
  const [kanbanData, setKanbanData] = useState(null);
  
  // Deal state
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [showDealSheet, setShowDealSheet] = useState(false);
  const [movingDeal, setMovingDeal] = useState(null);
  const [draggedDeal, setDraggedDeal] = useState(null);
  const [dragOverColumn, setDragOverColumn] = useState(null);
  
  // SPICED editor state
  const [showSpicedDialog, setShowSpicedDialog] = useState(false);
  const [spicedData, setSpicedData] = useState({
    situation: '',
    pain: '',
    impact: '',
    critical_event: '',
    economic: '',
    decision: ''
  });
  const [savingSpiced, setSavingSpiced] = useState(false);
  
  // AI Assistant state
  const [showAIPanel, setShowAIPanel] = useState(false);
  
  // Stage transition state
  const [showTransitionDialog, setShowTransitionDialog] = useState(false);
  const [pendingTransition, setPendingTransition] = useState(null);
  const [transitionError, setTransitionError] = useState(null);
  const [overrideReason, setOverrideReason] = useState('');

  // Calculation state
  const [calculationData, setCalculationData] = useState(null);
  const [calcInputs, setCalcInputs] = useState({});
  const [calcSaving, setCalcSaving] = useState(false);

  // Legacy pipelines (for non-Elev8 workspaces)
  const [legacyPipelines, setLegacyPipelines] = useState([]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  useEffect(() => {
    initializePipelines();
  }, [currentWorkspace]);

  useEffect(() => {
    if (selectedPipeline) {
      fetchKanbanData(selectedPipeline);
    }
  }, [selectedPipeline]);

  const initializePipelines = async () => {
    setLoading(true);
    try {
      // Try to fetch Elev8 pipelines first
      const elev8Response = await fetch(`${API_URL}/api/elev8/pipelines/elev8`, {
        headers: getAuthHeaders()
      });
      
      if (elev8Response.ok) {
        const elev8Data = await elev8Response.json();
        setElev8Pipelines(elev8Data);
        
        // Default to sales pipeline if available
        if (elev8Data.sales) {
          setSelectedPipeline(elev8Data.sales.id);
          setActivePipelineType('sales');
        } else if (elev8Data.qualification) {
          setSelectedPipeline(elev8Data.qualification.id);
          setActivePipelineType('qualification');
        }
      }
      
      // Also fetch legacy pipelines as fallback
      const legacyResponse = await api.get('/pipelines');
      setLegacyPipelines(legacyResponse.data.pipelines || []);
      
      // If no Elev8 pipelines, use legacy
      if (!elev8Pipelines.sales && !elev8Pipelines.qualification) {
        if (legacyResponse.data.pipelines?.length > 0) {
          setSelectedPipeline(legacyResponse.data.pipelines[0].id);
        }
      }
    } catch (error) {
      console.error('Error initializing pipelines:', error);
      // Fallback to legacy only
      try {
        const legacyResponse = await api.get('/pipelines');
        setLegacyPipelines(legacyResponse.data.pipelines || []);
        if (legacyResponse.data.pipelines?.length > 0) {
          setSelectedPipeline(legacyResponse.data.pipelines[0].id);
        }
      } catch (err) {
        console.error('Error fetching legacy pipelines:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchKanbanData = async (pipelineId) => {
    if (!pipelineId) return;
    
    setLoading(true);
    try {
      const response = await api.get(`/pipelines/${pipelineId}/kanban`);
      setKanbanData(response.data);
    } catch (error) {
      console.error('Error fetching kanban data:', error);
      setKanbanData(null);
    } finally {
      setLoading(false);
    }
  };

  const switchPipelineType = (type) => {
    setActivePipelineType(type);
    const pipeline = type === 'sales' ? elev8Pipelines.sales : elev8Pipelines.qualification;
    if (pipeline) {
      setSelectedPipeline(pipeline.id);
    }
  };

  const fetchDealCalculation = async (dealId) => {
    try {
      const response = await api.get(`/calculations/deal/${dealId}`);
      setCalculationData(response.data);
      if (response.data.result) {
        setCalcInputs(response.data.result.inputs || {});
      }
    } catch (error) {
      console.error('Error fetching calculation:', error);
      setCalculationData(null);
    }
  };

  const handleDealClick = async (deal) => {
    setSelectedDeal(deal);
    setShowDealSheet(true);
    
    // Load SPICED data
    if (deal.spiced_situation || deal.spiced_pain) {
      setSpicedData({
        situation: deal.spiced_situation || '',
        pain: deal.spiced_pain || '',
        impact: deal.spiced_impact || '',
        critical_event: deal.spiced_critical_event || '',
        economic: deal.spiced_economic || '',
        decision: deal.spiced_decision || ''
      });
    }
    
    await fetchDealCalculation(deal.id);
  };

  const closeDealSheet = () => {
    setShowDealSheet(false);
    setSelectedDeal(null);
    setCalculationData(null);
    setCalcInputs({});
    setSpicedData({
      situation: '', pain: '', impact: '',
      critical_event: '', economic: '', decision: ''
    });
  };

  // Drag and Drop handlers
  const handleDragStart = (e, deal, columnId) => {
    setDraggedDeal({ ...deal, sourceColumnId: columnId });
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', deal.id);
  };

  const handleDragEnd = () => {
    setDraggedDeal(null);
    setDragOverColumn(null);
  };

  const handleDragOver = (e, columnId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverColumn(columnId);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = async (e, targetColumnId) => {
    e.preventDefault();
    setDragOverColumn(null);
    
    if (!draggedDeal || draggedDeal.sourceColumnId === targetColumnId) {
      setDraggedDeal(null);
      return;
    }

    await attemptStageMove(draggedDeal.id, targetColumnId, draggedDeal.sourceColumnId);
    setDraggedDeal(null);
  };

  const attemptStageMove = async (dealId, targetStageId, sourceStageId) => {
    setMovingDeal(dealId);
    setTransitionError(null);
    
    try {
      // Find target column to check requirements
      const targetColumn = kanbanData?.columns.find(c => c.id === targetStageId);
      
      // Check for SPICED requirement (Discovery stages)
      if (targetColumn?.requires_spiced) {
        const deal = kanbanData?.columns
          .flatMap(c => c.deals)
          .find(d => d.id === dealId);
        
        if (!deal?.spiced_summary && !deal?.spiced_situation) {
          setTransitionError({
            type: 'spiced_required',
            message: 'SPICED summary is required before moving to this stage'
          });
          setPendingTransition({ dealId, targetStageId, sourceStageId });
          setShowTransitionDialog(true);
          setMovingDeal(null);
          return;
        }
      }
      
      // Check for calculation requirement
      if (targetColumn?.requires_calculation) {
        const checkResponse = await api.get(`/calculations/deal/${dealId}/check`);
        const check = checkResponse.data;
        
        if (!check.is_complete) {
          setTransitionError({
            type: 'calculation_required',
            message: check.error_message || 'Calculation must be complete before this stage',
            missingFields: check.missing_fields || []
          });
          setPendingTransition({ dealId, targetStageId, sourceStageId });
          setShowTransitionDialog(true);
          setMovingDeal(null);
          return;
        }
      }
      
      // Proceed with move
      await api.post(`/deals/${dealId}/move-stage`, {
        stage_id: targetStageId
      });
      await fetchKanbanData(selectedPipeline);
      toast({ title: "Deal moved", description: `Moved to ${targetColumn?.name}` });
      
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      if (errorDetail) {
        setPendingTransition({ dealId, targetStageId, sourceStageId });
        setTransitionError({
          type: 'rule_violation',
          message: errorDetail
        });
        setShowTransitionDialog(true);
      }
      console.error('Error moving deal:', error);
    } finally {
      setMovingDeal(null);
    }
  };

  const handleMoveWithOverride = async () => {
    if (!pendingTransition || !overrideReason.trim()) return;
    
    setMovingDeal(pendingTransition.dealId);
    try {
      await api.post(`/deals/${pendingTransition.dealId}/move-stage`, {
        stage_id: pendingTransition.targetStageId,
        override: true,
        override_reason: overrideReason
      });
      await fetchKanbanData(selectedPipeline);
      setShowTransitionDialog(false);
      setPendingTransition(null);
      setOverrideReason('');
      setTransitionError(null);
      toast({ title: "Deal moved with override" });
    } catch (error) {
      console.error('Error with override:', error);
    } finally {
      setMovingDeal(null);
    }
  };

  // SPICED handlers
  const openSpicedEditor = () => {
    if (selectedDeal) {
      setSpicedData({
        situation: selectedDeal.spiced_situation || '',
        pain: selectedDeal.spiced_pain || '',
        impact: selectedDeal.spiced_impact || '',
        critical_event: selectedDeal.spiced_critical_event || '',
        economic: selectedDeal.spiced_economic || '',
        decision: selectedDeal.spiced_decision || ''
      });
      setShowSpicedDialog(true);
    }
  };

  const saveSpiced = async () => {
    if (!selectedDeal) return;
    
    setSavingSpiced(true);
    try {
      // Combine into summary
      const summary = `**Situation:** ${spicedData.situation}\n\n**Pain:** ${spicedData.pain}\n\n**Impact:** ${spicedData.impact}\n\n**Critical Event:** ${spicedData.critical_event}\n\n**Economic:** ${spicedData.economic}\n\n**Decision:** ${spicedData.decision}`;
      
      await api.put(`/deals/${selectedDeal.id}`, {
        spiced_summary: summary,
        spiced_situation: spicedData.situation,
        spiced_pain: spicedData.pain,
        spiced_impact: spicedData.impact,
        spiced_critical_event: spicedData.critical_event,
        spiced_economic: spicedData.economic,
        spiced_decision: spicedData.decision
      });
      
      toast({ title: "SPICED saved", description: "Discovery summary updated successfully" });
      setShowSpicedDialog(false);
      await fetchKanbanData(selectedPipeline);
    } catch (error) {
      console.error('Error saving SPICED:', error);
      toast({ title: "Error", description: "Failed to save SPICED summary", variant: "destructive" });
    } finally {
      setSavingSpiced(false);
    }
  };

  // Apply AI-drafted SPICED to form (pre-fill, user must still save)
  const applyAISpicedDraft = (draft) => {
    if (!draft) return;
    
    setSpicedData({
      situation: draft.situation || '',
      pain: draft.pain || '',
      impact: draft.impact || '',
      critical_event: draft.critical_event || '',
      economic: draft.economic || '',
      decision: draft.decision || ''
    });
    
    // Open the SPICED editor with the drafted content
    setShowSpicedDialog(true);
    setShowAIPanel(false);
    
    toast({
      title: "AI Draft Applied",
      description: "Review and save the SPICED summary to commit changes.",
    });
  };

  // Calculation handlers
  const handleCalcInputChange = (name, value) => {
    setCalcInputs(prev => ({ ...prev, [name]: value }));
  };

  const saveCalculation = async () => {
    if (!selectedDeal) return;
    
    setCalcSaving(true);
    try {
      const response = await api.put(`/calculations/deal/${selectedDeal.id}`, {
        inputs: calcInputs
      });
      
      setCalculationData(prev => ({
        ...prev,
        result: {
          ...response.data,
          inputs: response.data.inputs,
          outputs: response.data.outputs
        }
      }));
      
      if (response.data.stage_returned) {
        await fetchKanbanData(selectedPipeline);
      }
      toast({ title: "Calculation saved" });
    } catch (error) {
      console.error('Error saving calculation:', error);
    } finally {
      setCalcSaving(false);
    }
  };

  const formatCurrency = (value) => {
    if (value === undefined || value === null) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0
    }).format(value);
  };

  const hasElev8Pipelines = elev8Pipelines.qualification || elev8Pipelines.sales;

  if (loading && !kanbanData) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-[280px]" />
          <Skeleton className="h-10 w-24" />
        </div>
        <div className="flex gap-4 overflow-x-auto">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex-shrink-0 w-[300px]">
              <Skeleton className="h-16 w-full mb-2" />
              <Skeleton className="h-32 w-full mb-2" />
              <Skeleton className="h-32 w-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          {/* Elev8 Pipeline Switcher */}
          {hasElev8Pipelines && (
            <div className="flex items-center bg-muted rounded-lg p-1">
              {elev8Pipelines.qualification && (
                <Button
                  variant={activePipelineType === 'qualification' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => switchPipelineType('qualification')}
                  className="gap-2"
                >
                  <Users className="w-4 h-4" />
                  Qualification
                  {elev8Pipelines.qualification?.stages && (
                    <Badge variant="secondary" className="ml-1">
                      {elev8Pipelines.qualification.stages.length}
                    </Badge>
                  )}
                </Button>
              )}
              {elev8Pipelines.sales && (
                <Button
                  variant={activePipelineType === 'sales' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => switchPipelineType('sales')}
                  className="gap-2"
                >
                  <Target className="w-4 h-4" />
                  Sales Pipeline
                  {elev8Pipelines.sales?.stages && (
                    <Badge variant="secondary" className="ml-1">
                      {elev8Pipelines.sales.stages.length}
                    </Badge>
                  )}
                </Button>
              )}
            </div>
          )}
          
          {/* Legacy Pipeline Selector (if no Elev8 or additional pipelines) */}
          {(!hasElev8Pipelines || legacyPipelines.length > 2) && (
            <Select value={selectedPipeline} onValueChange={setSelectedPipeline}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select pipeline" />
              </SelectTrigger>
              <SelectContent>
                {legacyPipelines.map(p => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          <Button variant="outline" size="sm" onClick={() => fetchKanbanData(selectedPipeline)}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        {kanbanData && (
          <div className="flex items-center gap-4 text-sm">
            <Badge variant="outline" className="gap-1">
              <Package className="w-3 h-3" />
              {kanbanData.total_deals} deals
            </Badge>
            <Badge variant="outline" className="gap-1 font-semibold">
              <DollarSign className="w-3 h-3" />
              {formatCurrency(kanbanData.total_value)}
            </Badge>
          </div>
        )}
      </div>

      {/* Pipeline Type Description */}
      {hasElev8Pipelines && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {activePipelineType === 'qualification' ? (
            <>
              <Users className="w-4 h-4" />
              <span>Qualification Pipeline: Activate, contact, and qualify leads before pushing to Sales Pipeline</span>
            </>
          ) : (
            <>
              <Target className="w-4 h-4" />
              <span>Sales Pipeline: Convert qualified leads into revenue through discovery, demo, and closing</span>
            </>
          )}
        </div>
      )}

      {/* Kanban Board */}
      <ScrollArea className="w-full">
        <div className="flex gap-4 pb-4 min-w-max">
          {kanbanData?.columns?.map((column, index) => (
            <div
              key={column.id}
              className={`flex-shrink-0 w-[300px] rounded-lg transition-all ${
                dragOverColumn === column.id ? 'ring-2 ring-primary' : ''
              }`}
              onDragOver={(e) => handleDragOver(e, column.id)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, column.id)}
            >
              {/* Column Header */}
              <div 
                className="p-3 rounded-t-lg mb-2"
                style={{ backgroundColor: column.color + '20', borderLeft: `4px solid ${column.color}` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{column.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {column.deals?.length || 0}
                    </Badge>
                  </div>
                  {column.probability !== undefined && (
                    <Badge variant="outline" className="text-xs">
                      {column.probability}%
                    </Badge>
                  )}
                </div>
                {column.deals?.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {formatCurrency(column.deals.reduce((sum, d) => sum + (d.amount || 0), 0))}
                  </p>
                )}
              </div>

              {/* Column Content */}
              <div className="space-y-2 min-h-[200px] p-1">
                {column.deals?.map(deal => (
                  <Card
                    key={deal.id}
                    className={`cursor-pointer transition-all hover:shadow-md ${
                      draggedDeal?.id === deal.id ? 'opacity-50' : ''
                    } ${movingDeal === deal.id ? 'animate-pulse' : ''}`}
                    draggable
                    onDragStart={(e) => handleDragStart(e, deal, column.id)}
                    onDragEnd={handleDragEnd}
                    onClick={() => handleDealClick(deal)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{deal.name}</p>
                          <p className="text-xs text-muted-foreground truncate">
                            {deal.contact_name || 'No contact'}
                          </p>
                        </div>
                        {deal.tier && (
                          <Badge className={`${tierColors[deal.tier]} text-white text-xs`}>
                            {deal.tier}
                          </Badge>
                        )}
                      </div>
                      
                      <div className="flex items-center justify-between mt-2">
                        <span className="text-sm font-semibold">
                          {formatCurrency(deal.amount)}
                        </span>
                        {deal.sales_motion_type === 'partner_sales' && (
                          <Badge variant="outline" className="text-xs">
                            <Building2 className="w-3 h-3 mr-1" />
                            Partner
                          </Badge>
                        )}
                      </div>
                      
                      {/* Lead Score Progress */}
                      {deal.lead_score !== undefined && (
                        <div className="mt-2">
                          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                            <span>Score</span>
                            <span>{deal.lead_score}/100</span>
                          </div>
                          <Progress value={deal.lead_score} className="h-1" />
                        </div>
                      )}
                      
                      {/* SPICED indicator */}
                      {(deal.spiced_summary || deal.spiced_situation) && (
                        <Badge variant="secondary" className="mt-2 text-xs">
                          <ClipboardList className="w-3 h-3 mr-1" />
                          SPICED
                        </Badge>
                      )}
                    </CardContent>
                  </Card>
                ))}
                
                {(!column.deals || column.deals.length === 0) && (
                  <div className="flex items-center justify-center h-24 text-xs text-muted-foreground border-2 border-dashed rounded-lg">
                    Drop deals here
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Deal Detail Sheet */}
      <Sheet open={showDealSheet} onOpenChange={setShowDealSheet}>
        <SheetContent className="w-[500px] sm:w-[600px] overflow-y-auto">
          {selectedDeal && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {selectedDeal.name}
                  {selectedDeal.tier && (
                    <Badge className={`${tierColors[selectedDeal.tier]} text-white`}>
                      Tier {selectedDeal.tier}
                    </Badge>
                  )}
                </SheetTitle>
                <SheetDescription>
                  {selectedDeal.contact_name} • {selectedDeal.company || 'No company'}
                </SheetDescription>
              </SheetHeader>
              
              {/* AI Assistant Button */}
              <div className="mt-4">
                <Button 
                  variant="outline" 
                  className="w-full bg-purple-50 hover:bg-purple-100 border-purple-200"
                  onClick={() => setShowAIPanel(true)}
                >
                  <Sparkles className="w-4 h-4 mr-2 text-purple-500" />
                  AI Assistant - Draft SPICED
                  <Badge variant="secondary" className="ml-2 text-xs">Advisory</Badge>
                </Button>
              </div>
              
              <div className="mt-6 space-y-6">
                {/* Deal Summary */}
                <Card>
                  <CardContent className="pt-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-muted-foreground">Amount</p>
                        <p className="text-xl font-bold">{formatCurrency(selectedDeal.amount)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Probability</p>
                        <p className="text-xl font-bold">{Math.round((selectedDeal.forecast_probability || 0) * 100)}%</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Weighted Value</p>
                        <p className="text-lg font-semibold">
                          {formatCurrency((selectedDeal.amount || 0) * (selectedDeal.forecast_probability || 0))}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Lead Score</p>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-semibold">{selectedDeal.lead_score || 0}</span>
                          <Progress value={selectedDeal.lead_score || 0} className="flex-1 h-2" />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                {/* Sales Motion Info */}
                {selectedDeal.sales_motion_type && (
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      {selectedDeal.sales_motion_type === 'partner_sales' ? (
                        <Building2 className="w-4 h-4" />
                      ) : (
                        <Target className="w-4 h-4" />
                      )}
                      <span className="font-medium">
                        {selectedDeal.sales_motion_type === 'partner_sales' ? 'Partner Sales' : 'Partnership Sales'}
                      </span>
                    </div>
                    {selectedDeal.partner_name && (
                      <p className="text-sm">Partner: <span className="font-medium">{selectedDeal.partner_name}</span></p>
                    )}
                    {selectedDeal.product_name && (
                      <p className="text-sm">Product: <span className="font-medium">{selectedDeal.product_name}</span></p>
                    )}
                  </div>
                )}
                
                {/* SPICED Summary */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium flex items-center gap-2">
                      <ClipboardList className="w-4 h-4" />
                      SPICED Summary
                    </h3>
                    <Button size="sm" variant="outline" onClick={openSpicedEditor}>
                      {selectedDeal.spiced_situation ? 'Edit' : 'Add'} SPICED
                    </Button>
                  </div>
                  
                  {selectedDeal.spiced_situation ? (
                    <Card>
                      <CardContent className="pt-4 space-y-3 text-sm">
                        {selectedDeal.spiced_situation && (
                          <div>
                            <p className="font-medium text-muted-foreground">Situation</p>
                            <p>{selectedDeal.spiced_situation}</p>
                          </div>
                        )}
                        {selectedDeal.spiced_pain && (
                          <div>
                            <p className="font-medium text-muted-foreground">Pain</p>
                            <p>{selectedDeal.spiced_pain}</p>
                          </div>
                        )}
                        {selectedDeal.spiced_impact && (
                          <div>
                            <p className="font-medium text-muted-foreground">Impact</p>
                            <p>{selectedDeal.spiced_impact}</p>
                          </div>
                        )}
                        {selectedDeal.spiced_critical_event && (
                          <div>
                            <p className="font-medium text-muted-foreground">Critical Event</p>
                            <p>{selectedDeal.spiced_critical_event}</p>
                          </div>
                        )}
                        {selectedDeal.spiced_economic && (
                          <div>
                            <p className="font-medium text-muted-foreground">Economic</p>
                            <p>{selectedDeal.spiced_economic}</p>
                          </div>
                        )}
                        {selectedDeal.spiced_decision && (
                          <div>
                            <p className="font-medium text-muted-foreground">Decision</p>
                            <p>{selectedDeal.spiced_decision}</p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <Card>
                      <CardContent className="py-8 text-center text-muted-foreground">
                        <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No SPICED summary yet</p>
                        <p className="text-xs">Required for Discovery stage progression</p>
                      </CardContent>
                    </Card>
                  )}
                </div>
                
                {/* Scoring Details */}
                {selectedDeal.economic_units !== undefined && (
                  <div>
                    <h3 className="font-medium mb-2">Scoring Inputs</h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="p-2 bg-muted rounded">
                        <p className="text-muted-foreground">Economic Units</p>
                        <p className="font-medium">{selectedDeal.economic_units || '-'}</p>
                      </div>
                      <div className="p-2 bg-muted rounded">
                        <p className="text-muted-foreground">Usage Volume</p>
                        <p className="font-medium">{selectedDeal.usage_volume || '-'}</p>
                      </div>
                      <div className="p-2 bg-muted rounded">
                        <p className="text-muted-foreground">Urgency</p>
                        <p className="font-medium">{selectedDeal.urgency || '-'}/5</p>
                      </div>
                      <div className="p-2 bg-muted rounded">
                        <p className="text-muted-foreground">Decision Role</p>
                        <p className="font-medium">{selectedDeal.decision_role?.replace('_', ' ') || '-'}</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Close button */}
                <Button variant="outline" onClick={closeDealSheet} className="w-full">
                  Close
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* SPICED Editor Dialog */}
      <Dialog open={showSpicedDialog} onOpenChange={setShowSpicedDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>SPICED Discovery Summary</DialogTitle>
            <DialogDescription>
              Capture key discovery information. Required for progression past Discovery stage.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>
                <span className="font-semibold text-blue-600">S</span>ituation
              </Label>
              <Textarea
                value={spicedData.situation}
                onChange={(e) => setSpicedData({...spicedData, situation: e.target.value})}
                placeholder="Company background, current state, context..."
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>
                <span className="font-semibold text-red-600">P</span>ain
              </Label>
              <Textarea
                value={spicedData.pain}
                onChange={(e) => setSpicedData({...spicedData, pain: e.target.value})}
                placeholder="Specific business pain point(s) identified..."
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>
                <span className="font-semibold text-green-600">I</span>mpact
              </Label>
              <Textarea
                value={spicedData.impact}
                onChange={(e) => setSpicedData({...spicedData, impact: e.target.value})}
                placeholder="Quantified impact in $ or operational terms..."
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>
                <span className="font-semibold text-orange-600">C</span>ritical Event
              </Label>
              <Textarea
                value={spicedData.critical_event}
                onChange={(e) => setSpicedData({...spicedData, critical_event: e.target.value})}
                placeholder="Timeline trigger - what makes this urgent?"
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>
                <span className="font-semibold text-purple-600">E</span>conomic
              </Label>
              <Textarea
                value={spicedData.economic}
                onChange={(e) => setSpicedData({...spicedData, economic: e.target.value})}
                placeholder="Budget, decision-maker, approval authority, procurement process..."
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>
                <span className="font-semibold text-teal-600">D</span>ecision
              </Label>
              <Textarea
                value={spicedData.decision}
                onChange={(e) => setSpicedData({...spicedData, decision: e.target.value})}
                placeholder="How do they buy? Decision criteria? Timeline to close?"
                rows={2}
              />
            </div>
          </div>
          
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setShowSpicedDialog(false)}>
              Cancel
            </Button>
            <Button onClick={saveSpiced} disabled={savingSpiced}>
              {savingSpiced && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Save SPICED
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Stage Transition Dialog */}
      <AlertDialog open={showTransitionDialog} onOpenChange={setShowTransitionDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Stage Transition Blocked
            </AlertDialogTitle>
            <AlertDialogDescription>
              {transitionError?.message}
              
              {transitionError?.type === 'spiced_required' && (
                <div className="mt-3 p-3 bg-muted rounded-lg text-sm">
                  <p className="font-medium">Required: SPICED Summary</p>
                  <p className="text-muted-foreground">
                    Open the deal details and add SPICED information before progressing.
                  </p>
                </div>
              )}
              
              {transitionError?.missingFields?.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-medium">Missing fields:</p>
                  <ul className="list-disc list-inside text-sm">
                    {transitionError.missingFields.map((field, i) => (
                      <li key={i}>{field}</li>
                    ))}
                  </ul>
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          <div className="mt-4">
            <Label>Override Reason (optional)</Label>
            <Textarea
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Explain why you're overriding this requirement..."
              rows={2}
            />
          </div>
          
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setShowTransitionDialog(false);
              setPendingTransition(null);
              setOverrideReason('');
              setTransitionError(null);
            }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleMoveWithOverride}
              disabled={!overrideReason.trim() || movingDeal}
              className="bg-amber-600 hover:bg-amber-700"
            >
              {movingDeal && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              Override & Move
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default PipelinePage;
