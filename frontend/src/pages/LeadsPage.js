import React, { useState, useEffect } from 'react';
import {
  Users, Search, Plus, Filter, ChevronLeft, ChevronRight,
  Building, Phone, Mail, Target, TrendingUp, Star, Clock,
  MoreHorizontal, Edit, Trash2, CheckCircle, XCircle,
  ArrowRight, Zap, AlertCircle, UserPlus, RefreshCw, Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
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
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../components/ui/dropdown-menu';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useToast } from '../hooks/use-toast';
import { useAuth } from '../contexts/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Tier badge colors
const tierColors = {
  A: 'bg-green-500 text-white',
  B: 'bg-blue-500 text-white',
  C: 'bg-yellow-500 text-black',
  D: 'bg-gray-400 text-white'
};

const tierDescriptions = {
  A: 'Priority Account (80-100)',
  B: 'Strategic (60-79)',
  C: 'Standard (40-59)',
  D: 'Nurture Only (0-39)'
};

const statusColors = {
  new: 'bg-blue-100 text-blue-800',
  assigned: 'bg-purple-100 text-purple-800',
  working: 'bg-yellow-100 text-yellow-800',
  info_collected: 'bg-indigo-100 text-indigo-800',
  unresponsive: 'bg-gray-100 text-gray-800',
  disqualified: 'bg-red-100 text-red-800',
  qualified: 'bg-green-100 text-green-800'
};

const LeadsPage = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [filterTier, setFilterTier] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterMotion, setFilterMotion] = useState('all');
  
  // Partners and Products for dropdowns
  const [partners, setPartners] = useState([]);
  const [products, setProducts] = useState([]);
  
  // Scoring stats
  const [scoringStats, setScoringStats] = useState(null);
  
  // Dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [saving, setSaving] = useState(false);
  const [qualifying, setQualifying] = useState(false);
  
  // New lead form
  const [newLead, setNewLead] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    company_name: '',
    title: '',
    sales_motion_type: 'partnership_sales',
    partner_id: '',
    product_id: '',
    source: '',
    economic_units: '',
    usage_volume: '',
    urgency: '3',
    trigger_event: '',
    primary_motivation: '',
    decision_role: '',
    decision_process_clarity: '3',
    notes: ''
  });

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  useEffect(() => {
    loadLeads();
    loadPartners();
    loadScoringStats();
  }, [page, search, filterTier, filterStatus, filterMotion]);

  const loadLeads = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      if (search) params.append('search', search);
      if (filterTier !== 'all') params.append('tier', filterTier);
      if (filterStatus !== 'all') params.append('status', filterStatus);
      if (filterMotion !== 'all') params.append('sales_motion_type', filterMotion);

      const response = await fetch(`${API_URL}/api/elev8/leads?${params}`, {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setLeads(data.leads || []);
        setTotal(data.total || 0);
      }
    } catch (error) {
      console.error('Error loading leads:', error);
      toast({ title: "Error", description: "Failed to load leads", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const loadPartners = async () => {
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
    }
  };

  const loadProducts = async (partnerId) => {
    if (!partnerId) {
      setProducts([]);
      return;
    }
    try {
      const response = await fetch(`${API_URL}/api/elev8/products?partner_id=${partnerId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setProducts(data.products || []);
      }
    } catch (error) {
      console.error('Error loading products:', error);
    }
  };

  const loadScoringStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/elev8/leads/scoring/stats`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setScoringStats(data);
      }
    } catch (error) {
      console.error('Error loading scoring stats:', error);
    }
  };

  const loadLeadDetails = async (leadId) => {
    try {
      const response = await fetch(`${API_URL}/api/elev8/leads/${leadId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedLead(data);
        setShowDetailSheet(true);
      }
    } catch (error) {
      console.error('Error loading lead:', error);
    }
  };

  const createLead = async () => {
    setSaving(true);
    try {
      const payload = {
        ...newLead,
        economic_units: newLead.economic_units ? parseInt(newLead.economic_units) : null,
        usage_volume: newLead.usage_volume ? parseInt(newLead.usage_volume) : null,
        urgency: newLead.urgency ? parseInt(newLead.urgency) : null,
        decision_process_clarity: newLead.decision_process_clarity ? parseInt(newLead.decision_process_clarity) : null,
        partner_id: newLead.partner_id || null,
        product_id: newLead.product_id || null
      };

      const response = await fetch(`${API_URL}/api/elev8/leads`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        toast({ title: "Success", description: "Lead created successfully" });
        setShowCreateDialog(false);
        resetNewLead();
        loadLeads();
        loadScoringStats();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to create lead", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to create lead", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const qualifyLead = async (leadId) => {
    setQualifying(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/leads/${leadId}/qualify`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const result = await response.json();
        toast({ 
          title: "Lead Qualified!", 
          description: `Deal created successfully. Deal ID: ${result.deal_id.slice(0, 8)}...` 
        });
        setShowDetailSheet(false);
        loadLeads();
        loadScoringStats();
      } else {
        const error = await response.json();
        toast({ title: "Qualification Failed", description: error.detail || "Cannot qualify lead", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to qualify lead", variant: "destructive" });
    } finally {
      setQualifying(false);
    }
  };

  const deleteLead = async (leadId) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;
    
    try {
      const response = await fetch(`${API_URL}/api/elev8/leads/${leadId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        toast({ title: "Deleted", description: "Lead deleted successfully" });
        loadLeads();
        loadScoringStats();
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete lead", variant: "destructive" });
    }
  };

  const resetNewLead = () => {
    setNewLead({
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      company_name: '',
      title: '',
      sales_motion_type: 'partnership_sales',
      partner_id: '',
      product_id: '',
      source: '',
      economic_units: '',
      usage_volume: '',
      urgency: '3',
      trigger_event: '',
      primary_motivation: '',
      decision_role: '',
      decision_process_clarity: '3',
      notes: ''
    });
    setProducts([]);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Lead Management</h1>
          <p className="text-muted-foreground">Qualification pipeline with intelligent scoring</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Lead
        </Button>
      </div>

      {/* Scoring Stats */}
      {scoringStats && (
        <div className="grid gap-4 md:grid-cols-5">
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{scoringStats.total_leads || 0}</div>
              <p className="text-sm text-muted-foreground">Total Leads</p>
            </CardContent>
          </Card>
          {['A', 'B', 'C', 'D'].map(tier => (
            <Card key={tier}>
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold">
                      {scoringStats.tier_distribution?.[tier]?.count || 0}
                    </div>
                    <p className="text-sm text-muted-foreground">Tier {tier}</p>
                  </div>
                  <Badge className={tierColors[tier]}>{tier}</Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  Avg Score: {scoringStats.tier_distribution?.[tier]?.avg_score || 0}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search leads..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={filterTier} onValueChange={setFilterTier}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Tier" />
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
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="working">Working</SelectItem>
                <SelectItem value="info_collected">Info Collected</SelectItem>
                <SelectItem value="qualified">Qualified</SelectItem>
                <SelectItem value="unresponsive">Unresponsive</SelectItem>
                <SelectItem value="disqualified">Disqualified</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterMotion} onValueChange={setFilterMotion}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Sales Motion" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Motions</SelectItem>
                <SelectItem value="partnership_sales">Partnership Sales</SelectItem>
                <SelectItem value="partner_sales">Partner Sales</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={loadLeads}>
              <RefreshCw className="w-4 h-4" />
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
                <TableHead>Company</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Sales Motion</TableHead>
                <TableHead>Source</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : leads.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    No leads found. Create your first lead to get started.
                  </TableCell>
                </TableRow>
              ) : (
                leads.map(lead => (
                  <TableRow 
                    key={lead.id} 
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => loadLeadDetails(lead.id)}
                  >
                    <TableCell>
                      <div>
                        <p className="font-medium">{lead.full_name || `${lead.first_name} ${lead.last_name}`}</p>
                        <p className="text-sm text-muted-foreground">{lead.email}</p>
                      </div>
                    </TableCell>
                    <TableCell>{lead.company_name || '-'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={lead.lead_score} className="w-16 h-2" />
                        <span className="text-sm font-medium">{lead.lead_score}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={tierColors[lead.tier]} title={tierDescriptions[lead.tier]}>
                        {lead.tier}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusColors[lead.status]}>
                        {lead.status?.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {lead.sales_motion_type === 'partner_sales' ? 'Partner' : 'Partnership'}
                      </Badge>
                    </TableCell>
                    <TableCell>{lead.source || '-'}</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); loadLeadDetails(lead.id); }}>
                            <Edit className="w-4 h-4 mr-2" /> View Details
                          </DropdownMenuItem>
                          {lead.status !== 'qualified' && lead.status !== 'disqualified' && (
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); qualifyLead(lead.id); }}>
                              <CheckCircle className="w-4 h-4 mr-2" /> Qualify Lead
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            className="text-destructive"
                            onClick={(e) => { e.stopPropagation(); deleteLead(lead.id); }}
                          >
                            <Trash2 className="w-4 h-4 mr-2" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} leads
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(p => p + 1)}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Create Lead Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create New Lead</DialogTitle>
            <DialogDescription>
              Enter lead information. Score will be calculated automatically.
            </DialogDescription>
          </DialogHeader>
          
          <Tabs defaultValue="basic" className="mt-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="basic">Basic Info</TabsTrigger>
              <TabsTrigger value="scoring">Scoring Fields</TabsTrigger>
              <TabsTrigger value="sales">Sales Motion</TabsTrigger>
            </TabsList>
            
            <TabsContent value="basic" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>First Name *</Label>
                  <Input
                    value={newLead.first_name}
                    onChange={(e) => setNewLead({...newLead, first_name: e.target.value})}
                    placeholder="John"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Last Name *</Label>
                  <Input
                    value={newLead.last_name}
                    onChange={(e) => setNewLead({...newLead, last_name: e.target.value})}
                    placeholder="Smith"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={newLead.email}
                    onChange={(e) => setNewLead({...newLead, email: e.target.value})}
                    placeholder="john@company.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={newLead.phone}
                    onChange={(e) => setNewLead({...newLead, phone: e.target.value})}
                    placeholder="555-123-4567"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Company Name</Label>
                  <Input
                    value={newLead.company_name}
                    onChange={(e) => setNewLead({...newLead, company_name: e.target.value})}
                    placeholder="Acme Corp"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input
                    value={newLead.title}
                    onChange={(e) => setNewLead({...newLead, title: e.target.value})}
                    placeholder="VP of Operations"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Lead Source</Label>
                <Select 
                  value={newLead.source} 
                  onValueChange={(v) => setNewLead({...newLead, source: v})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="referral">Referral</SelectItem>
                    <SelectItem value="partner_referral">Partner Referral</SelectItem>
                    <SelectItem value="inbound_demo">Inbound Demo Request</SelectItem>
                    <SelectItem value="website_demo">Website Demo</SelectItem>
                    <SelectItem value="trade_show">Trade Show</SelectItem>
                    <SelectItem value="webinar">Webinar</SelectItem>
                    <SelectItem value="content_download">Content Download</SelectItem>
                    <SelectItem value="cold_outreach">Cold Outreach</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </TabsContent>
            
            <TabsContent value="scoring" className="space-y-4 mt-4">
              <div className="p-3 bg-muted rounded-lg text-sm">
                <p className="font-medium">Scoring Categories:</p>
                <p className="text-muted-foreground">
                  Size (30%) • Urgency (20%) • Source (15%) • Motivation (20%) • Decision (15%)
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Economic Units (locations, sites, etc.)</Label>
                  <Input
                    type="number"
                    value={newLead.economic_units}
                    onChange={(e) => setNewLead({...newLead, economic_units: e.target.value})}
                    placeholder="e.g., 25"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Usage Volume</Label>
                  <Input
                    type="number"
                    value={newLead.usage_volume}
                    onChange={(e) => setNewLead({...newLead, usage_volume: e.target.value})}
                    placeholder="e.g., 50"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Urgency (1-5)</Label>
                  <Select 
                    value={newLead.urgency} 
                    onValueChange={(v) => setNewLead({...newLead, urgency: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 - Not Urgent</SelectItem>
                      <SelectItem value="2">2 - Low</SelectItem>
                      <SelectItem value="3">3 - Medium</SelectItem>
                      <SelectItem value="4">4 - High</SelectItem>
                      <SelectItem value="5">5 - Critical</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Decision Process Clarity (1-5)</Label>
                  <Select 
                    value={newLead.decision_process_clarity} 
                    onValueChange={(v) => setNewLead({...newLead, decision_process_clarity: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 - Unclear</SelectItem>
                      <SelectItem value="2">2 - Somewhat Clear</SelectItem>
                      <SelectItem value="3">3 - Moderately Clear</SelectItem>
                      <SelectItem value="4">4 - Clear</SelectItem>
                      <SelectItem value="5">5 - Very Clear</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Trigger Event</Label>
                <Input
                  value={newLead.trigger_event}
                  onChange={(e) => setNewLead({...newLead, trigger_event: e.target.value})}
                  placeholder="e.g., Rising costs in Q4"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Primary Motivation</Label>
                  <Select 
                    value={newLead.primary_motivation} 
                    onValueChange={(v) => setNewLead({...newLead, primary_motivation: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select motivation" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cost_reduction">Cost Reduction</SelectItem>
                      <SelectItem value="revenue_growth">Revenue Growth</SelectItem>
                      <SelectItem value="efficiency">Efficiency</SelectItem>
                      <SelectItem value="compliance">Compliance</SelectItem>
                      <SelectItem value="competitive_pressure">Competitive Pressure</SelectItem>
                      <SelectItem value="modernization">Modernization</SelectItem>
                      <SelectItem value="expansion">Expansion</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Decision Role</Label>
                  <Select 
                    value={newLead.decision_role} 
                    onValueChange={(v) => setNewLead({...newLead, decision_role: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="decision_maker">Decision Maker</SelectItem>
                      <SelectItem value="economic_buyer">Economic Buyer</SelectItem>
                      <SelectItem value="champion">Champion</SelectItem>
                      <SelectItem value="influencer">Influencer</SelectItem>
                      <SelectItem value="user">End User</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="sales" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Sales Motion Type *</Label>
                <Select 
                  value={newLead.sales_motion_type} 
                  onValueChange={(v) => {
                    setNewLead({...newLead, sales_motion_type: v, partner_id: '', product_id: ''});
                    setProducts([]);
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="partnership_sales">Partnership Sales (Elev8 Services)</SelectItem>
                    <SelectItem value="partner_sales">Partner Sales (Partner Products)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {newLead.sales_motion_type === 'partner_sales' && (
                <>
                  <div className="space-y-2">
                    <Label>Partner *</Label>
                    <Select 
                      value={newLead.partner_id} 
                      onValueChange={(v) => {
                        setNewLead({...newLead, partner_id: v, product_id: ''});
                        loadProducts(v);
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select partner" />
                      </SelectTrigger>
                      <SelectContent>
                        {partners.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {newLead.partner_id && (
                    <div className="space-y-2">
                      <Label>Product *</Label>
                      <Select 
                        value={newLead.product_id} 
                        onValueChange={(v) => setNewLead({...newLead, product_id: v})}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select product" />
                        </SelectTrigger>
                        <SelectContent>
                          {products.map(p => (
                            <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </>
              )}
              
              <div className="space-y-2">
                <Label>Notes</Label>
                <Textarea
                  value={newLead.notes}
                  onChange={(e) => setNewLead({...newLead, notes: e.target.value})}
                  placeholder="Additional notes about this lead..."
                  rows={3}
                />
              </div>
            </TabsContent>
          </Tabs>
          
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => { setShowCreateDialog(false); resetNewLead(); }}>
              Cancel
            </Button>
            <Button onClick={createLead} disabled={saving || !newLead.first_name || !newLead.last_name}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Create Lead
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Lead Detail Sheet */}
      <Sheet open={showDetailSheet} onOpenChange={setShowDetailSheet}>
        <SheetContent className="w-[500px] sm:w-[600px] overflow-y-auto">
          {selectedLead && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-3">
                  {selectedLead.full_name || `${selectedLead.first_name} ${selectedLead.last_name}`}
                  <Badge className={tierColors[selectedLead.tier]}>{selectedLead.tier}</Badge>
                </SheetTitle>
                <SheetDescription>
                  {selectedLead.company_name} • {selectedLead.title || 'No title'}
                </SheetDescription>
              </SheetHeader>
              
              <div className="mt-6 space-y-6">
                {/* Score Card */}
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium">Lead Score</span>
                      <span className="text-2xl font-bold">{selectedLead.lead_score}</span>
                    </div>
                    <Progress value={selectedLead.lead_score} className="h-3" />
                    <p className="text-xs text-muted-foreground mt-2">
                      {tierDescriptions[selectedLead.tier]}
                    </p>
                  </CardContent>
                </Card>
                
                {/* Contact Info */}
                <div className="space-y-3">
                  <h3 className="font-medium">Contact Information</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-muted-foreground" />
                      {selectedLead.email || 'No email'}
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-muted-foreground" />
                      {selectedLead.phone || 'No phone'}
                    </div>
                    <div className="flex items-center gap-2">
                      <Building className="w-4 h-4 text-muted-foreground" />
                      {selectedLead.company_name || 'No company'}
                    </div>
                    <div className="flex items-center gap-2">
                      <Target className="w-4 h-4 text-muted-foreground" />
                      {selectedLead.source || 'Unknown source'}
                    </div>
                  </div>
                </div>
                
                {/* Scoring Details */}
                <div className="space-y-3">
                  <h3 className="font-medium">Scoring Inputs</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-muted-foreground">Economic Units</p>
                      <p className="font-medium">{selectedLead.economic_units || '-'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Usage Volume</p>
                      <p className="font-medium">{selectedLead.usage_volume || '-'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Urgency</p>
                      <p className="font-medium">{selectedLead.urgency || '-'} / 5</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Decision Clarity</p>
                      <p className="font-medium">{selectedLead.decision_process_clarity || '-'} / 5</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Motivation</p>
                      <p className="font-medium">{selectedLead.primary_motivation?.replace('_', ' ') || '-'}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Decision Role</p>
                      <p className="font-medium">{selectedLead.decision_role?.replace('_', ' ') || '-'}</p>
                    </div>
                  </div>
                  {selectedLead.trigger_event && (
                    <div>
                      <p className="text-muted-foreground text-sm">Trigger Event</p>
                      <p className="font-medium text-sm">{selectedLead.trigger_event}</p>
                    </div>
                  )}
                </div>
                
                {/* Sales Motion */}
                <div className="space-y-3">
                  <h3 className="font-medium">Sales Motion</h3>
                  <div className="p-3 bg-muted rounded-lg">
                    <Badge variant="outline" className="mb-2">
                      {selectedLead.sales_motion_type === 'partner_sales' ? 'Partner Sales' : 'Partnership Sales'}
                    </Badge>
                    {selectedLead.partner_name && (
                      <p className="text-sm">Partner: <span className="font-medium">{selectedLead.partner_name}</span></p>
                    )}
                    {selectedLead.product_name && (
                      <p className="text-sm">Product: <span className="font-medium">{selectedLead.product_name}</span></p>
                    )}
                  </div>
                </div>
                
                {/* Status & Actions */}
                <div className="space-y-3">
                  <h3 className="font-medium">Status</h3>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={statusColors[selectedLead.status]}>
                      {selectedLead.status?.replace('_', ' ')}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      {selectedLead.touchpoint_count || 0} touchpoints
                    </span>
                  </div>
                </div>
                
                {/* Actions */}
                {selectedLead.status !== 'qualified' && selectedLead.status !== 'disqualified' && (
                  <div className="pt-4 border-t">
                    <Button 
                      className="w-full" 
                      onClick={() => qualifyLead(selectedLead.id)}
                      disabled={qualifying}
                    >
                      {qualifying ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <ArrowRight className="w-4 h-4 mr-2" />
                      )}
                      Qualify & Push to Sales Pipeline
                    </Button>
                    <p className="text-xs text-muted-foreground mt-2 text-center">
                      This will create a Deal, Contact, and Company record
                    </p>
                  </div>
                )}
                
                {selectedLead.status === 'qualified' && selectedLead.converted_deal_id && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-2 text-green-700">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Lead Qualified</span>
                    </div>
                    <p className="text-sm text-green-600 mt-1">
                      Converted to Deal: {selectedLead.converted_deal_id.slice(0, 8)}...
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default LeadsPage;
