import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Checkbox } from '../components/ui/checkbox';
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
  TrendingUp, Package, Loader2, AlertCircle, ArrowRight, Save
} from 'lucide-react';
import { toast } from 'sonner';

const PipelinePage = () => {
  const { api, currentWorkspace } = useAuth();
  const { dealId } = useParams();
  const [loading, setLoading] = useState(true);
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState(null);
  const [kanbanData, setKanbanData] = useState(null);
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [showDealSheet, setShowDealSheet] = useState(false);
  const [dealSheetTab, setDealSheetTab] = useState('details');
  const [nextStepAt, setNextStepAt] = useState('');
  const [nextStepNote, setNextStepNote] = useState('');
  const [savingNextStep, setSavingNextStep] = useState(false);
  const [estimatedCloseAt, setEstimatedCloseAt] = useState('');
  const [productServiceType, setProductServiceType] = useState('');
  const [proposalValue, setProposalValue] = useState('');
  const [commercialSummaryUrl, setCommercialSummaryUrl] = useState('');
  const [stakeholderMapText, setStakeholderMapText] = useState('{}');
  const [paymentTerms, setPaymentTerms] = useState('');
  const [contractFinalValue, setContractFinalValue] = useState('');
  const [clientName, setClientName] = useState('');
  const [partnerCommissionStructure, setPartnerCommissionStructure] = useState('');
  const [productCategory, setProductCategory] = useState('');
  const [savingDealMeta, setSavingDealMeta] = useState(false);
  const [dealContactId, setDealContactId] = useState('');
  const [savingDealContact, setSavingDealContact] = useState(false);
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

  // Add Deal state
  const [showAddDealDialog, setShowAddDealDialog] = useState(false);
  const [addingDeal, setAddingDeal] = useState(false);
  const [contacts, setContacts] = useState([]);
  const [newDeal, setNewDeal] = useState({
    name: '',
    amount: '',
    contact_id: '',
    pipeline_id: '',
    stage_id: '',
    next_step_at: '',
    next_step_note: '',
    estimated_close_date: '',
    product_service_type: '',
    sales_motion_type: 'partnership_sales',
    partner_name: '',
    product_name: '',
    client_name: '',
    partner_commission_structure: '',
    product_category: ''
  });

  const toDateTimeLocal = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const fromDateTimeLocal = (value) => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  };

  useEffect(() => {
    fetchPipelines();
    fetchContacts();
  }, [currentWorkspace]);

  useEffect(() => {
    const openDealFromUrl = async () => {
      if (!dealId) return;
      try {
        const res = await api.get(`/deals/${dealId}`);
        const d = res.data;
        if (d?.pipeline_id) setSelectedPipeline(d.pipeline_id);
        setSelectedDeal(d);
        setNextStepAt(toDateTimeLocal(d.next_step_at));
        setNextStepNote(d.next_step_note || '');
        setDealContactId(d.contact_id || '');
        syncDealMetaFromDeal(d);
        setDealSheetTab('details');
        setShowDealSheet(true);
        await fetchDealCalculation(d.id);
      } catch (error) {
        console.error('Error opening deal from URL:', error);
        toast.error(error.response?.data?.detail || 'Failed to load deal');
      }
    };

    openDealFromUrl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dealId]);

  useEffect(() => {
    if (selectedPipeline) {
      fetchKanbanData(selectedPipeline);
    }
  }, [selectedPipeline]);

  const fetchPipelines = async () => {
    try {
      const response = await api.get('/pipelines');
      setPipelines(response.data.pipelines);
      setSelectedPipeline(prev => prev || (response.data.pipelines?.[0]?.id || null));
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

  const fetchContacts = async () => {
    try {
      const response = await api.get('/contacts?page_size=100');
      setContacts(response.data.contacts || []);
    } catch (error) {
      console.error('Error fetching contacts:', error);
    }
  };

  const openAddDealDialog = () => {
    // Set default pipeline and stage
    if (selectedPipeline && kanbanData?.columns?.length > 0) {
      const defaultNextStep = toDateTimeLocal(new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString());
      const defaultCloseDate = toDateTimeLocal(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString());
      setNewDeal({
        name: '',
        amount: '',
        contact_id: '',
        pipeline_id: selectedPipeline,
        stage_id: kanbanData.columns[0].id, // First stage
        next_step_at: defaultNextStep,
        next_step_note: '',
        estimated_close_date: defaultCloseDate,
        product_service_type: 'Elev8 Services',
        sales_motion_type: 'partnership_sales',
        partner_name: '',
        product_name: '',
        client_name: '',
        partner_commission_structure: '',
        product_category: ''
      });
    }
    setShowAddDealDialog(true);
  };

  const handleAddDeal = async () => {
    if (!newDeal.name.trim() || !newDeal.contact_id || !newDeal.pipeline_id || !newDeal.stage_id || !newDeal.next_step_at) {
      toast.error('Deal name, contact, stage, and next step are required');
      return;
    }
    const dealAmount = Number(newDeal.amount);
    if (newDeal.amount === '' || Number.isNaN(dealAmount) || dealAmount < 0) {
      toast.error('Estimated value is required');
      return;
    }
    if (!newDeal.estimated_close_date) {
      toast.error('Estimated close date is required');
      return;
    }
    if (!newDeal.product_service_type?.trim()) {
      toast.error('Product / service type is required');
      return;
    }

    if (newDeal.sales_motion_type === 'partner_sales') {
      if (!newDeal.partner_name?.trim() || !newDeal.product_name?.trim()) {
        toast.error('Partner name and product are required for Partner Sales');
        return;
      }
      if (!newDeal.client_name?.trim() || !newDeal.partner_commission_structure?.trim() || !newDeal.product_category?.trim()) {
        toast.error('Client name, commission structure, and product category are required for Partner Sales');
        return;
      }
    }

    setAddingDeal(true);
    try {
      await api.post('/deals', {
        name: newDeal.name.trim(),
        amount: dealAmount,
        contact_id: newDeal.contact_id,
        pipeline_id: newDeal.pipeline_id,
        stage_id: newDeal.stage_id,
        next_step_at: fromDateTimeLocal(newDeal.next_step_at),
        next_step_note: newDeal.next_step_note || null,
        estimated_close_date: fromDateTimeLocal(newDeal.estimated_close_date),
        product_service_type: newDeal.product_service_type?.trim(),
        sales_motion_type: newDeal.sales_motion_type,
        partner_name: newDeal.sales_motion_type === 'partner_sales' ? newDeal.partner_name?.trim() : null,
        product_name: newDeal.sales_motion_type === 'partner_sales' ? newDeal.product_name?.trim() : null,
        client_name: newDeal.sales_motion_type === 'partner_sales' ? newDeal.client_name?.trim() : null,
        partner_commission_structure: newDeal.sales_motion_type === 'partner_sales' ? newDeal.partner_commission_structure?.trim() : null,
        product_category: newDeal.sales_motion_type === 'partner_sales' ? newDeal.product_category?.trim() : null
      });

      // Refresh kanban data
      await fetchKanbanData(selectedPipeline);

      // Reset form and close dialog
      setNewDeal({
        name: '',
        amount: '',
        contact_id: '',
        pipeline_id: '',
        stage_id: '',
        next_step_at: '',
        next_step_note: '',
        estimated_close_date: '',
        product_service_type: '',
        sales_motion_type: 'partnership_sales',
        partner_name: '',
        product_name: '',
        client_name: '',
        partner_commission_structure: '',
        product_category: ''
      });
      setShowAddDealDialog(false);
      toast.success('Deal created');
    } catch (error) {
      console.error('Error creating deal:', error);
      toast.error(error.response?.data?.detail || 'Failed to create deal');
    } finally {
      setAddingDeal(false);
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
    setNextStepAt(toDateTimeLocal(deal.next_step_at));
    setNextStepNote(deal.next_step_note || '');
    setDealContactId(deal.contact_id || '');
    syncDealMetaFromDeal(deal);
    setDealSheetTab('details');
    setShowDealSheet(true);
    await fetchDealCalculation(deal.id);
  };

  const closeDealSheet = () => {
    setShowDealSheet(false);
    setSelectedDeal(null);
    setCalculationData(null);
    setCalcInputs({});
    setNextStepAt('');
    setNextStepNote('');
    setEstimatedCloseAt('');
    setProductServiceType('');
    setProposalValue('');
    setCommercialSummaryUrl('');
    setStakeholderMapText('{}');
    setPaymentTerms('');
    setContractFinalValue('');
    setClientName('');
    setPartnerCommissionStructure('');
    setProductCategory('');
    setDealContactId('');
    setDealSheetTab('details');
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

  const saveNextStep = async () => {
    if (!selectedDeal) return;

    if (!nextStepAt) {
      toast.error('Next step date/time is required');
      return;
    }

    setSavingNextStep(true);
    try {
      const nextStepIso = fromDateTimeLocal(nextStepAt);
      await api.put(`/deals/${selectedDeal.id}`, {
        next_step_at: nextStepIso,
        next_step_note: nextStepNote || null
      });

      setSelectedDeal(prev => prev ? ({
        ...prev,
        next_step_at: nextStepIso,
        next_step_note: nextStepNote || null
      }) : prev);

      await fetchKanbanData(selectedPipeline);
      toast.success('Next step saved');
    } catch (error) {
      console.error('Error saving next step:', error);
      toast.error(error.response?.data?.detail || 'Failed to save next step');
    } finally {
      setSavingNextStep(false);
    }
  };

  const saveDealContact = async () => {
    if (!selectedDeal) return;

    if (!dealContactId) {
      toast.error('Contact is required');
      return;
    }

    setSavingDealContact(true);
    try {
      await api.put(`/deals/${selectedDeal.id}`, {
        contact_id: dealContactId
      });

      const contact = contacts.find(c => c.id === dealContactId);
      const contactName = contact ? `${contact.first_name} ${contact.last_name}`.trim() : selectedDeal.contact_name;

      setSelectedDeal(prev => prev ? ({
        ...prev,
        contact_id: dealContactId,
        contact_name: contactName
      }) : prev);

      await fetchKanbanData(selectedPipeline);
      toast.success('Contact updated');
    } catch (error) {
      console.error('Error updating deal contact:', error);
      toast.error(error.response?.data?.detail || 'Failed to update contact');
    } finally {
      setSavingDealContact(false);
    }
  };

  const saveDealMeta = async () => {
    if (!selectedDeal) return;
    if (!estimatedCloseAt) {
      toast.error('Estimated close date is required');
      return;
    }
    if (!productServiceType?.trim()) {
      toast.error('Product / service type is required');
      return;
    }

    setSavingDealMeta(true);
    try {
      const payload = {
        estimated_close_date: fromDateTimeLocal(estimatedCloseAt),
        product_service_type: productServiceType.trim(),
        proposal_value: proposalValue === '' ? null : Number(proposalValue),
        commercial_summary_url: commercialSummaryUrl?.trim() || null,
        stakeholder_map: parseStakeholderMap(stakeholderMapText),
        payment_terms: paymentTerms?.trim() || null,
        contract_final_value: contractFinalValue === '' ? null : Number(contractFinalValue),
      };

      if (selectedDeal.sales_motion_type === 'partner_sales') {
        payload.client_name = clientName?.trim() || null;
        payload.partner_commission_structure = partnerCommissionStructure?.trim() || null;
        payload.product_category = productCategory?.trim() || null;
      }

      const res = await api.put(`/deals/${selectedDeal.id}`, payload);
      setSelectedDeal(res.data);
      syncDealMetaFromDeal(res.data);
      await fetchKanbanData(selectedPipeline);
      toast.success('Deal fields saved');
    } catch (error) {
      console.error('Error saving deal fields:', error);
      toast.error(error.response?.data?.detail || 'Failed to save deal fields');
    } finally {
      setSavingDealMeta(false);
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

  const getLeadTierBadge = (tier) => {
    const t = (tier || '').toString().trim().toUpperCase();
    const styles = {
      A: 'bg-green-500/20 text-green-400 border-green-500/30',
      B: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      C: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      D: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
    };
    if (!styles[t]) return <Badge variant="outline">-</Badge>;
    return <Badge className={styles[t]}>{t}</Badge>;
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

          <Button onClick={openAddDealDialog}>
            <Plus className="w-4 h-4 mr-2" />
            Add Deal
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

                      {deal.cadence_breached && (
                        <div className="flex items-center gap-1">
                          <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-xs">
                            <Clock className="w-3 h-3 mr-1" />
                            Stale {deal.cadence_hours_since_touch ?? '-'}h
                          </Badge>
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

      {/* Add Deal Dialog */}
      <AlertDialog open={showAddDealDialog} onOpenChange={setShowAddDealDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Create New Deal</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4 pt-2">
                <div className="space-y-2">
                  <Label htmlFor="deal-name">Deal Name <span className="text-red-500">*</span></Label>
                  <Input
                    id="deal-name"
                    value={newDeal.name}
                    onChange={(e) => setNewDeal({ ...newDeal, name: e.target.value })}
                    placeholder="Enter deal name..."
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="deal-amount">Deal Value <span className="text-red-500">*</span></Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        id="deal-amount"
                        type="number"
                      value={newDeal.amount}
                      onChange={(e) => setNewDeal({ ...newDeal, amount: e.target.value })}
                      placeholder="0.00"
                      className="pl-9"
                        step="0.01"
                      />
                    </div>
                  </div>

                <div className="space-y-2">
                  <Label>Pipeline <span className="text-red-500">*</span></Label>
                  <Select
                    value={newDeal.pipeline_id}
                    onValueChange={(value) => {
                      const pipeline = pipelines.find(p => p.id === value);
                      setNewDeal({
                        ...newDeal,
                        pipeline_id: value,
                        stage_id: '' // Reset stage when pipeline changes
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select pipeline..." />
                    </SelectTrigger>
                    <SelectContent>
                      {pipelines.map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Stage <span className="text-red-500">*</span></Label>
                  <Select
                    value={newDeal.stage_id}
                    onValueChange={(value) => setNewDeal({ ...newDeal, stage_id: value })}
                    disabled={!newDeal.pipeline_id}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select stage..." />
                    </SelectTrigger>
                    <SelectContent>
                      {kanbanData?.columns?.map(stage => (
                        <SelectItem key={stage.id} value={stage.id}>{stage.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Sales Motion Type <span className="text-red-500">*</span></Label>
                  <Select
                    value={newDeal.sales_motion_type}
                    onValueChange={(value) => setNewDeal({ ...newDeal, sales_motion_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="partnership_sales">Partnership Sales (Elev8 services)</SelectItem>
                      <SelectItem value="partner_sales">Partner Sales (partner product)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {newDeal.sales_motion_type === 'partner_sales' && (
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Partner Name <span className="text-red-500">*</span></Label>
                      <Input
                        value={newDeal.partner_name}
                        onChange={(e) => setNewDeal({ ...newDeal, partner_name: e.target.value })}
                        placeholder="Partner"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Partner Product <span className="text-red-500">*</span></Label>
                      <Input
                        value={newDeal.product_name}
                        onChange={(e) => setNewDeal({ ...newDeal, product_name: e.target.value })}
                        placeholder="Product"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Client Name <span className="text-red-500">*</span></Label>
                      <Input
                        value={newDeal.client_name}
                        onChange={(e) => setNewDeal({ ...newDeal, client_name: e.target.value })}
                        placeholder="Client name"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Commission Structure <span className="text-red-500">*</span></Label>
                      <Input
                        value={newDeal.partner_commission_structure}
                        onChange={(e) => setNewDeal({ ...newDeal, partner_commission_structure: e.target.value })}
                        placeholder="e.g. 12% of net"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Product Category <span className="text-red-500">*</span></Label>
                      <Input
                        value={newDeal.product_category}
                        onChange={(e) => setNewDeal({ ...newDeal, product_category: e.target.value })}
                        placeholder="Category"
                      />
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Estimated Close Date <span className="text-red-500">*</span></Label>
                    <Input
                      type="datetime-local"
                      value={newDeal.estimated_close_date}
                      onChange={(e) => setNewDeal({ ...newDeal, estimated_close_date: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Product / Service Type <span className="text-red-500">*</span></Label>
                    <Input
                      value={newDeal.product_service_type}
                      onChange={(e) => setNewDeal({ ...newDeal, product_service_type: e.target.value })}
                      placeholder="e.g. Elev8 Services"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Next Step <span className="text-red-500">*</span></Label>
                  <Input
                    type="datetime-local"
                    value={newDeal.next_step_at}
                    onChange={(e) => setNewDeal({ ...newDeal, next_step_at: e.target.value })}
                  />
                  <p className="text-xs text-muted-foreground">Required for all active deals.</p>
                </div>

                <div className="space-y-2">
                  <Label>Next Step Note</Label>
                  <Textarea
                    value={newDeal.next_step_note}
                    onChange={(e) => setNewDeal({ ...newDeal, next_step_note: e.target.value })}
                    placeholder="What is the next action?"
                    rows={2}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Associated Contact <span className="text-red-500">*</span></Label>
                  <Select
                    value={newDeal.contact_id}
                    onValueChange={(value) => setNewDeal({ ...newDeal, contact_id: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select contact..." />
                    </SelectTrigger>
                    <SelectContent>
                      {contacts.map(c => (
                        <SelectItem key={c.id} value={c.id}>
                          {c.first_name} {c.last_name} {c.email && `(${c.email})`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setShowAddDealDialog(false);
              setNewDeal({
                name: '',
                amount: '',
                contact_id: '',
                pipeline_id: '',
                stage_id: '',
                next_step_at: '',
                next_step_note: '',
                estimated_close_date: '',
                product_service_type: '',
                sales_motion_type: 'partnership_sales',
                partner_name: '',
                product_name: '',
                client_name: '',
                partner_commission_structure: '',
                product_category: ''
              });
            }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleAddDeal}
              disabled={
                !newDeal.name.trim() ||
                !newDeal.pipeline_id ||
                !newDeal.stage_id ||
                !newDeal.contact_id ||
                newDeal.amount === '' ||
                Number.isNaN(Number(newDeal.amount)) ||
                Number(newDeal.amount) < 0 ||
                !newDeal.next_step_at ||
                !newDeal.estimated_close_date ||
                !newDeal.product_service_type?.trim() ||
                addingDeal
              }
            >
              {addingDeal ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Deal
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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

              <Tabs value={dealSheetTab} onValueChange={setDealSheetTab} className="flex-1 flex flex-col">
                <TabsList className="mx-6 mt-4 flex flex-wrap">
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="spiced">
                    <FileText className="w-4 h-4 mr-1" />
                    SPICED
                  </TabsTrigger>
                  <TabsTrigger value="demo">
                    <Calendar className="w-4 h-4 mr-1" />
                    Demo
                  </TabsTrigger>
                  <TabsTrigger value="tasks">Tasks</TabsTrigger>
                  <TabsTrigger value="calculation">
                    <Calculator className="w-4 h-4 mr-1" />
                    Calculator
                  </TabsTrigger>
                  <TabsTrigger value="activity">Activity</TabsTrigger>
                  <TabsTrigger value="handoff">Handoff</TabsTrigger>
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
                          <div className="col-span-2 space-y-2">
                            <Label className="text-xs text-muted-foreground">Contact <span className="text-red-500">*</span></Label>
                            <div className="flex gap-2">
                              <Select value={dealContactId} onValueChange={setDealContactId}>
                                <SelectTrigger className="flex-1">
                                  <SelectValue placeholder="Select contact..." />
                                </SelectTrigger>
                                <SelectContent>
                                  {contacts.map(c => (
                                    <SelectItem key={c.id} value={c.id}>
                                      {c.first_name} {c.last_name} {c.email && `(${c.email})`}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <Button
                                variant="outline"
                                onClick={saveDealContact}
                                disabled={savingDealContact || !dealContactId}
                              >
                                {savingDealContact ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  'Save'
                                )}
                              </Button>
                            </div>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Status</Label>
                            <p className="font-medium capitalize">{selectedDeal.status}</p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Risk Flag</Label>
                            <p className="font-medium">{selectedDeal.at_risk ? 'At Risk' : 'Normal'}</p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Lead Tier</Label>
                            <div className="mt-1">{getLeadTierBadge(selectedDeal.lead_tier)}</div>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Locked</Label>
                            <p className="font-medium">{selectedDeal.deal_locked ? 'Yes' : 'No'}</p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Sales Motion</Label>
                            <p className="font-medium">
                              {selectedDeal.sales_motion_type === 'partner_sales'
                                ? 'Partner Sales'
                                : 'Partnership Sales'}
                            </p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Lead Score</Label>
                            <p className="font-medium">{selectedDeal.lead_score ?? '-'}</p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Partner</Label>
                            <p className="font-medium">
                              {selectedDeal.sales_motion_type === 'partner_sales'
                                ? (selectedDeal.partner_name || '-')
                                : '-'}
                            </p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Product</Label>
                            <p className="font-medium">
                              {selectedDeal.sales_motion_type === 'partner_sales'
                                ? (selectedDeal.product_name || '-')
                                : '-'}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Commercial & Stage Fields</CardTitle>
                        <CardDescription>
                          Required fields for Decision Pending, Contract Sent, and Closed Won are enforced here.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Estimated Close Date <span className="text-red-500">*</span></Label>
                            <Input
                              type="datetime-local"
                              value={estimatedCloseAt}
                              onChange={(e) => setEstimatedCloseAt(e.target.value)}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Product / Service Type <span className="text-red-500">*</span></Label>
                            <Input
                              value={productServiceType}
                              onChange={(e) => setProductServiceType(e.target.value)}
                              placeholder="e.g. Elev8 Services"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Proposal Value</Label>
                            <Input
                              type="number"
                              value={proposalValue}
                              onChange={(e) => setProposalValue(e.target.value)}
                              placeholder="0.00"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Commercial Summary URL</Label>
                            <Input
                              value={commercialSummaryUrl}
                              onChange={(e) => setCommercialSummaryUrl(e.target.value)}
                              placeholder="https://..."
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Payment Terms</Label>
                            <Input
                              value={paymentTerms}
                              onChange={(e) => setPaymentTerms(e.target.value)}
                              placeholder="e.g. Net 30"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Final Contract Value</Label>
                            <Input
                              type="number"
                              value={contractFinalValue}
                              onChange={(e) => setContractFinalValue(e.target.value)}
                              placeholder="0.00"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <Label>Stakeholder Map (JSON or comma-separated names)</Label>
                          <Textarea
                            value={stakeholderMapText}
                            onChange={(e) => setStakeholderMapText(e.target.value)}
                            rows={4}
                            placeholder='{"decision_maker":"Jane","champion":"Mark"}'
                          />
                        </div>

                        {selectedDeal.sales_motion_type === 'partner_sales' && (
                          <div className="grid grid-cols-3 gap-4">
                            <div className="space-y-2">
                              <Label>Client Name</Label>
                              <Input
                                value={clientName}
                                onChange={(e) => setClientName(e.target.value)}
                                placeholder="Client name"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Commission Structure</Label>
                              <Input
                                value={partnerCommissionStructure}
                                onChange={(e) => setPartnerCommissionStructure(e.target.value)}
                                placeholder="e.g. 12% of net"
                              />
                            </div>
                            <div className="space-y-2">
                              <Label>Product Category</Label>
                              <Input
                                value={productCategory}
                                onChange={(e) => setProductCategory(e.target.value)}
                                placeholder="Category"
                              />
                            </div>
                          </div>
                        )}

                        <Button onClick={saveDealMeta} disabled={savingDealMeta} className="w-full">
                          {savingDealMeta ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Saving...
                            </>
                          ) : (
                            <>
                              <Save className="w-4 h-4 mr-2" />
                              Save Commercial Fields
                            </>
                          )}
                        </Button>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          Next Step
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="space-y-2">
                          <Label>Next Step Date/Time <span className="text-red-500">*</span></Label>
                          <Input
                            type="datetime-local"
                            value={nextStepAt}
                            onChange={(e) => setNextStepAt(e.target.value)}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Next Step Note</Label>
                          <Textarea
                            value={nextStepNote}
                            onChange={(e) => setNextStepNote(e.target.value)}
                            placeholder="What is the next action?"
                            rows={2}
                          />
                        </div>
                        <Button onClick={saveNextStep} disabled={savingNextStep || !nextStepAt} className="w-full">
                          {savingNextStep ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Saving...
                            </>
                          ) : (
                            <>
                              <Clock className="w-4 h-4 mr-2" />
                              Save Next Step
                            </>
                          )}
                        </Button>
                        {!selectedDeal.next_step_at && (
                          <p className="text-xs text-amber-600">
                            This deal has no next step scheduled. Playbook rules require a next step on active deals.
                          </p>
                        )}
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
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1" onClick={() => setDealSheetTab('demo')}>
                            <Calendar className="w-4 h-4" />
                            <span className="text-xs">Schedule</span>
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="spiced" className="p-6 space-y-4">
                    <SpicedPanel
                      deal={selectedDeal}
                      api={api}
                      onDealUpdated={(d) => {
                        setSelectedDeal(d);
                        syncDealMetaFromDeal(d);
                      }}
                      onUpdate={() => fetchKanbanData(selectedPipeline)}
                    />
                  </TabsContent>

                  <TabsContent value="demo" className="p-6 space-y-4">
                    <DemoPanel
                      deal={selectedDeal}
                      api={api}
                      onDealUpdated={(d) => {
                        setSelectedDeal(d);
                        syncDealMetaFromDeal(d);
                      }}
                      onUpdate={() => fetchKanbanData(selectedPipeline)}
                    />
                  </TabsContent>

                  <TabsContent value="tasks" className="p-6 space-y-4">
                    <TasksPanel
                      dealId={selectedDeal.id}
                      api={api}
                      onUpdate={() => fetchKanbanData(selectedPipeline)}
                    />
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

                  <TabsContent value="handoff" className="p-6 space-y-4">
                    <HandoffPanel
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

const DemoPanel = ({ deal, api, onDealUpdated, onUpdate }) => {
  const toDateTimeLocal = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const fromDateTimeLocal = (value) => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  };

  const formatStakeholderMap = (value) => {
    if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length === 0) {
      return '{}';
    }
    try {
      return JSON.stringify(value, null, 2);
    } catch (_err) {
      return '{}';
    }
  };

  const parseStakeholderMap = (raw) => {
    const text = (raw || '').trim();
    if (!text || text === '{}') return {};
    try {
      const parsed = JSON.parse(text);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
    } catch (_err) {
      // fallback below
    }
    const names = text
      .split(/[\n,]/)
      .map((x) => x.trim())
      .filter(Boolean);
    if (!names.length) return {};
    return { stakeholders: names };
  };

  const syncDealMetaFromDeal = (deal) => {
    if (!deal) return;
    setEstimatedCloseAt(toDateTimeLocal(deal.estimated_close_date));
    setProductServiceType(deal.product_service_type || '');
    setProposalValue(deal.proposal_value === null || deal.proposal_value === undefined ? '' : String(deal.proposal_value));
    setCommercialSummaryUrl(deal.commercial_summary_url || '');
    setStakeholderMapText(formatStakeholderMap(deal.stakeholder_map || {}));
    setPaymentTerms(deal.payment_terms || '');
    setContractFinalValue(deal.contract_final_value === null || deal.contract_final_value === undefined ? '' : String(deal.contract_final_value));
    setClientName(deal.client_name || '');
    setPartnerCommissionStructure(deal.partner_commission_structure || '');
    setProductCategory(deal.product_category || '');
  };

  const [form, setForm] = React.useState({
    demo_title: '',
    demo_type: '',
    demo_status: 'auto',
    demo_scheduled_at: '',
    demo_duration_minutes: 30,
    demo_meet_url: '',
    demo_calendar_url: '',
    demo_completed_at: '',
    demo_notes: ''
  });
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (!deal) return;
    setForm({
      demo_title: deal.demo_title || deal.name || '',
      demo_type: deal.demo_type || 'consultation',
      demo_status: deal.demo_status || 'auto',
      demo_scheduled_at: toDateTimeLocal(deal.demo_scheduled_at),
      demo_duration_minutes: deal.demo_duration_minutes || 30,
      demo_meet_url: deal.demo_meet_url || '',
      demo_calendar_url: deal.demo_calendar_url || '',
      demo_completed_at: toDateTimeLocal(deal.demo_completed_at),
      demo_notes: deal.demo_notes || ''
    });
  }, [deal?.id]);

  const buildGoogleCalendarUrl = () => {
    const startIso = fromDateTimeLocal(form.demo_scheduled_at);
    if (!startIso) {
      toast.error('Set a demo scheduled date/time first');
      return null;
    }

    const start = new Date(startIso);
    const durationMinutes = Number(form.demo_duration_minutes) || 30;
    const end = new Date(start.getTime() + durationMinutes * 60 * 1000);

    const pad = (n) => String(n).padStart(2, '0');
    const fmt = (d) =>
      `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`;

    const title = (form.demo_title || `${deal?.name || 'Demo'} Demo`).trim();
    const detailsLines = [
      deal?.name ? `Deal: ${deal.name}` : null,
      deal?.contact_name ? `Contact: ${deal.contact_name}` : null,
      form.demo_meet_url ? `Meet: ${form.demo_meet_url}` : null,
      form.demo_notes ? `Notes: ${form.demo_notes}` : null,
    ].filter(Boolean);

    const params = new URLSearchParams({
      action: 'TEMPLATE',
      text: title,
      dates: `${fmt(start)}/${fmt(end)}`,
      details: detailsLines.join('\n'),
      location: form.demo_meet_url || ''
    });

    return `https://calendar.google.com/calendar/render?${params.toString()}`;
  };

  const openGoogleCalendar = () => {
    const url = buildGoogleCalendarUrl();
    if (!url) return;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const saveDemo = async () => {
    if (!deal?.id) return;
    setSaving(true);
    try {
      const payload = {
        demo_title: form.demo_title?.trim() || null,
        demo_type: form.demo_type?.trim() || null,
        demo_status: form.demo_status === 'auto' ? null : form.demo_status,
        demo_scheduled_at: fromDateTimeLocal(form.demo_scheduled_at),
        demo_duration_minutes: Number(form.demo_duration_minutes) || 30,
        demo_meet_url: form.demo_meet_url?.trim() || null,
        demo_calendar_url: form.demo_calendar_url?.trim() || null,
        demo_completed_at: fromDateTimeLocal(form.demo_completed_at),
        demo_notes: form.demo_notes || null,
      };

      const res = await api.put(`/deals/${deal.id}`, payload);
      toast.success('Demo saved');
      if (onDealUpdated) onDealUpdated(res.data);
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error saving demo:', error);
      toast.error(error.response?.data?.detail || 'Failed to save demo');
    } finally {
      setSaving(false);
    }
  };

  if (!deal) return null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Demo Scheduling (v1)
          </CardTitle>
          <CardDescription>
            Store demo details + open a Google Calendar template event (no OAuth sync in v1).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Title</Label>
            <Input
              value={form.demo_title}
              onChange={(e) => setForm((p) => ({ ...p, demo_title: e.target.value }))}
              placeholder="e.g. ACME Corp | Solution Consultation"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Type</Label>
              <Input
                value={form.demo_type}
                onChange={(e) => setForm((p) => ({ ...p, demo_type: e.target.value }))}
                placeholder="consultation / webinar / demo"
              />
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={form.demo_status} onValueChange={(v) => setForm((p) => ({ ...p, demo_status: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto</SelectItem>
                  <SelectItem value="scheduled">Scheduled</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="no_show">No-show</SelectItem>
                  <SelectItem value="canceled">Canceled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Scheduled At</Label>
              <Input
                type="datetime-local"
                value={form.demo_scheduled_at}
                onChange={(e) => setForm((p) => ({ ...p, demo_scheduled_at: e.target.value }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Duration (minutes)</Label>
              <Input
                type="number"
                min={5}
                max={480}
                value={form.demo_duration_minutes}
                onChange={(e) => setForm((p) => ({ ...p, demo_duration_minutes: e.target.value }))}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Google Meet URL</Label>
            <Input
              value={form.demo_meet_url}
              onChange={(e) => setForm((p) => ({ ...p, demo_meet_url: e.target.value }))}
              placeholder="https://meet.google.com/..."
            />
          </div>

          <div className="space-y-2">
            <Label>Calendar Event URL (optional)</Label>
            <Input
              value={form.demo_calendar_url}
              onChange={(e) => setForm((p) => ({ ...p, demo_calendar_url: e.target.value }))}
              placeholder="Paste the created event URL if desired"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Completed At (optional)</Label>
              <Input
                type="datetime-local"
                value={form.demo_completed_at}
                onChange={(e) => setForm((p) => ({ ...p, demo_completed_at: e.target.value }))}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              value={form.demo_notes}
              onChange={(e) => setForm((p) => ({ ...p, demo_notes: e.target.value }))}
              rows={3}
              placeholder="Add context, agenda, external CRM link, etc."
            />
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={openGoogleCalendar} disabled={!form.demo_scheduled_at}>
              <Calendar className="w-4 h-4 mr-2" />
              Create Google Calendar Event
            </Button>
            {form.demo_calendar_url?.trim() && (
              <Button variant="outline" asChild>
                <a href={form.demo_calendar_url} target="_blank" rel="noreferrer">
                  Open Event
                </a>
              </Button>
            )}
          </div>

          <Button onClick={saveDemo} disabled={saving} className="w-full">
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Demo
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

const SpicedPanel = ({ deal, api, onDealUpdated, onUpdate }) => {
  const FIELDS = [
    { key: 'situation', label: 'Situation' },
    { key: 'problem', label: 'Problem' },
    { key: 'implication', label: 'Implication' },
    { key: 'critical_event', label: 'Critical Event' },
    { key: 'economic_impact', label: 'Economic Impact' },
    { key: 'decision', label: 'Decision' },
  ];

  const [spiced, setSpiced] = React.useState({});
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (!deal) return;
    const existing = deal.spiced || {};
    const next = {};
    for (const f of FIELDS) next[f.key] = existing[f.key] || '';
    setSpiced(next);
  }, [deal?.id]);

  const completeCount = FIELDS.filter((f) => (spiced?.[f.key] || '').toString().trim().length > 0).length;
  const pct = Math.round((completeCount / FIELDS.length) * 100);
  const isComplete = completeCount === FIELDS.length;

  const saveSpiced = async () => {
    if (!deal?.id) return;
    setSaving(true);
    try {
      const payload = { spiced: { ...spiced } };
      const res = await api.put(`/deals/${deal.id}`, payload);
      toast.success('SPICED saved');
      if (onDealUpdated) onDealUpdated(res.data);
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error saving SPICED:', error);
      toast.error(error.response?.data?.detail || 'Failed to save SPICED');
    } finally {
      setSaving(false);
    }
  };

  if (!deal) return null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-4 h-4" />
            SPICED Summary
            {isComplete ? (
              <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Complete</Badge>
            ) : (
              <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">Incomplete</Badge>
            )}
          </CardTitle>
          <CardDescription>
            Required for playbook-aligned discovery. Demo Completed stage requires SPICED complete.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{completeCount}/{FIELDS.length} fields complete</span>
              <span>{pct}%</span>
            </div>
            <Progress value={pct} className="h-2" />
          </div>

          {FIELDS.map((f) => (
            <div key={f.key} className="space-y-2">
              <Label>{f.label}</Label>
              <Textarea
                value={spiced?.[f.key] || ''}
                onChange={(e) => setSpiced((p) => ({ ...(p || {}), [f.key]: e.target.value }))}
                rows={2}
                placeholder={`Enter ${f.label.toLowerCase()}...`}
              />
            </div>
          ))}

          <Button onClick={saveSpiced} disabled={saving} className="w-full">
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save SPICED
              </>
            )}
          </Button>
        </CardContent>
      </Card>
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

const TasksPanel = ({ dealId, api, onUpdate }) => {
  const [loading, setLoading] = React.useState(true);
  const [tasks, setTasks] = React.useState([]);
  const [showCreate, setShowCreate] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [newTask, setNewTask] = React.useState({
    title: '',
    due_at: '',
    description: ''
  });

  const toDateTimeLocal = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const fromDateTimeLocal = (value) => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  React.useEffect(() => {
    if (!dealId) return;
    fetchTasks();
    const defaultDue = toDateTimeLocal(new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString());
    setNewTask(prev => ({ ...prev, due_at: defaultDue }));
  }, [dealId]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/tasks?status=open&related_type=deal&related_id=${dealId}&page_size=200`);
      setTasks(response.data.tasks || []);
    } catch (error) {
      console.error('Error fetching tasks:', error);
      toast.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const completeTask = async (task) => {
    try {
      await api.put(`/tasks/${task.id}`, { status: 'completed' });
      toast.success('Task completed');
      await fetchTasks();
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error completing task:', error);
      toast.error(error.response?.data?.detail || 'Failed to complete task');
    }
  };

  const handleCreateTask = async () => {
    const title = (newTask.title || '').trim();
    const due = fromDateTimeLocal(newTask.due_at);
    if (!title) {
      toast.error('Task title is required');
      return;
    }
    if (!due) {
      toast.error('Due date/time is required');
      return;
    }

    setCreating(true);
    try {
      await api.post('/tasks', {
        title,
        due_at: due,
        description: (newTask.description || '').trim() || null,
        related_type: 'deal',
        related_id: dealId,
        kind: 'manual'
      });
      toast.success('Task created');
      setNewTask(prev => ({ ...prev, title: '', description: '' }));
      setShowCreate(false);
      await fetchTasks();
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error creating task:', error);
      toast.error(error.response?.data?.detail || 'Failed to create task');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base">Tasks</CardTitle>
              <CardDescription>Next steps and follow-ups for this deal.</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={fetchTasks} disabled={loading}>
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
              <Button size="sm" onClick={() => setShowCreate(v => !v)}>
                <Plus className="w-4 h-4 mr-2" />
                New
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {showCreate && (
            <div className="rounded-lg border p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2 col-span-2">
                  <Label>Title</Label>
                  <Input
                    value={newTask.title}
                    onChange={(e) => setNewTask(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="e.g. Follow up after demo"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Due</Label>
                  <Input
                    type="datetime-local"
                    value={newTask.due_at}
                    onChange={(e) => setNewTask(prev => ({ ...prev, due_at: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description (optional)</Label>
                  <Input
                    value={newTask.description}
                    onChange={(e) => setNewTask(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Notes..."
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setShowCreate(false)} disabled={creating}>
                  Cancel
                </Button>
                <Button className="flex-1" onClick={handleCreateTask} disabled={creating}>
                  {creating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
                  Create
                </Button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle2 className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No open tasks for this deal</p>
            </div>
          ) : (
            <div className="space-y-2">
              {tasks.map(t => {
                const dueMs = t.due_at ? new Date(t.due_at).getTime() : null;
                const overdue = dueMs && !Number.isNaN(dueMs) && dueMs < Date.now();
                return (
                  <div key={t.id} className="flex items-start justify-between gap-3 p-3 rounded-lg border">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">{t.title}</p>
                        {t.kind === 'next_step' && (
                          <Badge variant="outline">Next Step</Badge>
                        )}
                        {overdue && (
                          <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Overdue</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Due {formatDateTime(t.due_at)}{t.owner_name ? ` • Owner: ${t.owner_name}` : ''}
                      </p>
                      {t.description && (
                        <p className="text-sm text-muted-foreground mt-2">{t.description}</p>
                      )}
                    </div>
                    <Button variant="outline" size="sm" onClick={() => completeTask(t)}>
                      Complete
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

const HandoffPanel = ({ dealId, api, onUpdate }) => {
  const [handoff, setHandoff] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [users, setUsers] = React.useState([]);
  const [loadingUsers, setLoadingUsers] = React.useState(false);

  const [deliveryOwnerId, setDeliveryOwnerId] = React.useState('');
  const [kickoffAt, setKickoffAt] = React.useState('');
  const [notes, setNotes] = React.useState('');
  const [checklist, setChecklist] = React.useState({});

  const CHECKLIST_LABELS = {
    spiced_summary: 'SPICED summary',
    gap_analysis: 'Gap analysis',
    proposal: 'Proposal',
    contract: 'Contract',
    risk_notes: 'Risk notes',
    kickoff_readiness_checklist: 'Kickoff readiness checklist',
  };

  const CHECKLIST_KEYS = Object.keys(CHECKLIST_LABELS);

  const toDateTimeLocal = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) return '';
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const fromDateTimeLocal = (value) => {
    if (!value) return null;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  };

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const res = await api.get('/users');
      setUsers(res.data.users || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoadingUsers(false);
    }
  };

  const fetchHandoff = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/deals/${dealId}/handoff`);
      const data = res.data;
      setHandoff(data);
      setDeliveryOwnerId(data.delivery_owner_id || '');
      setKickoffAt(toDateTimeLocal(data.kickoff_at));
      setNotes(data.notes || '');
      setChecklist(data.checklist || {});
    } catch (error) {
      console.error('Error fetching handoff:', error);
      toast.error('Failed to load handoff');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    if (!dealId) return;
    fetchUsers();
    fetchHandoff();
  }, [dealId]);

  const missingItems = React.useMemo(() => {
    const missing = [];
    if (!deliveryOwnerId) missing.push('Delivery owner');
    if (!kickoffAt) missing.push('Kickoff scheduled');
    CHECKLIST_KEYS.forEach(k => {
      if (!checklist?.[k]) missing.push(CHECKLIST_LABELS[k]);
    });
    return missing;
  }, [deliveryOwnerId, kickoffAt, checklist]);

  const isComplete = missingItems.length === 0;

  const saveHandoff = async () => {
    const kickoffIso = kickoffAt ? fromDateTimeLocal(kickoffAt) : '';
    if (kickoffAt && !kickoffIso) {
      toast.error('Invalid kickoff date/time');
      return;
    }

    setSaving(true);
    try {
      const res = await api.put(`/deals/${dealId}/handoff`, {
        delivery_owner_id: deliveryOwnerId || '',
        kickoff_at: kickoffIso,
        notes: notes ?? '',
        checklist: CHECKLIST_KEYS.reduce((acc, k) => {
          acc[k] = Boolean(checklist?.[k]);
          return acc;
        }, {})
      });
      setHandoff(res.data);
      toast.success('Handoff saved');
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Error saving handoff:', error);
      toast.error(error.response?.data?.detail || 'Failed to save handoff');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base">Handoff to Delivery</CardTitle>
              <CardDescription>Required before moving to the Handoff stage.</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              {handoff?.status === 'completed' ? (
                <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Completed</Badge>
              ) : (
                <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">Pending</Badge>
              )}
              <Button variant="outline" size="sm" onClick={fetchHandoff} disabled={loading}>
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Delivery Owner <span className="text-red-500">*</span></Label>
                  <Select
                    value={deliveryOwnerId || 'unassigned'}
                    onValueChange={(v) => setDeliveryOwnerId(v === 'unassigned' ? '' : v)}
                    disabled={loadingUsers}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select owner..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unassigned">Unassigned</SelectItem>
                      {users.map(u => (
                        <SelectItem key={u.id} value={u.id}>{u.full_name || u.email}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Kickoff Scheduled <span className="text-red-500">*</span></Label>
                  <Input
                    type="datetime-local"
                    value={kickoffAt}
                    onChange={(e) => setKickoffAt(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Notes (optional)</Label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Risk notes, context for delivery..."
                />
              </div>

              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">Required artifacts</p>
                  {isComplete ? (
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Ready</Badge>
                  ) : (
                    <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Incomplete</Badge>
                  )}
                </div>
                <div className="space-y-3">
                  {CHECKLIST_KEYS.map((key) => (
                    <div key={key} className="flex items-start gap-3">
                      <Checkbox
                        checked={Boolean(checklist?.[key])}
                        onCheckedChange={(v) => setChecklist(prev => ({ ...prev, [key]: Boolean(v) }))}
                        id={`handoff_${key}`}
                      />
                      <Label htmlFor={`handoff_${key}`} className="text-sm font-normal cursor-pointer">
                        {CHECKLIST_LABELS[key]}
                      </Label>
                    </div>
                  ))}
                </div>
                {!isComplete && (
                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    Missing: {missingItems.join(', ')}
                  </div>
                )}
              </div>

              <Button onClick={saveHandoff} disabled={saving} className="w-full">
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Save Handoff
                  </>
                )}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default PipelinePage;
