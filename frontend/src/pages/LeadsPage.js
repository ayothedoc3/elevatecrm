import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { ScrollArea } from '../components/ui/scroll-area';
import { Progress } from '../components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '../components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import {
  Search, Plus, Mail, Phone, Building, User, MoreHorizontal,
  ChevronLeft, ChevronRight, Filter, Download, Upload, Target, RefreshCw,
  TrendingUp, Users, Zap, Star, Edit, Trash2, UserPlus, ArrowRight, Loader2
} from 'lucide-react';
import { toast } from 'sonner';

const LEAD_STATUS_OPTIONS = [
  { value: 'new', label: 'New' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'new_assigned', label: 'New / Assigned' },
  { value: 'working', label: 'Working' },
  { value: 'info_collected', label: 'Information Collected' },
  { value: 'qualified', label: 'Qualified' },
  { value: 'nurture', label: 'Nurture' },
  { value: 'unresponsive', label: 'Unresponsive' },
  { value: 'disqualified', label: 'Disqualified' },
  { value: 'converted', label: 'Converted' },
];

const LeadsPage = () => {
  const { api } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [filterTier, setFilterTier] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [selectedLead, setSelectedLead] = useState(null);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  const [stats, setStats] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [leadToDelete, setLeadToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [workflowOwnerId, setWorkflowOwnerId] = useState('');
  const [workflowStatus, setWorkflowStatus] = useState('');
  const [workflowNotes, setWorkflowNotes] = useState('');
  const [workflowDisqualificationReason, setWorkflowDisqualificationReason] = useState('');
  const [savingWorkflow, setSavingWorkflow] = useState(false);
  const [scoringData, setScoringData] = useState({
    icp_tier: '',
    engagement_score: '',
    company_size_fit: '',
    buying_role_strength: '',
    buying_role: '',
    job_title: '',
    industry: '',
    company_size: '',
    country: '',
    budget_range: '',
    authority_identified: '',
    use_case_defined: '',
    timeline_confirmed: '',
    discovery_notes: '',
    call_outcome: '',
  });
  const [savingScore, setSavingScore] = useState(false);
  const [showPushDialog, setShowPushDialog] = useState(false);
  const [pushForm, setPushForm] = useState({
    deal_name: '',
    amount: '',
    next_step_at: '',
    next_step_note: '',
    estimated_close_date: '',
    product_service_type: ''
  });
  const [pushingToSales, setPushingToSales] = useState(false);
  const [touchpointType, setTouchpointType] = useState('call');
  const [touchpointNotes, setTouchpointNotes] = useState('');
  const [loggingTouchpoint, setLoggingTouchpoint] = useState(false);
  const [newLead, setNewLead] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    company_name: '',
    country_region: '',
    source: 'manual',
    sales_motion_type: 'partnership_sales',
    partner_name: '',
    product_name: '',
    client_name: '',
    partner_commission_structure: '',
    product_category: '',
    score: 0,
    notes: '',
    owner_id: ''
  });

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [page, search, filterTier, filterStatus]);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      if (search) params.append('search', search);
      if (filterTier !== 'all') params.append('tier', filterTier);
      if (filterStatus !== 'all') params.append('status', filterStatus);

      const response = await api.get(`/leads?${params}`);
      setLeads(response.data.leads || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching leads:', error);
      toast.error(error?.response?.data?.detail || error?.message || 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/leads/stats/summary');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching lead stats:', error);
    }
  };

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const response = await api.get('/users');
      setUsers(response.data.users || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleExportLeads = async () => {
    try {
      const res = await api.get('/leads/export?format=hubspot', { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leads_export_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Leads exported');
    } catch (error) {
      console.error('Error exporting leads:', error);
      toast.error(error?.response?.data?.detail || 'Failed to export leads');
    }
  };

  const handleImportLeads = async () => {
    if (!importFile) {
      toast.error('Select a CSV file first');
      return;
    }

    setImporting(true);
    setImportResult(null);
    try {
      const form = new FormData();
      form.append('file', importFile);
      const res = await api.post('/leads/import?max_rows=5000', form, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setImportResult(res.data);
      toast.success(`Imported: ${res.data.created || 0} created, ${res.data.updated || 0} updated`);
      fetchLeads();
      fetchStats();
    } catch (error) {
      console.error('Error importing leads:', error);
      toast.error(error?.response?.data?.detail || 'Failed to import leads');
    } finally {
      setImporting(false);
    }
  };

  const handleLeadClick = async (lead) => {
    setShowDetailSheet(true);
    try {
      const response = await api.get(`/leads/${lead.id}`);
      const fullLead = response.data;
      setSelectedLead(fullLead);

      setWorkflowOwnerId(fullLead.owner_id || '');
      setWorkflowStatus(fullLead.status || 'new_assigned');
      setWorkflowNotes(fullLead.notes || '');
      setWorkflowDisqualificationReason(fullLead.disqualification_reason || '');

      const sd = fullLead.scoring_data || {};
      setScoringData({
        icp_tier: sd.icp_tier ?? '',
        engagement_score: sd.engagement_score ?? '',
        company_size_fit: sd.company_size_fit ?? '',
        buying_role_strength: sd.buying_role_strength ?? '',
        buying_role: sd.buying_role ?? '',
        job_title: sd.job_title ?? '',
        industry: sd.industry ?? '',
        company_size: sd.company_size ?? '',
        country: sd.country ?? fullLead.country_region ?? '',
        budget_range: sd.budget_range ?? '',
        authority_identified: sd.authority_identified ?? '',
        use_case_defined: sd.use_case_defined ?? '',
        timeline_confirmed: sd.timeline_confirmed ?? '',
        discovery_notes: sd.discovery_notes ?? fullLead.notes ?? '',
        call_outcome: sd.call_outcome ?? '',
      });

      setTouchpointType('call');
      setTouchpointNotes('');

      const defaultNextStep = toDateTimeLocal(new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString());
      const defaultCloseDate = toDateTimeLocal(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString());
      setPushForm({
        deal_name: (fullLead.company_name || fullLead.full_name || '').trim(),
        amount: '',
        next_step_at: defaultNextStep,
        next_step_note: '',
        estimated_close_date: defaultCloseDate,
        product_service_type: fullLead.product_name || fullLead.product_category || (fullLead.sales_motion_type === 'partner_sales' ? 'Partner Product' : 'Elev8 Services')
      });
    } catch (error) {
      console.error('Error fetching lead:', error);
      toast.error('Failed to load lead details');
      setSelectedLead(lead);
      setWorkflowOwnerId(lead.owner_id || '');
      setWorkflowStatus(lead.status || 'new_assigned');
      setWorkflowNotes(lead.notes || '');
      setWorkflowDisqualificationReason(lead.disqualification_reason || '');
      setScoringData({
        icp_tier: '',
        engagement_score: '',
        company_size_fit: '',
        buying_role_strength: '',
        buying_role: '',
        job_title: '',
        industry: '',
        company_size: '',
        country: lead.country_region || '',
        budget_range: '',
        authority_identified: '',
        use_case_defined: '',
        timeline_confirmed: '',
        discovery_notes: lead.notes || '',
        call_outcome: '',
      });
      const defaultNextStep = toDateTimeLocal(new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString());
      const defaultCloseDate = toDateTimeLocal(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString());
      setPushForm({
        deal_name: (lead.company_name || lead.full_name || '').trim(),
        amount: '',
        next_step_at: defaultNextStep,
        next_step_note: '',
        estimated_close_date: defaultCloseDate,
        product_service_type: lead.product_name || lead.product_category || (lead.sales_motion_type === 'partner_sales' ? 'Partner Product' : 'Elev8 Services')
      });
      setTouchpointType('call');
      setTouchpointNotes('');
    }
  };

  const closeDetailSheet = () => {
    setShowDetailSheet(false);
    setSelectedLead(null);
    setShowPushDialog(false);
  };

  const updateLeadInState = (updatedLead) => {
    if (!updatedLead?.id) return;
    setLeads(prev => prev.map(l => (l.id === updatedLead.id ? { ...l, ...updatedLead } : l)));
    setSelectedLead(prev => (prev && prev.id === updatedLead.id ? { ...prev, ...updatedLead } : prev));
  };

  const handleCreateLead = async () => {
    if (!newLead.first_name || !newLead.last_name) {
      toast.error('First name and last name are required');
      return;
    }
    if (!newLead.company_name?.trim()) {
      toast.error('Company name is required');
      return;
    }
    if (!newLead.country_region?.trim()) {
      toast.error('Country / region is required');
      return;
    }
    if (!newLead.source?.trim()) {
      toast.error('Lead source is required');
      return;
    }

    if (newLead.sales_motion_type === 'partner_sales') {
      if (!newLead.partner_name?.trim() || !newLead.product_name?.trim()) {
        toast.error('Partner name and partner product are required for Partner Sales');
        return;
      }
      if (!newLead.client_name?.trim() || !newLead.partner_commission_structure?.trim() || !newLead.product_category?.trim()) {
        toast.error('Client name, commission structure, and product category are required for Partner Sales');
        return;
      }
    }

    setCreating(true);
    try {
      const payload = { ...newLead };
      if (!payload.owner_id) delete payload.owner_id;
      await api.post('/leads', payload);
      toast.success('Lead created successfully');
      setShowCreateModal(false);
      setNewLead({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        company_name: '',
        country_region: '',
        source: 'manual',
        sales_motion_type: 'partnership_sales',
        partner_name: '',
        product_name: '',
        client_name: '',
        partner_commission_structure: '',
        product_category: '',
        score: 0,
        notes: '',
        owner_id: ''
      });
      fetchLeads();
      fetchStats();
    } catch (error) {
      console.error('Error creating lead:', error);
      toast.error(error?.response?.data?.detail || 'Failed to create lead');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteLead = async () => {
    if (!leadToDelete) return;

    setDeleting(true);
    try {
      await api.delete(`/leads/${leadToDelete.id}`);
      toast.success('Lead deleted successfully');
      setShowDeleteDialog(false);
      setLeadToDelete(null);
      if (showDetailSheet && selectedLead?.id === leadToDelete.id) {
        closeDetailSheet();
      }
      fetchLeads();
      fetchStats();
    } catch (error) {
      console.error('Error deleting lead:', error);
      toast.error('Failed to delete lead');
    } finally {
      setDeleting(false);
    }
  };

  const handleConvertLead = async (leadId) => {
    try {
      await api.post(`/leads/${leadId}/convert`);
      toast.success('Lead converted to contact successfully');
      closeDetailSheet();
      fetchLeads();
      fetchStats();
    } catch (error) {
      console.error('Error converting lead:', error);
      toast.error(error.response?.data?.detail || 'Failed to convert lead');
    }
  };

  const handleAssignLead = async () => {
    if (!selectedLead) return;
    if (!workflowOwnerId) {
      toast.error('Select an owner to assign');
      return;
    }

    try {
      const response = await api.post(`/leads/${selectedLead.id}/assign`, {
        owner_id: workflowOwnerId
      });
      updateLeadInState(response.data);
      setWorkflowStatus(response.data.status || workflowStatus);
      toast.success('Lead assigned');
      fetchStats();
    } catch (error) {
      console.error('Error assigning lead:', error);
      toast.error(error.response?.data?.detail || 'Failed to assign lead');
    }
  };

  const handleSaveWorkflow = async () => {
    if (!selectedLead) return;

    setSavingWorkflow(true);
    try {
      const workflowPayload = {
        status: workflowStatus,
        notes: workflowNotes
      };
      if (workflowStatus === 'disqualified') {
        workflowPayload.disqualification_reason = workflowDisqualificationReason?.trim() || null;
      }
      const response = await api.put(`/leads/${selectedLead.id}`, {
        ...workflowPayload
      });
      updateLeadInState(response.data);
      setWorkflowStatus(response.data.status || workflowStatus);
      setWorkflowNotes(response.data.notes || workflowNotes);
      setWorkflowDisqualificationReason(response.data.disqualification_reason || workflowDisqualificationReason || '');
      toast.success('Lead updated');
      fetchStats();
    } catch (error) {
      console.error('Error updating lead:', error);
      toast.error(error.response?.data?.detail || 'Failed to update lead');
    } finally {
      setSavingWorkflow(false);
    }
  };

  const handleSaveScore = async () => {
    if (!selectedLead) return;

    setSavingScore(true);
    try {
      const payload = {
        scoring_data: {
          icp_tier: scoringData.icp_tier,
          engagement_score: scoringData.engagement_score === '' ? null : Number(scoringData.engagement_score),
          company_size_fit: scoringData.company_size_fit,
          buying_role_strength: scoringData.buying_role_strength,
          buying_role: scoringData.buying_role,
          job_title: scoringData.job_title,
          industry: scoringData.industry,
          company_size: scoringData.company_size,
          country: scoringData.country,
          budget_range: scoringData.budget_range,
          authority_identified: scoringData.authority_identified,
          use_case_defined: scoringData.use_case_defined,
          timeline_confirmed: scoringData.timeline_confirmed,
          discovery_notes: scoringData.discovery_notes || workflowNotes || '',
          call_outcome: scoringData.call_outcome,
        }
      };

      const response = await api.post(`/leads/${selectedLead.id}/score`, payload);
      updateLeadInState(response.data);
      toast.success('Score updated');
      fetchStats();
    } catch (error) {
      console.error('Error scoring lead:', error);
      toast.error(error.response?.data?.detail || 'Failed to update score');
    } finally {
      setSavingScore(false);
    }
  };

  const handleLogTouchpoint = async () => {
    if (!selectedLead) return;

    setLoggingTouchpoint(true);
    try {
      const response = await api.post(`/leads/${selectedLead.id}/touchpoint`, {
        activity_type: touchpointType,
        notes: touchpointNotes || null,
        got_response: false,
      });
      updateLeadInState(response.data);
      setTouchpointNotes('');
      toast.success('Touchpoint logged');
      fetchStats();
    } catch (error) {
      console.error('Error logging touchpoint:', error);
      toast.error(error.response?.data?.detail || 'Failed to log touchpoint');
    } finally {
      setLoggingTouchpoint(false);
    }
  };

  const handlePushToSales = async () => {
    if (!selectedLead) return;
    const dealAmount = Number(pushForm.amount);
    if (pushForm.amount === '' || Number.isNaN(dealAmount) || dealAmount < 0) {
      toast.error('Estimated deal size is required');
      return;
    }
    if (!pushForm.next_step_at) {
      toast.error('Next step is required');
      return;
    }
    if (!pushForm.estimated_close_date) {
      toast.error('Estimated close date is required');
      return;
    }
    if (!pushForm.product_service_type?.trim()) {
      toast.error('Product / service type is required');
      return;
    }

    setPushingToSales(true);
    try {
      const response = await api.post(`/leads/${selectedLead.id}/push-to-sales`, {
        deal_name: pushForm.deal_name?.trim() || null,
        amount: dealAmount,
        next_step_at: fromDateTimeLocal(pushForm.next_step_at),
        next_step_note: pushForm.next_step_note?.trim() || null,
        estimated_close_date: fromDateTimeLocal(pushForm.estimated_close_date),
        product_service_type: pushForm.product_service_type?.trim(),
      });

      toast.success('Lead pushed to Sales Pipeline');
      setShowPushDialog(false);
      closeDetailSheet();
      await fetchLeads();
      await fetchStats();
      navigate('/pipeline');
      return response.data;
    } catch (error) {
      console.error('Error pushing lead to sales:', error);
      toast.error(error.response?.data?.detail || 'Failed to push lead to Sales Pipeline');
      return null;
    } finally {
      setPushingToSales(false);
    }
  };

  const getTierBadge = (tier) => {
    const colors = {
      'A': 'bg-green-500/20 text-green-400 border-green-500/30',
      'B': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      'C': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      'D': 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    return (
      <Badge className={`${colors[tier] || 'bg-gray-500/20 text-gray-400'} font-semibold`}>
        Tier {tier}
      </Badge>
    );
  };

  const getStatusBadge = (status) => {
    const colors = {
      'new': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      'assigned': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      'new_assigned': 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      'working': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      'info_collected': 'bg-sky-500/20 text-sky-400 border-sky-500/30',
      'nurture': 'bg-violet-500/20 text-violet-300 border-violet-500/30',
      'unresponsive': 'bg-gray-500/20 text-gray-300 border-gray-500/30',
      'qualified': 'bg-green-500/20 text-green-400 border-green-500/30',
      'converted': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      'disqualified': 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    return (
      <Badge className={colors[status] || 'bg-gray-500/20 text-gray-400'}>
        {(status || '').replace(/_/g, ' ')}
      </Badge>
    );
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-blue-500';
    if (score >= 40) return 'text-amber-500';
    return 'text-red-500';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
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

  const scoringInputsComplete = (sd) => {
    const required = [
      'icp_tier',
      'engagement_score',
      'company_size_fit',
      'buying_role_strength',
      'job_title',
      'buying_role',
      'industry',
      'company_size',
      'country',
      'budget_range',
      'authority_identified',
      'use_case_defined',
      'timeline_confirmed',
      'call_outcome',
    ];
    return required.every((key) => {
      const value = sd?.[key];
      return !(value === undefined || value === null || (typeof value === 'string' && value.trim() === ''));
    });
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Leads</h1>
          <p className="text-muted-foreground">{total} total leads</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => { fetchLeads(); fetchStats(); }}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Lead
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Users className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Leads</p>
                <p className="text-2xl font-bold">{stats?.total || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                <Star className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Tier A Leads</p>
                <p className="text-2xl font-bold">{stats?.by_tier?.A || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Avg. Score</p>
                <p className="text-2xl font-bold">{stats?.average_score || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Zap className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Converted</p>
                <p className="text-2xl font-bold">{stats?.by_status?.converted || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search leads by name, email, or company..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={filterTier} onValueChange={setFilterTier}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="All Tiers" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tiers</SelectItem>
                <SelectItem value="A">Tier A</SelectItem>
                <SelectItem value="B">Tier B</SelectItem>
                <SelectItem value="C">Tier C</SelectItem>
                <SelectItem value="D">Tier D</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                {LEAD_STATUS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
              <Button
                variant="outline"
                onClick={() => {
                  setImportResult(null);
                  setImportFile(null);
                  setShowImportModal(true);
                }}
              >
                <Upload className="w-4 h-4 mr-2" />
                Import
              </Button>
              <Button variant="outline" onClick={handleExportLeads}>
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>
          </CardContent>
        </Card>

      {/* Leads Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Lead</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Created</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                  </TableRow>
                ))
              ) : leads.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center py-12">
                    <div className="flex flex-col items-center gap-2">
                      <Target className="w-12 h-12 text-muted-foreground opacity-50" />
                      <p className="text-muted-foreground">No leads found</p>
                      <Button variant="outline" onClick={() => setShowCreateModal(true)}>
                        <Plus className="w-4 h-4 mr-2" />
                        Add Your First Lead
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                leads.map(lead => (
                  <TableRow
                    key={lead.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleLeadClick(lead)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <User className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{lead.full_name || `${lead.first_name} ${lead.last_name}`}</p>
                          {lead.owner_name && (
                            <p className="text-xs text-muted-foreground">Owner: {lead.owner_name}</p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Mail className="w-3 h-3 text-muted-foreground" />
                        {lead.email || '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Phone className="w-3 h-3 text-muted-foreground" />
                        {lead.phone || '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Building className="w-3 h-3 text-muted-foreground" />
                        {lead.company_name || '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className={`font-bold ${getScoreColor(lead.score)}`}>
                          {lead.score}
                        </span>
                        <Progress value={lead.score} className="w-16 h-2" />
                      </div>
                    </TableCell>
                    <TableCell>{getTierBadge(lead.tier)}</TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        {getStatusBadge(lead.status)}
                        {(lead.speed_to_lead_breached || lead.cadence_breached) && (
                          <div className="flex flex-wrap gap-1">
                            {lead.speed_to_lead_breached && (
                              <Badge className="bg-red-500/20 text-red-400 border-red-500/30">
                                Speed {lead.speed_to_lead_minutes ?? '-'}m
                              </Badge>
                            )}
                            {lead.cadence_breached && (
                              <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
                                Stale {lead.cadence_hours_since_touch ?? '-'}h
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground capitalize">
                      {lead.source || '-'}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(lead.created_at)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleLeadClick(lead); }}>
                            <Edit className="w-4 h-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          {lead.status === 'qualified' && (
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleConvertLead(lead.id); }}>
                              <ArrowRight className="w-4 h-4 mr-2" />
                              Convert to Contact Only
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-red-500"
                            onClick={(e) => {
                              e.stopPropagation();
                              setLeadToDelete(lead);
                              setShowDeleteDialog(true);
                            }}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <p className="text-sm text-muted-foreground">
                Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Lead Detail Sheet */}
      <Sheet
        open={showDetailSheet}
        onOpenChange={(open) => {
          if (!open) closeDetailSheet();
          else setShowDetailSheet(true);
        }}
      >
        <SheetContent className="w-full sm:max-w-lg p-0 flex flex-col">
          {selectedLead && (
            <>
              <SheetHeader className="p-6 border-b">
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="w-8 h-8 text-primary" />
                  </div>
                  <div className="flex-1">
                    <SheetTitle className="text-xl">{selectedLead.full_name}</SheetTitle>
                    <SheetDescription className="flex items-center gap-2 mt-1">
                      {selectedLead.company_name && (
                        <span className="flex items-center gap-1">
                          <Building className="w-4 h-4" />
                          {selectedLead.company_name}
                        </span>
                      )}
                    </SheetDescription>
                    <div className="flex gap-2 mt-3">
                      {getTierBadge(selectedLead.tier)}
                      {getStatusBadge(selectedLead.status)}
                    </div>
                  </div>
                </div>
              </SheetHeader>

              <ScrollArea className="flex-1 p-6">
                <div className="space-y-6">
                  {/* Score Section */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Lead Score</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-4">
                        <div className={`text-4xl font-bold ${getScoreColor(selectedLead.score)}`}>
                          {selectedLead.score}
                        </div>
                        <div className="flex-1">
                          <Progress value={selectedLead.score} className="h-3" />
                          <p className="text-xs text-muted-foreground mt-1">
                            {selectedLead.score >= 80 ? 'Hot Lead' :
                             selectedLead.score >= 60 ? 'Warm Lead' :
                             selectedLead.score >= 40 ? 'Cool Lead' : 'Cold Lead'}
                          </p>
                        </div>
                      </div>
                      <div className="mt-3 text-xs text-muted-foreground">
                        Scoring inputs {scoringInputsComplete(scoringData) ? 'complete' : 'incomplete'}.
                        {' '}Required before moving to <span className="font-medium">Info Collected</span> or <span className="font-medium">Qualified</span>.
                      </div>
                    </CardContent>
                  </Card>

                  {/* Workflow */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Workflow</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Owner</Label>
                          <Select
                            value={workflowOwnerId || 'unassigned'}
                            onValueChange={(v) => setWorkflowOwnerId(v === 'unassigned' ? '' : v)}
                            disabled={loadingUsers || selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
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
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={handleAssignLead}
                            disabled={!workflowOwnerId || selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <UserPlus className="w-4 h-4 mr-2" />
                            Assign
                          </Button>
                        </div>

                        <div className="space-y-2">
                          <Label>Status</Label>
                          <Select
                            value={workflowStatus || selectedLead.status || 'new_assigned'}
                            onValueChange={setWorkflowStatus}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {LEAD_STATUS_OPTIONS.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <div className="text-xs text-muted-foreground">
                            Stage rules are enforced: Info Collected requires call outcome + discovery + next step task; Qualified requires budget, authority, use case, timeline, and complete scoring.
                          </div>
                        </div>
                      </div>

                      {workflowStatus === 'disqualified' && (
                        <div className="space-y-2">
                          <Label>Disqualification Reason <span className="text-red-500">*</span></Label>
                          <Input
                            value={workflowDisqualificationReason}
                            onChange={(e) => setWorkflowDisqualificationReason(e.target.value)}
                            placeholder="e.g. No budget, not ICP, no authority"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                      )}

                      <div className="rounded-lg border p-4 space-y-3">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-sm font-medium">Touchpoints</p>
                            <p className="text-xs text-muted-foreground">
                              {(selectedLead.touchpoints_count || 0)} logged • Last: {formatDateTime(selectedLead.last_touchpoint_at)}
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <Badge
                              className={selectedLead.speed_to_lead_breached
                                ? "bg-red-500/20 text-red-400 border-red-500/30 whitespace-nowrap"
                                : "bg-green-500/20 text-green-400 border-green-500/30 whitespace-nowrap"}
                            >
                              Speed {selectedLead.speed_to_lead_minutes ?? '-'}m
                            </Badge>
                            <Badge
                              className={selectedLead.cadence_breached
                                ? "bg-amber-500/20 text-amber-400 border-amber-500/30 whitespace-nowrap"
                                : "bg-blue-500/20 text-blue-400 border-blue-500/30 whitespace-nowrap"}
                            >
                              Cadence {selectedLead.cadence_hours_since_touch ?? '-'}h
                            </Badge>
                            <Badge variant="outline" className="whitespace-nowrap">
                              Min 3 before Unresponsive
                            </Badge>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-2">
                            <Label>Type</Label>
                            <Select
                              value={touchpointType}
                              onValueChange={setTouchpointType}
                              disabled={loggingTouchpoint || selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="call">Call</SelectItem>
                                <SelectItem value="email">Email</SelectItem>
                                <SelectItem value="sms">SMS</SelectItem>
                                <SelectItem value="meeting">Meeting</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-2">
                            <Label>Notes (optional)</Label>
                            <Input
                              value={touchpointNotes}
                              onChange={(e) => setTouchpointNotes(e.target.value)}
                              placeholder="e.g. Left voicemail"
                              disabled={loggingTouchpoint || selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                            />
                          </div>
                        </div>

                        <Button
                          variant="outline"
                          onClick={handleLogTouchpoint}
                          disabled={loggingTouchpoint || selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          className="w-full"
                        >
                          {loggingTouchpoint ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Logging...
                            </>
                          ) : (
                            'Log Touchpoint'
                          )}
                        </Button>
                      </div>

                      <div className="space-y-2">
                        <Label>Notes</Label>
                        <Textarea
                          value={workflowNotes}
                          onChange={(e) => setWorkflowNotes(e.target.value)}
                          rows={3}
                          disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        />
                      </div>

                      <Button
                        onClick={handleSaveWorkflow}
                        disabled={savingWorkflow || selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        className="w-full"
                      >
                        {savingWorkflow ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          'Save Changes'
                        )}
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Scoring Inputs */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Scoring Inputs</CardTitle>
                      <CardDescription>
                        Product-agnostic, required for Info Collected / Qualified.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>ICP Tier *</Label>
                          <Select
                            value={scoringData.icp_tier || ''}
                            onValueChange={(v) => setScoringData({ ...scoringData, icp_tier: v })}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select ICP tier" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="A">A</SelectItem>
                              <SelectItem value="B">B</SelectItem>
                              <SelectItem value="C">C</SelectItem>
                              <SelectItem value="D">D</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Engagement Score (0-30) *</Label>
                          <Input
                            type="number"
                            min={0}
                            max={30}
                            value={scoringData.engagement_score}
                            onChange={(e) => setScoringData({ ...scoringData, engagement_score: e.target.value })}
                            placeholder="0-30"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Company Size Fit *</Label>
                          <Select
                            value={scoringData.company_size_fit || ''}
                            onValueChange={(v) => setScoringData({ ...scoringData, company_size_fit: v })}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select fit" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="ideal">Ideal</SelectItem>
                              <SelectItem value="strong">Strong</SelectItem>
                              <SelectItem value="medium">Medium</SelectItem>
                              <SelectItem value="low">Low</SelectItem>
                              <SelectItem value="poor">Poor</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Buying Role Strength *</Label>
                          <Select
                            value={scoringData.buying_role_strength || ''}
                            onValueChange={(v) => setScoringData({ ...scoringData, buying_role_strength: v })}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select strength" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="strong">Strong</SelectItem>
                              <SelectItem value="medium">Medium</SelectItem>
                              <SelectItem value="low">Low</SelectItem>
                              <SelectItem value="poor">Poor</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Job Title *</Label>
                          <Input
                            value={scoringData.job_title}
                            onChange={(e) => setScoringData({ ...scoringData, job_title: e.target.value })}
                            placeholder="e.g. Operations Director"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Buying Role *</Label>
                          <Select
                            value={scoringData.buying_role || ''}
                            onValueChange={(v) => setScoringData({ ...scoringData, buying_role: v })}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select role" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="decision_maker">Decision Maker</SelectItem>
                              <SelectItem value="champion">Champion</SelectItem>
                              <SelectItem value="influencer">Influencer</SelectItem>
                              <SelectItem value="technical">Technical</SelectItem>
                              <SelectItem value="finance">Finance</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label>Industry *</Label>
                          <Input
                            value={scoringData.industry}
                            onChange={(e) => setScoringData({ ...scoringData, industry: e.target.value })}
                            placeholder="Industry"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Company Size *</Label>
                          <Input
                            value={scoringData.company_size}
                            onChange={(e) => setScoringData({ ...scoringData, company_size: e.target.value })}
                            placeholder="e.g. 50-200"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Country *</Label>
                          <Input
                            value={scoringData.country}
                            onChange={(e) => setScoringData({ ...scoringData, country: e.target.value })}
                            placeholder="Country"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label>Budget Range *</Label>
                          <Input
                            value={scoringData.budget_range}
                            onChange={(e) => setScoringData({ ...scoringData, budget_range: e.target.value })}
                            placeholder="e.g. $15k-$30k"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Authority Identified *</Label>
                          <Input
                            value={scoringData.authority_identified}
                            onChange={(e) => setScoringData({ ...scoringData, authority_identified: e.target.value })}
                            placeholder="Who approves?"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Use Case Defined *</Label>
                          <Input
                            value={scoringData.use_case_defined}
                            onChange={(e) => setScoringData({ ...scoringData, use_case_defined: e.target.value })}
                            placeholder="Use case"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Timeline Confirmed *</Label>
                          <Input
                            value={scoringData.timeline_confirmed}
                            onChange={(e) => setScoringData({ ...scoringData, timeline_confirmed: e.target.value })}
                            placeholder="e.g. Q2 close"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label>Call Outcome *</Label>
                        <Input
                          value={scoringData.call_outcome}
                          onChange={(e) => setScoringData({ ...scoringData, call_outcome: e.target.value })}
                          placeholder="Latest call outcome summary"
                          disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Discovery Notes</Label>
                        <Textarea
                          value={scoringData.discovery_notes}
                          onChange={(e) => setScoringData({ ...scoringData, discovery_notes: e.target.value })}
                          rows={3}
                          placeholder="Discovery notes used for Working -> Information Collected"
                          disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        />
                      </div>

                      <Button
                        onClick={handleSaveScore}
                        disabled={savingScore || selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        className="w-full"
                      >
                        {savingScore ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Computing...
                          </>
                        ) : (
                          'Compute Score'
                        )}
                      </Button>

                      {!scoringInputsComplete(scoringData) && (
                        <p className="text-xs text-amber-600">
                          Complete all required fields (*) before moving to Info Collected / Qualified.
                        </p>
                      )}
                    </CardContent>
                  </Card>

                  {/* Contact Info */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Contact Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center gap-3">
                        <Mail className="w-4 h-4 text-muted-foreground" />
                        <span>{selectedLead.email || 'No email'}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Phone className="w-4 h-4 text-muted-foreground" />
                        <span>{selectedLead.phone || 'No phone'}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <Building className="w-4 h-4 text-muted-foreground" />
                        <span>{selectedLead.company_name || 'No company'}</span>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Details */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Details</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label className="text-xs text-muted-foreground">Source</Label>
                          <p className="font-medium capitalize">{selectedLead.source || '-'}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Owner</Label>
                          <p className="font-medium">{selectedLead.owner_name || 'Unassigned'}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Country / Region</Label>
                          <p className="font-medium">{selectedLead.country_region || '-'}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Sales Motion</Label>
                          <p className="font-medium">
                            {selectedLead.sales_motion_type === 'partner_sales'
                              ? 'Partner Sales'
                              : 'Partnership Sales'}
                          </p>
                        </div>
                        {selectedLead.sales_motion_type === 'partner_sales' ? (
                          <div>
                            <Label className="text-xs text-muted-foreground">Partner</Label>
                            <p className="font-medium">{selectedLead.partner_name || '-'}</p>
                          </div>
                        ) : (
                          <div>
                            <Label className="text-xs text-muted-foreground">Partner</Label>
                            <p className="font-medium">-</p>
                          </div>
                        )}
                        <div>
                          <Label className="text-xs text-muted-foreground">Product</Label>
                          <p className="font-medium">
                            {selectedLead.sales_motion_type === 'partner_sales'
                              ? (selectedLead.product_name || '-')
                              : '-'}
                          </p>
                        </div>
                        {selectedLead.sales_motion_type === 'partner_sales' && (
                          <>
                            <div>
                              <Label className="text-xs text-muted-foreground">Client</Label>
                              <p className="font-medium">{selectedLead.client_name || '-'}</p>
                            </div>
                            <div>
                              <Label className="text-xs text-muted-foreground">Commission</Label>
                              <p className="font-medium">{selectedLead.partner_commission_structure || '-'}</p>
                            </div>
                            <div>
                              <Label className="text-xs text-muted-foreground">Product Category</Label>
                              <p className="font-medium">{selectedLead.product_category || '-'}</p>
                            </div>
                          </>
                        )}
                        <div>
                          <Label className="text-xs text-muted-foreground">Created</Label>
                          <p className="font-medium">{formatDate(selectedLead.created_at)}</p>
                        </div>
                        <div>
                          <Label className="text-xs text-muted-foreground">Assigned</Label>
                          <p className="font-medium">{formatDate(selectedLead.assigned_at)}</p>
                        </div>
                      </div>
                      {selectedLead.notes && (
                        <div>
                          <Label className="text-xs text-muted-foreground">Notes</Label>
                          <p className="text-sm mt-1">{selectedLead.notes}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </ScrollArea>

              <div className="p-4 border-t flex gap-2">
                <Button variant="outline" className="flex-1" onClick={closeDetailSheet}>
                  Close
                </Button>
                {selectedLead.status === 'qualified' && (
                  <Button onClick={() => setShowPushDialog(true)}>
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Push to Sales Pipeline
                  </Button>
                )}
                {selectedLead.status === 'qualified' && (
                  <Button onClick={() => handleConvertLead(selectedLead.id)}>
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Convert to Contact Only
                  </Button>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Push to Sales Dialog */}
      <Dialog open={showPushDialog} onOpenChange={setShowPushDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Push to Sales Pipeline</DialogTitle>
            <DialogDescription>
              Creates a Contact (if needed) and a Deal in the default Sales pipeline.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Deal Name</Label>
              <Input
                value={pushForm.deal_name}
                onChange={(e) => setPushForm({ ...pushForm, deal_name: e.target.value })}
                placeholder="Deal name"
              />
            </div>

            <div className="space-y-2">
              <Label>Estimated Deal Size <span className="text-red-500">*</span></Label>
              <Input
                type="number"
                value={pushForm.amount}
                onChange={(e) => setPushForm({ ...pushForm, amount: e.target.value })}
                placeholder="0.00"
                step="0.01"
              />
            </div>

            <div className="space-y-2">
              <Label>Next Step <span className="text-red-500">*</span></Label>
              <Input
                type="datetime-local"
                value={pushForm.next_step_at}
                onChange={(e) => setPushForm({ ...pushForm, next_step_at: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Estimated Close Date <span className="text-red-500">*</span></Label>
              <Input
                type="datetime-local"
                value={pushForm.estimated_close_date}
                onChange={(e) => setPushForm({ ...pushForm, estimated_close_date: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>Product / Service Type <span className="text-red-500">*</span></Label>
              <Input
                value={pushForm.product_service_type}
                onChange={(e) => setPushForm({ ...pushForm, product_service_type: e.target.value })}
                placeholder="e.g. Elev8 Services, Partner Product"
              />
            </div>

            <div className="space-y-2">
              <Label>Next Step Note</Label>
              <Textarea
                value={pushForm.next_step_note}
                onChange={(e) => setPushForm({ ...pushForm, next_step_note: e.target.value })}
                placeholder="What is the next action?"
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPushDialog(false)} disabled={pushingToSales}>
              Cancel
            </Button>
            <Button
              onClick={handlePushToSales}
              disabled={
                pushingToSales
                || pushForm.amount === ''
                || Number.isNaN(Number(pushForm.amount))
                || Number(pushForm.amount) < 0
                || !pushForm.next_step_at
                || !pushForm.estimated_close_date
                || !pushForm.product_service_type?.trim()
              }
            >
              {pushingToSales ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Pushing...
                </>
              ) : (
                'Create Deal'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
        </Dialog>

        {/* Import Leads Modal */}
        <Dialog
          open={showImportModal}
          onOpenChange={(open) => {
            setShowImportModal(open);
            if (!open) {
              setImportFile(null);
              setImportResult(null);
            }
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Import Leads (CSV)</DialogTitle>
              <DialogDescription>
                Import leads from a HubSpot CSV export (or a standard CSV). Minimum required: Email or Phone, Company, and Country/Region.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label>CSV file</Label>
                <Input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                />
                <p className="text-xs text-muted-foreground">
                  Tip: Include scoring columns (ICP Tier, Engagement Score, Company Size Fit, Buying Role Strength) to auto-compute Lead Score/Tier.
                </p>
              </div>

              {importResult && (
                <div className="rounded-lg border p-4 space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium">Import results</p>
                    <Badge variant="secondary">
                      {(importResult.created || 0) + (importResult.updated || 0)} processed
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div><span className="text-muted-foreground">Created:</span> {importResult.created || 0}</div>
                    <div><span className="text-muted-foreground">Updated:</span> {importResult.updated || 0}</div>
                    <div><span className="text-muted-foreground">Skipped:</span> {importResult.skipped || 0}</div>
                  </div>

                  {importResult.errors?.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Errors (first {importResult.errors.length})</p>
                      <ScrollArea className="h-36 rounded border p-2">
                        <div className="space-y-1 text-xs">
                          {importResult.errors.map((e, idx) => (
                            <div key={idx} className="text-muted-foreground">
                              Row {e.row}: {e.error}
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </div>
                  )}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowImportModal(false)} disabled={importing}>
                Close
              </Button>
              <Button onClick={handleImportLeads} disabled={importing || !importFile}>
                {importing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Importing...
                  </>
                ) : (
                  'Import'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Create Lead Modal */}
        <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Lead</DialogTitle>
            <DialogDescription>
              Create a new lead to track in your pipeline
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>First Name *</Label>
                <Input
                  value={newLead.first_name}
                  onChange={(e) => setNewLead({ ...newLead, first_name: e.target.value })}
                  placeholder="John"
                />
              </div>
              <div className="space-y-2">
                <Label>Last Name *</Label>
                <Input
                  value={newLead.last_name}
                  onChange={(e) => setNewLead({ ...newLead, last_name: e.target.value })}
                  placeholder="Doe"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={newLead.email}
                onChange={(e) => setNewLead({ ...newLead, email: e.target.value })}
                placeholder="john@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input
                value={newLead.phone}
                onChange={(e) => setNewLead({ ...newLead, phone: e.target.value })}
                placeholder="+1 (555) 123-4567"
              />
            </div>
            <div className="space-y-2">
              <Label>Company <span className="text-red-500">*</span></Label>
              <Input
                value={newLead.company_name}
                onChange={(e) => setNewLead({ ...newLead, company_name: e.target.value })}
                placeholder="Acme Inc."
              />
            </div>
            <div className="space-y-2">
              <Label>Country / Region <span className="text-red-500">*</span></Label>
              <Input
                value={newLead.country_region}
                onChange={(e) => setNewLead({ ...newLead, country_region: e.target.value })}
                placeholder="e.g. United States"
              />
            </div>
            <div className="space-y-2">
              <Label>Owner</Label>
              <Select
                value={newLead.owner_id || 'unassigned'}
                onValueChange={(v) => setNewLead({ ...newLead, owner_id: v === 'unassigned' ? '' : v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Unassigned" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unassigned">Unassigned</SelectItem>
                  {users.map(u => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.first_name} {u.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Sales Motion Type *</Label>
              <Select
                value={newLead.sales_motion_type}
                onValueChange={(v) => setNewLead({ ...newLead, sales_motion_type: v })}
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
            {newLead.sales_motion_type === 'partner_sales' && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Partner Name *</Label>
                  <Input
                    value={newLead.partner_name}
                    onChange={(e) => setNewLead({ ...newLead, partner_name: e.target.value })}
                    placeholder="Partner"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Partner Product *</Label>
                  <Input
                    value={newLead.product_name}
                    onChange={(e) => setNewLead({ ...newLead, product_name: e.target.value })}
                    placeholder="Product"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Client Name *</Label>
                  <Input
                    value={newLead.client_name}
                    onChange={(e) => setNewLead({ ...newLead, client_name: e.target.value })}
                    placeholder="Client this deal belongs to"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Commission Structure *</Label>
                  <Input
                    value={newLead.partner_commission_structure}
                    onChange={(e) => setNewLead({ ...newLead, partner_commission_structure: e.target.value })}
                    placeholder="e.g. 12% of net"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Product Category *</Label>
                  <Input
                    value={newLead.product_category}
                    onChange={(e) => setNewLead({ ...newLead, product_category: e.target.value })}
                    placeholder="e.g. Hardware"
                  />
                </div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Source <span className="text-red-500">*</span></Label>
                <Select
                  value={newLead.source}
                  onValueChange={(v) => setNewLead({ ...newLead, source: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual</SelectItem>
                    <SelectItem value="inbound_form">Inbound (Form)</SelectItem>
                    <SelectItem value="affiliate">Inbound (Affiliate)</SelectItem>
                    <SelectItem value="ads">Inbound (Ads)</SelectItem>
                    <SelectItem value="outbound">Outbound</SelectItem>
                    <SelectItem value="referral">Referral / Partner</SelectItem>
                    <SelectItem value="event">Event / Trade Show</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Initial Score (0-100)</Label>
                <Input
                  type="number"
                  min={0}
                  max={100}
                  value={newLead.score}
                  onChange={(e) => setNewLead({ ...newLead, score: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={newLead.notes}
                onChange={(e) => setNewLead({ ...newLead, notes: e.target.value })}
                placeholder="Any initial notes about this lead..."
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button onClick={handleCreateLead} disabled={creating}>
              {creating ? 'Creating...' : 'Create Lead'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Lead</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{leadToDelete?.full_name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteLead} disabled={deleting}>
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LeadsPage;
