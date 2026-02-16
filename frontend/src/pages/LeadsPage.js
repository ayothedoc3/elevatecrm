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
  const [savingWorkflow, setSavingWorkflow] = useState(false);
  const [scoringData, setScoringData] = useState({
    economic_units: '',
    usage_volume: '',
    urgency: '3',
    trigger_event: '',
    primary_motivation: '',
    decision_role: 'decision_maker',
    decision_process_clarity: '3',
  });
  const [savingScore, setSavingScore] = useState(false);
  const [showPushDialog, setShowPushDialog] = useState(false);
  const [pushForm, setPushForm] = useState({
    deal_name: '',
    amount: '',
    next_step_at: '',
    next_step_note: ''
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
    source: 'manual',
    sales_motion_type: 'partnership_sales',
    partner_name: '',
    product_name: '',
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
      setWorkflowStatus(fullLead.status || 'new');
      setWorkflowNotes(fullLead.notes || '');

      const sd = fullLead.scoring_data || {};
      setScoringData({
        economic_units: sd.economic_units ?? '',
        usage_volume: sd.usage_volume ?? '',
        urgency: String(sd.urgency ?? '3'),
        trigger_event: sd.trigger_event ?? '',
        primary_motivation: sd.primary_motivation ?? '',
        decision_role: sd.decision_role ?? 'decision_maker',
        decision_process_clarity: String(sd.decision_process_clarity ?? '3'),
      });

      setTouchpointType('call');
      setTouchpointNotes('');

      const defaultNextStep = toDateTimeLocal(new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString());
      setPushForm({
        deal_name: (fullLead.company_name || fullLead.full_name || '').trim(),
        amount: '',
        next_step_at: defaultNextStep,
        next_step_note: ''
      });
    } catch (error) {
      console.error('Error fetching lead:', error);
      toast.error('Failed to load lead details');
      setSelectedLead(lead);
      setWorkflowOwnerId(lead.owner_id || '');
      setWorkflowStatus(lead.status || 'new');
      setWorkflowNotes(lead.notes || '');
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

    if (newLead.sales_motion_type === 'partner_sales') {
      if (!newLead.partner_name?.trim() || !newLead.product_name?.trim()) {
        toast.error('Partner name and partner product are required for Partner Sales');
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
        source: 'manual',
        sales_motion_type: 'partnership_sales',
        partner_name: '',
        product_name: '',
        score: 0,
        notes: '',
        owner_id: ''
      });
      fetchLeads();
      fetchStats();
    } catch (error) {
      console.error('Error creating lead:', error);
      toast.error('Failed to create lead');
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
      const response = await api.put(`/leads/${selectedLead.id}`, {
        status: workflowStatus,
        notes: workflowNotes
      });
      updateLeadInState(response.data);
      setWorkflowStatus(response.data.status || workflowStatus);
      setWorkflowNotes(response.data.notes || workflowNotes);
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
          economic_units: scoringData.economic_units,
          usage_volume: scoringData.usage_volume,
          urgency: Number(scoringData.urgency),
          trigger_event: scoringData.trigger_event,
          primary_motivation: scoringData.primary_motivation,
          decision_role: scoringData.decision_role,
          decision_process_clarity: Number(scoringData.decision_process_clarity),
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
    if (!pushForm.next_step_at) {
      toast.error('Next step is required');
      return;
    }

    setPushingToSales(true);
    try {
      const response = await api.post(`/leads/${selectedLead.id}/push-to-sales`, {
        deal_name: pushForm.deal_name?.trim() || null,
        amount: parseFloat(pushForm.amount) || 0,
        next_step_at: fromDateTimeLocal(pushForm.next_step_at),
        next_step_note: pushForm.next_step_note?.trim() || null,
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
      'working': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      'info_collected': 'bg-sky-500/20 text-sky-400 border-sky-500/30',
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
      'economic_units',
      'usage_volume',
      'urgency',
      'trigger_event',
      'primary_motivation',
      'decision_role',
      'decision_process_clarity',
    ];
    return required.every((key) => {
      const value = sd?.[key];
      if (value === undefined || value === null) return false;
      if (typeof value === 'string') return value.trim() !== '';
      return true;
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
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="assigned">Assigned</SelectItem>
                <SelectItem value="working">Working</SelectItem>
                <SelectItem value="info_collected">Info Collected</SelectItem>
                <SelectItem value="unresponsive">Unresponsive</SelectItem>
                <SelectItem value="disqualified">Disqualified</SelectItem>
                <SelectItem value="qualified">Qualified</SelectItem>
                <SelectItem value="converted">Converted</SelectItem>
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
                          {lead.status !== 'converted' && (
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleConvertLead(lead.id); }}>
                              <ArrowRight className="w-4 h-4 mr-2" />
                              Convert to Contact
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
                            value={workflowStatus || selectedLead.status || 'new'}
                            onValueChange={setWorkflowStatus}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="new">New / Assigned</SelectItem>
                              <SelectItem value="assigned">Assigned</SelectItem>
                              <SelectItem value="working">Working</SelectItem>
                              <SelectItem value="info_collected">Info Collected</SelectItem>
                              <SelectItem value="unresponsive">Unresponsive</SelectItem>
                              <SelectItem value="disqualified">Disqualified</SelectItem>
                              <SelectItem value="qualified">Qualified</SelectItem>
                              <SelectItem value="converted">Converted</SelectItem>
                            </SelectContent>
                          </Select>
                          <div className="text-xs text-muted-foreground">
                            Note: moving to Info Collected / Qualified requires scoring inputs.
                          </div>
                        </div>
                      </div>

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
                          <Label>Economic Units *</Label>
                          <Input
                            type="number"
                            value={scoringData.economic_units}
                            onChange={(e) => setScoringData({ ...scoringData, economic_units: e.target.value })}
                            placeholder="e.g. locations, sites, licenses"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Usage Volume *</Label>
                          <Input
                            type="number"
                            value={scoringData.usage_volume}
                            onChange={(e) => setScoringData({ ...scoringData, usage_volume: e.target.value })}
                            placeholder="e.g. units, users, lines"
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Urgency (1-5) *</Label>
                          <Select
                            value={String(scoringData.urgency)}
                            onValueChange={(v) => setScoringData({ ...scoringData, urgency: v })}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="1">1</SelectItem>
                              <SelectItem value="2">2</SelectItem>
                              <SelectItem value="3">3</SelectItem>
                              <SelectItem value="4">4</SelectItem>
                              <SelectItem value="5">5</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label>Decision Process Clarity (1-5) *</Label>
                          <Select
                            value={String(scoringData.decision_process_clarity)}
                            onValueChange={(v) => setScoringData({ ...scoringData, decision_process_clarity: v })}
                            disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="1">1</SelectItem>
                              <SelectItem value="2">2</SelectItem>
                              <SelectItem value="3">3</SelectItem>
                              <SelectItem value="4">4</SelectItem>
                              <SelectItem value="5">5</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label>Trigger Event *</Label>
                        <Input
                          value={scoringData.trigger_event}
                          onChange={(e) => setScoringData({ ...scoringData, trigger_event: e.target.value })}
                          placeholder="What's happening now that creates urgency?"
                          disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Primary Motivation *</Label>
                        <Input
                          value={scoringData.primary_motivation}
                          onChange={(e) => setScoringData({ ...scoringData, primary_motivation: e.target.value })}
                          placeholder="e.g. cost savings, growth, efficiency"
                          disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label>Decision Role *</Label>
                        <Select
                          value={scoringData.decision_role || 'decision_maker'}
                          onValueChange={(v) => setScoringData({ ...scoringData, decision_role: v })}
                          disabled={selectedLead.status === 'converted' || selectedLead.status === 'disqualified'}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="decision_maker">Decision Maker</SelectItem>
                            <SelectItem value="owner">Owner / Founder</SelectItem>
                            <SelectItem value="influencer">Influencer / Champion</SelectItem>
                            <SelectItem value="manager">Manager / Director</SelectItem>
                            <SelectItem value="researcher">Researcher</SelectItem>
                          </SelectContent>
                        </Select>
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
                {selectedLead.status !== 'converted' && selectedLead.status !== 'qualified' && (
                  <Button onClick={() => handleConvertLead(selectedLead.id)}>
                    <ArrowRight className="w-4 h-4 mr-2" />
                    Convert to Contact
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
              <Label>Estimated Deal Size</Label>
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
            <Button onClick={handlePushToSales} disabled={pushingToSales || !pushForm.next_step_at}>
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
                Import leads from a HubSpot CSV export (or a standard CSV). Minimum required: Email or Phone.
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
                  Tip: Include scoring columns (Economic Units, Usage Volume, Urgency, Trigger Event, Primary Motivation, Decision Role, Decision
                  Process Clarity) to auto-compute Lead Score/Tier.
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
              <Label>Company</Label>
              <Input
                value={newLead.company_name}
                onChange={(e) => setNewLead({ ...newLead, company_name: e.target.value })}
                placeholder="Acme Inc."
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
                    placeholder="Partner (e.g. Frylow)"
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
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Source</Label>
                <Select
                  value={newLead.source}
                  onValueChange={(v) => setNewLead({ ...newLead, source: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual</SelectItem>
                    <SelectItem value="web">Website</SelectItem>
                    <SelectItem value="referral">Referral</SelectItem>
                    <SelectItem value="cold_call">Cold Call</SelectItem>
                    <SelectItem value="email">Email Campaign</SelectItem>
                    <SelectItem value="social">Social Media</SelectItem>
                    <SelectItem value="event">Event</SelectItem>
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
