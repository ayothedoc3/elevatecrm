import React, { useState, useEffect, useCallback } from 'react';
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
  TrendingUp, Package, Loader2, AlertCircle, ArrowRight
} from 'lucide-react';

const PipelinePage = () => {
  const { api, currentWorkspace } = useAuth();
  const [loading, setLoading] = useState(true);
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState(null);
  const [kanbanData, setKanbanData] = useState(null);
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [showDealSheet, setShowDealSheet] = useState(false);
  const [movingDeal, setMovingDeal] = useState(null);
  const [draggedDeal, setDraggedDeal] = useState(null);
  const [dragOverColumn, setDragOverColumn] = useState(null);
  
  // Stage transition state
  const [showTransitionDialog, setShowTransitionDialog] = useState(false);
  const [pendingTransition, setPendingTransition] = useState(null);
  const [transitionError, setTransitionError] = useState(null);
  const [overrideReason, setOverrideReason] = useState('');

  // Calculation state
  const [calculationData, setCalculationData] = useState(null);
  const [calcInputs, setCalcInputs] = useState({});
  const [calcSaving, setCalcSaving] = useState(false);

  useEffect(() => {
    fetchPipelines();
  }, [currentWorkspace]);

  useEffect(() => {
    if (selectedPipeline) {
      fetchKanbanData(selectedPipeline);
    }
  }, [selectedPipeline]);

  const fetchPipelines = async () => {
    try {
      const response = await api.get('/pipelines');
      setPipelines(response.data.pipelines);
      if (response.data.pipelines.length > 0) {
        setSelectedPipeline(response.data.pipelines[0].id);
      }
    } catch (error) {
      console.error('Error fetching pipelines:', error);
    }
  };

  const fetchKanbanData = async (pipelineId) => {
    setLoading(true);
    try {
      const response = await api.get(`/pipelines/${pipelineId}/kanban`);
      setKanbanData(response.data);
    } catch (error) {
      console.error('Error fetching kanban data:', error);
    } finally {
      setLoading(false);
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
    await fetchDealCalculation(deal.id);
  };

  const closeDealSheet = () => {
    setShowDealSheet(false);
    setSelectedDeal(null);
    setCalculationData(null);
    setCalcInputs({});
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

    // Check if we need to validate the transition
    await attemptStageMove(draggedDeal.id, targetColumnId, draggedDeal.sourceColumnId);
    setDraggedDeal(null);
  };

  const attemptStageMove = async (dealId, targetStageId, sourceStageId) => {
    setMovingDeal(dealId);
    setTransitionError(null);
    
    try {
      // First check if calculation is required
      const checkResponse = await api.get(`/calculations/deal/${dealId}/check`);
      const check = checkResponse.data;
      
      // Find target column to check if it requires calculation
      const targetColumn = kanbanData?.columns.find(c => c.id === targetStageId);
      const requiresCalc = targetColumn?.name?.toLowerCase().includes('demo') || 
                          targetColumn?.name?.toLowerCase().includes('scheduled');
      
      if (requiresCalc && !check.is_complete) {
        // Show transition dialog with error
        setPendingTransition({ dealId, targetStageId, sourceStageId });
        setTransitionError({
          type: 'calculation_required',
          message: check.error_message || 'Calculation must be complete before this stage',
          missingFields: check.missing_fields || []
        });
        setShowTransitionDialog(true);
        setMovingDeal(null);
        return;
      }
      
      // Proceed with move
      await api.post(`/deals/${dealId}/move-stage`, {
        stage_id: targetStageId
      });
      await fetchKanbanData(selectedPipeline);
      
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
    } catch (error) {
      console.error('Error with override:', error);
    } finally {
      setMovingDeal(null);
    }
  };

  // Calculation handlers
  const handleCalcInputChange = (name, value) => {
    setCalcInputs(prev => ({ ...prev, [name]: value }));
  };

  const handleMultiSelectChange = (name, value) => {
    const current = calcInputs[name] || [];
    if (current.includes(value)) {
      setCalcInputs(prev => ({ ...prev, [name]: current.filter(v => v !== value) }));
    } else {
      setCalcInputs(prev => ({ ...prev, [name]: [...current, value] }));
    }
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
      
      // Refresh kanban if stage changed
      if (response.data.stage_returned) {
        await fetchKanbanData(selectedPipeline);
      }
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

  const getComplianceBadge = (status) => {
    switch (status) {
      case 'compliant':
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/30"><CheckCircle2 className="w-3 h-3 mr-1" />Compliant</Badge>;
      case 'overridden':
        return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30"><AlertTriangle className="w-3 h-3 mr-1" />Override</Badge>;
      case 'missing_requirements':
        return <Badge className="bg-red-500/20 text-red-400 border-red-500/30"><AlertTriangle className="w-3 h-3 mr-1" />Missing</Badge>;
      default:
        return null;
    }
  };

  if (loading && !kanbanData) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-[280px]" />
          <Skeleton className="h-10 w-24" />
        </div>
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex-1 min-w-[280px]">
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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Select value={selectedPipeline} onValueChange={setSelectedPipeline}>
            <SelectTrigger className="w-[280px]">
              <SelectValue placeholder="Select pipeline" />
            </SelectTrigger>
            <SelectContent>
              {pipelines.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Button variant="outline" size="sm" onClick={() => fetchKanbanData(selectedPipeline)}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        {kanbanData && (
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{kanbanData.total_deals} deals</span>
            <span className="font-semibold text-foreground">
              {formatCurrency(kanbanData.total_value)} total value
            </span>
          </div>
        )}
      </div>

      {/* Kanban Board */}
      <ScrollArea className="h-[calc(100vh-220px)]">
        <div className="flex gap-4 pb-4" style={{ minWidth: 'max-content' }}>
          {kanbanData?.columns.map((column, colIndex) => (
            <div 
              key={column.id} 
              className={`flex-shrink-0 w-[320px] ${
                dragOverColumn === column.id ? 'ring-2 ring-primary ring-offset-2' : ''
              }`}
              onDragOver={(e) => handleDragOver(e, column.id)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, column.id)}
            >
              {/* Column Header */}
              <div 
                className="p-3 rounded-t-lg border border-b-0" 
                style={{ 
                  backgroundColor: `${column.color}15`,
                  borderColor: `${column.color}40`
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: column.color }}
                    />
                    <span className="font-medium text-sm">{column.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {column.deal_count}
                    </Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {column.probability}%
                  </span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {formatCurrency(column.total_value)}
                </div>
              </div>

              {/* Column Content */}
              <div 
                className={`p-2 space-y-2 min-h-[400px] rounded-b-lg border border-t-0 transition-colors ${
                  dragOverColumn === column.id ? 'bg-primary/10' : 'bg-muted/30'
                }`}
                style={{ borderColor: `${column.color}40` }}
              >
                {column.deals.map(deal => (
                  <Card 
                    key={deal.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, deal, column.id)}
                    onDragEnd={handleDragEnd}
                    className={`cursor-grab active:cursor-grabbing hover:shadow-md transition-all border-l-4 ${
                      movingDeal === deal.id ? 'opacity-50' : ''
                    } ${draggedDeal?.id === deal.id ? 'opacity-50 rotate-2' : ''}`}
                    style={{ borderLeftColor: column.color }}
                    onClick={() => handleDealClick(deal)}
                  >
                    <CardContent className="p-3 space-y-2">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <GripVertical className="w-4 h-4 text-muted-foreground" />
                          <p className="font-medium text-sm leading-tight">{deal.name}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-lg font-bold text-primary">
                          {formatCurrency(deal.amount)}
                        </span>
                        {getComplianceBadge(deal.blueprint_compliance)}
                      </div>
                      
                      {deal.contact_name && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <User className="w-3 h-3" />
                          <span>{deal.contact_name}</span>
                        </div>
                      )}
                      
                      {/* Quick Move Buttons */}
                      <div className="flex gap-1 pt-2 border-t" onClick={e => e.stopPropagation()}>
                        {colIndex > 0 && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="flex-1 h-7 text-xs"
                            onClick={() => attemptStageMove(deal.id, kanbanData.columns[colIndex - 1].id, column.id)}
                            disabled={movingDeal === deal.id}
                          >
                            <ChevronLeft className="w-3 h-3 mr-1" />
                            Back
                          </Button>
                        )}
                        {colIndex < kanbanData.columns.length - 1 && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="flex-1 h-7 text-xs"
                            onClick={() => attemptStageMove(deal.id, kanbanData.columns[colIndex + 1].id, column.id)}
                            disabled={movingDeal === deal.id}
                          >
                            Next
                            <ChevronRight className="w-3 h-3 ml-1" />
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
                
                {column.deals.length === 0 && (
                  <div className="h-32 flex items-center justify-center text-muted-foreground text-sm">
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
        <SheetContent className="w-full sm:max-w-2xl p-0 flex flex-col">
          {selectedDeal && (
            <>
              <SheetHeader className="p-6 border-b">
                <div className="flex items-start justify-between">
                  <div>
                    <SheetTitle className="text-xl">{selectedDeal.name}</SheetTitle>
                    <SheetDescription className="flex items-center gap-2 mt-1">
                      <User className="w-4 h-4" />
                      {selectedDeal.contact_name || 'No contact'}
                    </SheetDescription>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-primary">{formatCurrency(selectedDeal.amount)}</p>
                    {getComplianceBadge(selectedDeal.blueprint_compliance)}
                  </div>
                </div>
              </SheetHeader>

              <Tabs defaultValue="details" className="flex-1 flex flex-col">
                <TabsList className="mx-6 mt-4">
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="calculation">
                    <Calculator className="w-4 h-4 mr-1" />
                    Calculator
                  </TabsTrigger>
                  <TabsTrigger value="activity">Activity</TabsTrigger>
                </TabsList>

                <ScrollArea className="flex-1">
                  <TabsContent value="details" className="p-6 space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Deal Information</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-xs text-muted-foreground">Stage</Label>
                            <p className="font-medium">{selectedDeal.stage_name || 'Unknown'}</p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Value</Label>
                            <p className="font-medium">{formatCurrency(selectedDeal.amount)}</p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Contact</Label>
                            <p className="font-medium">{selectedDeal.contact_name || '-'}</p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Status</Label>
                            <p className="font-medium capitalize">{selectedDeal.status}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Quick Actions */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Quick Actions</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-4 gap-2">
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <Phone className="w-4 h-4" />
                            <span className="text-xs">Call</span>
                          </Button>
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <Mail className="w-4 h-4" />
                            <span className="text-xs">Email</span>
                          </Button>
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <MessageSquare className="w-4 h-4" />
                            <span className="text-xs">SMS</span>
                          </Button>
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <Calendar className="w-4 h-4" />
                            <span className="text-xs">Schedule</span>
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="calculation" className="p-6 space-y-4">
                    {calculationData?.definition ? (
                      <>
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-base flex items-center gap-2">
                              <Calculator className="w-4 h-4" />
                              {calculationData.definition.name}
                            </CardTitle>
                            <CardDescription>
                              {calculationData.definition.description}
                            </CardDescription>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            {calculationData.definition.inputs?.map(field => (
                              <div key={field.name} className="space-y-2">
                                <Label className="flex items-center gap-1">
                                  {field.label}
                                  {field.required && <span className="text-red-500">*</span>}
                                </Label>
                                
                                {field.type === 'integer' || field.type === 'number' ? (
                                  <Input
                                    type="number"
                                    value={calcInputs[field.name] || ''}
                                    onChange={(e) => handleCalcInputChange(field.name, parseInt(e.target.value) || '')}
                                    placeholder={field.placeholder}
                                    min={field.min}
                                    max={field.max}
                                  />
                                ) : field.type === 'currency' ? (
                                  <div className="relative">
                                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                    <Input
                                      type="number"
                                      value={calcInputs[field.name] || ''}
                                      onChange={(e) => handleCalcInputChange(field.name, parseFloat(e.target.value) || '')}
                                      placeholder={field.placeholder}
                                      className="pl-9"
                                      step="0.01"
                                    />
                                  </div>
                                ) : field.type === 'select' ? (
                                  <Select 
                                    value={calcInputs[field.name] || ''} 
                                    onValueChange={(v) => handleCalcInputChange(field.name, v)}
                                  >
                                    <SelectTrigger>
                                      <SelectValue placeholder={field.placeholder || 'Select...'} />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {field.options?.map(opt => (
                                        <SelectItem key={opt.value} value={opt.value}>
                                          {opt.label}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                ) : field.type === 'multi_select' ? (
                                  <div className="flex flex-wrap gap-2">
                                    {field.options?.map(opt => (
                                      <Button
                                        key={opt.value}
                                        type="button"
                                        variant={(calcInputs[field.name] || []).includes(opt.value) ? 'default' : 'outline'}
                                        size="sm"
                                        onClick={() => handleMultiSelectChange(field.name, opt.value)}
                                      >
                                        {opt.label}
                                        {(calcInputs[field.name] || []).includes(opt.value) && (
                                          <CheckCircle2 className="w-3 h-3 ml-1" />
                                        )}
                                      </Button>
                                    ))}
                                  </div>
                                ) : (
                                  <Input
                                    value={calcInputs[field.name] || ''}
                                    onChange={(e) => handleCalcInputChange(field.name, e.target.value)}
                                    placeholder={field.placeholder}
                                  />
                                )}
                                
                                {field.help_text && (
                                  <p className="text-xs text-muted-foreground">{field.help_text}</p>
                                )}
                              </div>
                            ))}
                            
                            <Button 
                              onClick={saveCalculation} 
                              disabled={calcSaving}
                              className="w-full"
                            >
                              {calcSaving ? (
                                <>
                                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                  Calculating...
                                </>
                              ) : (
                                <>
                                  <Calculator className="w-4 h-4 mr-2" />
                                  Calculate & Save
                                </>
                              )}
                            </Button>
                          </CardContent>
                        </Card>

                        {/* Calculation Results */}
                        {calculationData.result?.outputs && Object.keys(calculationData.result.outputs).length > 0 && (
                          <Card className="bg-green-500/5 border-green-500/20">
                            <CardHeader>
                              <CardTitle className="text-base flex items-center gap-2 text-green-600">
                                <TrendingUp className="w-4 h-4" />
                                Calculated Results
                                {calculationData.result.is_complete && (
                                  <Badge className="bg-green-500/20 text-green-400">Complete</Badge>
                                )}
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="grid grid-cols-2 gap-4">
                                <div className="p-3 bg-background rounded-lg">
                                  <p className="text-xs text-muted-foreground">Monthly Oil Spend</p>
                                  <p className="text-xl font-bold">
                                    {formatCurrency(calculationData.result.outputs.monthly_oil_spend)}
                                  </p>
                                </div>
                                <div className="p-3 bg-background rounded-lg">
                                  <p className="text-xs text-muted-foreground">Yearly Oil Spend</p>
                                  <p className="text-xl font-bold">
                                    {formatCurrency(calculationData.result.outputs.yearly_oil_spend)}
                                  </p>
                                </div>
                                <div className="col-span-2 p-3 bg-green-500/10 rounded-lg">
                                  <p className="text-xs text-green-600">Estimated Annual Savings</p>
                                  <p className="text-2xl font-bold text-green-600">
                                    {formatCurrency(calculationData.result.outputs.estimated_savings_low)} - {formatCurrency(calculationData.result.outputs.estimated_savings_high)}
                                  </p>
                                </div>
                                <div className="p-3 bg-background rounded-lg">
                                  <p className="text-xs text-muted-foreground">Devices Needed</p>
                                  <p className="text-xl font-bold flex items-center gap-1">
                                    <Package className="w-4 h-4" />
                                    {calculationData.result.outputs.recommended_device_quantity}
                                  </p>
                                </div>
                                <div className="p-3 bg-background rounded-lg">
                                  <p className="text-xs text-muted-foreground">Device Size</p>
                                  <p className="text-xl font-bold">
                                    {calculationData.result.outputs.recommended_device_size}
                                  </p>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <Calculator className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>No calculation defined for this workspace</p>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="activity" className="p-6 space-y-4">
                    <ActivityPanel 
                      dealId={selectedDeal.id} 
                      api={api} 
                      onUpdate={() => fetchKanbanData(selectedPipeline)}
                    />
                  </TabsContent>
                </ScrollArea>
              </Tabs>

              <div className="p-4 border-t">
                <Button variant="outline" className="w-full" onClick={closeDealSheet}>
                  Close
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Stage Transition Dialog */}
      <AlertDialog open={showTransitionDialog} onOpenChange={setShowTransitionDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-amber-500" />
              Stage Move Blocked
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4">
                <p>{transitionError?.message}</p>
                
                {transitionError?.missingFields?.length > 0 && (
                  <div className="p-3 bg-amber-500/10 rounded-lg">
                    <p className="text-sm font-medium text-amber-600 mb-2">Missing information:</p>
                    <ul className="text-sm space-y-1">
                      {transitionError.missingFields.map((field, i) => (
                        <li key={i} className="flex items-center gap-2">
                          <X className="w-3 h-3 text-red-500" />
                          {field}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {transitionError?.type === 'calculation_required' && (
                  <p className="text-sm">
                    Open the deal and complete the ROI Calculator before moving to this stage.
                  </p>
                )}
                
                <div className="pt-2 border-t">
                  <Label>Admin Override (requires reason)</Label>
                  <Textarea
                    placeholder="Enter reason for override..."
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    className="mt-2"
                    rows={2}
                  />
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setShowTransitionDialog(false);
              setPendingTransition(null);
              setOverrideReason('');
            }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleMoveWithOverride}
              disabled={!overrideReason.trim() || movingDeal}
              className="bg-amber-500 hover:bg-amber-600"
            >
              {movingDeal ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <AlertTriangle className="w-4 h-4 mr-2" />
              )}
              Override & Move
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

// Activity Panel Component
const ActivityPanel = ({ dealId, api, onUpdate }) => {
  const [activities, setActivities] = React.useState([]);
  const [summary, setSummary] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [showLogModal, setShowLogModal] = React.useState(false);
  const [logging, setLogging] = React.useState(false);
  const [newActivity, setNewActivity] = React.useState({
    activity_type: 'call',
    direction: 'outbound',
    status: 'completed',
    subject: '',
    notes: '',
    got_response: false
  });

  React.useEffect(() => {
    if (dealId) {
      fetchActivities();
      fetchSummary();
    }
  }, [dealId]);

  const fetchActivities = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/outreach/deal/${dealId}`);
      setActivities(response.data.activities || []);
    } catch (error) {
      console.error('Error fetching activities:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await api.get(`/outreach/deal/${dealId}/summary`);
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching summary:', error);
    }
  };

  const handleLogActivity = async () => {
    setLogging(true);
    try {
      await api.post('/outreach', {
        deal_id: dealId,
        ...newActivity
      });
      setShowLogModal(false);
      setNewActivity({
        activity_type: 'call',
        direction: 'outbound',
        status: 'completed',
        subject: '',
        notes: '',
        got_response: false
      });
      await fetchActivities();
      await fetchSummary();
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error logging activity:', error);
    } finally {
      setLogging(false);
    }
  };

  const getActivityIcon = (type) => {
    const icons = {
      call: <Phone className="w-4 h-4 text-blue-500" />,
      email: <Mail className="w-4 h-4 text-green-500" />,
      sms: <MessageSquare className="w-4 h-4 text-purple-500" />,
      meeting: <Calendar className="w-4 h-4 text-orange-500" />,
      demo: <TrendingUp className="w-4 h-4 text-cyan-500" />,
      note: <FileText className="w-4 h-4 text-gray-500" />
    };
    return icons[type] || <Clock className="w-4 h-4 text-gray-500" />;
  };

  const getActivityBgColor = (type) => {
    const colors = {
      call: 'bg-blue-500/20',
      email: 'bg-green-500/20',
      sms: 'bg-purple-500/20',
      meeting: 'bg-orange-500/20',
      demo: 'bg-cyan-500/20',
      note: 'bg-gray-500/20'
    };
    return colors[type] || 'bg-gray-500/20';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <>
      {/* Summary Card */}
      {summary && (
        <Card className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-blue-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Touchpoints</p>
                <p className="text-2xl font-bold">{summary.total_touchpoints}</p>
              </div>
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <p className="text-lg font-semibold">{summary.calls}</p>
                  <p className="text-xs text-muted-foreground">Calls</p>
                </div>
                <div>
                  <p className="text-lg font-semibold">{summary.emails}</p>
                  <p className="text-xs text-muted-foreground">Emails</p>
                </div>
                <div>
                  <p className="text-lg font-semibold">{summary.sms}</p>
                  <p className="text-xs text-muted-foreground">SMS</p>
                </div>
                <div>
                  <p className="text-lg font-semibold text-green-500">{summary.responses}</p>
                  <p className="text-xs text-muted-foreground">Replies</p>
                </div>
              </div>
            </div>
            {summary.days_since_last_contact !== null && (
              <p className="text-xs text-muted-foreground mt-2">
                Last contact: {summary.days_since_last_contact === 0 ? 'Today' : `${summary.days_since_last_contact} days ago`}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Activity List */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Activity Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map(i => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : activities.length > 0 ? (
            <div className="space-y-2">
              {activities.map(activity => (
                <div key={activity.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full ${getActivityBgColor(activity.activity_type)} flex items-center justify-center`}>
                      {getActivityIcon(activity.activity_type)}
                    </div>
                    <div>
                      <p className="font-medium text-sm capitalize">
                        {activity.activity_type} {activity.got_response && <Badge variant="outline" className="ml-1 text-xs">Got Reply</Badge>}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {activity.direction} • {activity.status}
                        {activity.subject && ` • ${activity.subject}`}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">{formatDate(activity.created_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 text-muted-foreground">
              <Phone className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No activities logged yet</p>
            </div>
          )}
          
          <Button variant="outline" className="w-full mt-4" onClick={() => setShowLogModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Log Activity
          </Button>
        </CardContent>
      </Card>

      {/* Log Activity Dialog */}
      <AlertDialog open={showLogModal} onOpenChange={setShowLogModal}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Log Outreach Activity</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Type</Label>
                    <Select 
                      value={newActivity.activity_type} 
                      onValueChange={(v) => setNewActivity({...newActivity, activity_type: v})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="call">📞 Call</SelectItem>
                        <SelectItem value="email">📧 Email</SelectItem>
                        <SelectItem value="sms">💬 SMS</SelectItem>
                        <SelectItem value="meeting">🤝 Meeting</SelectItem>
                        <SelectItem value="demo">📺 Demo</SelectItem>
                        <SelectItem value="note">📝 Note</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Direction</Label>
                    <Select 
                      value={newActivity.direction} 
                      onValueChange={(v) => setNewActivity({...newActivity, direction: v})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="outbound">Outbound</SelectItem>
                        <SelectItem value="inbound">Inbound</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Result</Label>
                  <Select 
                    value={newActivity.status} 
                    onValueChange={(v) => setNewActivity({...newActivity, status: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="no_answer">No Answer</SelectItem>
                      <SelectItem value="voicemail">Left Voicemail</SelectItem>
                      <SelectItem value="bounced">Bounced</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Subject (optional)</Label>
                  <Input
                    value={newActivity.subject}
                    onChange={(e) => setNewActivity({...newActivity, subject: e.target.value})}
                    placeholder="Brief description..."
                  />
                </div>

                <div className="space-y-2">
                  <Label>Notes (optional)</Label>
                  <Textarea
                    value={newActivity.notes}
                    onChange={(e) => setNewActivity({...newActivity, notes: e.target.value})}
                    placeholder="Additional details..."
                    rows={2}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="got_response"
                    checked={newActivity.got_response}
                    onChange={(e) => setNewActivity({...newActivity, got_response: e.target.checked})}
                    className="rounded border-gray-300"
                  />
                  <Label htmlFor="got_response" className="text-sm font-normal">Got a response from contact</Label>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleLogActivity} disabled={logging}>
              {logging ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Log Activity
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default PipelinePage;
