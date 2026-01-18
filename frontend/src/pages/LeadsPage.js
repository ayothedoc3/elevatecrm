import React, { useState, useEffect } from 'react';
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
  ChevronLeft, ChevronRight, Filter, Download, Target, RefreshCw,
  TrendingUp, Users, Zap, Star, Edit, Trash2, UserPlus, ArrowRight
} from 'lucide-react';
import { toast } from 'sonner';

const LeadsPage = () => {
  const { api } = useAuth();
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
  const [selectedLead, setSelectedLead] = useState(null);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  const [stats, setStats] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [leadToDelete, setLeadToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [newLead, setNewLead] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    company_name: '',
    source: 'manual',
    score: 50,
    notes: ''
  });

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [page, search, filterTier, filterStatus]);

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
      toast.error('Failed to load leads');
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

  const handleLeadClick = (lead) => {
    setSelectedLead(lead);
    setShowDetailSheet(true);
  };

  const closeDetailSheet = () => {
    setShowDetailSheet(false);
    setSelectedLead(null);
  };

  const handleCreateLead = async () => {
    if (!newLead.first_name || !newLead.last_name) {
      toast.error('First name and last name are required');
      return;
    }

    setCreating(true);
    try {
      await api.post('/leads', newLead);
      toast.success('Lead created successfully');
      setShowCreateModal(false);
      setNewLead({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        company_name: '',
        source: 'manual',
        score: 50,
        notes: ''
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
      'qualified': 'bg-green-500/20 text-green-400 border-green-500/30',
      'converted': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      'disqualified': 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    return (
      <Badge className={colors[status] || 'bg-gray-500/20 text-gray-400'}>
        {status}
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
                <SelectItem value="qualified">Qualified</SelectItem>
                <SelectItem value="converted">Converted</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
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
                    <TableCell>{getStatusBadge(lead.status)}</TableCell>
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
      <Sheet open={showDetailSheet} onOpenChange={setShowDetailSheet}>
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
                {selectedLead.status !== 'converted' && (
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
