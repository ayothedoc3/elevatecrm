import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Skeleton } from '../components/ui/skeleton';
import { Progress } from '../components/ui/progress';
import {
  Users, Plus, Search, Filter, DollarSign, TrendingUp, Link2,
  MousePointer, CheckCircle, Clock, XCircle, ExternalLink,
  Copy, MoreVertical, UserPlus, Settings, Eye, Ban, Play,
  RefreshCw, Download, ChevronRight, Percent, Target, Loader2,
  Image, FileText, Upload, Grid, List, Trash2, X
} from 'lucide-react';
import { toast } from 'sonner';

const AFFILIATE_STATUS_CONFIG = {
  pending: { label: 'Pending', color: 'bg-yellow-500/20 text-yellow-500', icon: Clock },
  active: { label: 'Active', color: 'bg-green-500/20 text-green-500', icon: CheckCircle },
  paused: { label: 'Paused', color: 'bg-gray-500/20 text-gray-500', icon: Clock },
  banned: { label: 'Banned', color: 'bg-red-500/20 text-red-500', icon: Ban }
};

const COMMISSION_STATUS_CONFIG = {
  pending: { label: 'Pending', color: 'bg-yellow-500' },
  approved: { label: 'Approved', color: 'bg-blue-500' },
  paid: { label: 'Paid', color: 'bg-green-500' },
  reversed: { label: 'Reversed', color: 'bg-red-500' }
};

const AffiliatesPage = () => {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState('affiliates');
  const [loading, setLoading] = useState(true);
  const [affiliates, setAffiliates] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [commissions, setCommissions] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [materialCategories, setMaterialCategories] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [selectedAffiliate, setSelectedAffiliate] = useState(null);
  const [showAffiliateSheet, setShowAffiliateSheet] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showProgramDialog, setShowProgramDialog] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showUrlDialog, setShowUrlDialog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [materialCategory, setMaterialCategory] = useState('all');
  const [viewMode, setViewMode] = useState('grid');

  // Upload form state
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadName, setUploadName] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');
  const [uploadCategory, setUploadCategory] = useState('other');
  const [uploadTags, setUploadTags] = useState('');

  // URL form state
  const [urlName, setUrlName] = useState('');
  const [urlDescription, setUrlDescription] = useState('');
  const [urlCategory, setUrlCategory] = useState('other');
  const [urlValue, setUrlValue] = useState('');
  const [urlTags, setUrlTags] = useState('');

  // New affiliate form
  const [newAffiliate, setNewAffiliate] = useState({
    name: '', email: '', phone: '', company: '', website: '',
    payout_method: 'manual', notes: ''
  });

  // New program form
  const [newProgram, setNewProgram] = useState({
    name: '', description: '', product_type: 'service', journey_type: 'demo_first',
    attribution_type: 'deal', commission_type: 'percentage', commission_value: 10,
    attribution_window_days: 30, auto_approve: false
  });

  const MATERIAL_CATEGORIES = [
    { value: 'banners', label: 'Banners' },
    { value: 'social_posts', label: 'Social Posts' },
    { value: 'email_templates', label: 'Email Templates' },
    { value: 'logos', label: 'Logos' },
    { value: 'product_images', label: 'Product Images' },
    { value: 'sales_sheets', label: 'Sales Sheets' },
    { value: 'videos', label: 'Videos' },
    { value: 'other', label: 'Other' }
  ];

  const api = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [affiliatesRes, programsRes, commissionsRes, dashboardRes, materialsRes, categoriesRes] = await Promise.all([
        api.get('/affiliates'),
        api.get('/affiliates/programs'),
        api.get('/affiliates/commissions'),
        api.get('/affiliates/analytics/dashboard'),
        api.get('/materials'),
        api.get('/materials/categories')
      ]);
      setAffiliates(affiliatesRes.data.affiliates || []);
      setPrograms(programsRes.data.programs || []);
      setCommissions(commissionsRes.data.commissions || []);
      setDashboard(dashboardRes.data);
      setMaterials(materialsRes.data.materials || []);
      setMaterialCategories(categoriesRes.data.categories || []);
    } catch (error) {
      console.error('Error fetching affiliate data:', error);
      toast.error('Failed to load affiliate data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateAffiliate = async () => {
    if (!newAffiliate.name || !newAffiliate.email) {
      toast.error('Name and email are required');
      return;
    }
    setSaving(true);
    try {
      await api.post('/affiliates', newAffiliate);
      toast.success('Affiliate created successfully');
      setShowCreateDialog(false);
      setNewAffiliate({ name: '', email: '', phone: '', company: '', website: '', payout_method: 'manual', notes: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create affiliate');
    } finally {
      setSaving(false);
    }
  };

  const handleCreateProgram = async () => {
    if (!newProgram.name) {
      toast.error('Program name is required');
      return;
    }
    setSaving(true);
    try {
      await api.post('/affiliates/programs', newProgram);
      toast.success('Program created successfully');
      setShowProgramDialog(false);
      setNewProgram({
        name: '', description: '', product_type: 'service', journey_type: 'demo_first',
        attribution_type: 'deal', commission_type: 'percentage', commission_value: 10,
        attribution_window_days: 30, auto_approve: false
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create program');
    } finally {
      setSaving(false);
    }
  };

  const handleApproveAffiliate = async (affiliateId) => {
    try {
      await api.post(`/affiliates/${affiliateId}/approve`);
      toast.success('Affiliate approved');
      fetchData();
    } catch (error) {
      toast.error('Failed to approve affiliate');
    }
  };

  const handleApproveCommission = async (commissionId) => {
    try {
      await api.post(`/affiliates/commissions/${commissionId}/approve`);
      toast.success('Commission approved');
      fetchData();
    } catch (error) {
      toast.error('Failed to approve commission');
    }
  };

  const handlePayCommission = async (commissionId) => {
    try {
      await api.post(`/affiliates/commissions/${commissionId}/pay`);
      toast.success('Commission marked as paid');
      fetchData();
    } catch (error) {
      toast.error('Failed to mark commission as paid');
    }
  };

  const copyToClipboard = async (text) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        toast.success('Copied to clipboard');
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        try {
          document.execCommand('copy');
          toast.success('Copied to clipboard');
        } catch (err) {
          toast.info(`Copy this: ${text}`);
          prompt('Copy this:', text);
        }
        document.body.removeChild(textArea);
      }
    } catch (err) {
      toast.info(`Copy this: ${text}`);
      prompt('Copy this:', text);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency: 'USD', minimumFractionDigits: 0
    }).format(amount || 0);
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleFileUpload = async () => {
    if (!uploadFile || !uploadName) {
      toast.error('Please select a file and enter a name');
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('name', uploadName);
      formData.append('description', uploadDescription);
      formData.append('category', uploadCategory);
      formData.append('tags', uploadTags);
      await api.post('/materials/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Material uploaded successfully');
      setShowUploadDialog(false);
      setUploadFile(null);
      setUploadName('');
      setUploadDescription('');
      setUploadCategory('other');
      setUploadTags('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload material');
    } finally {
      setUploading(false);
    }
  };

  const handleUrlCreate = async () => {
    if (!urlName || !urlValue) {
      toast.error('Please enter a name and URL');
      return;
    }
    setUploading(true);
    try {
      await api.post('/materials/url', {
        name: urlName,
        description: urlDescription,
        category: urlCategory,
        material_type: 'url',
        url: urlValue,
        tags: urlTags.split(',').map(t => t.trim()).filter(Boolean)
      });
      toast.success('URL material created successfully');
      setShowUrlDialog(false);
      setUrlName('');
      setUrlDescription('');
      setUrlCategory('other');
      setUrlValue('');
      setUrlTags('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create URL material');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteMaterial = async (materialId) => {
    if (!window.confirm('Are you sure you want to delete this material?')) return;
    try {
      await api.delete(`/materials/${materialId}`);
      toast.success('Material deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete material');
    }
  };

  const filteredMaterials = materials.filter(mat => {
    return materialCategory === 'all' || mat.category === materialCategory;
  });

  const filteredAffiliates = affiliates.filter(aff => {
    const matchesSearch = !searchQuery || 
      aff.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      aff.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || aff.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Users className="w-6 h-6" />
            Affiliate Management
          </h1>
          <p className="text-muted-foreground">Manage affiliates, programs, and commissions</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Dialog open={showProgramDialog} onOpenChange={setShowProgramDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Settings className="w-4 h-4 mr-2" />
                New Program
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Create Affiliate Program</DialogTitle>
                <DialogDescription>Configure a new affiliate program</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Program Name *</Label>
                  <Input
                    value={newProgram.name}
                    onChange={(e) => setNewProgram({...newProgram, name: e.target.value})}
                    placeholder="e.g. Partner Program"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={newProgram.description}
                    onChange={(e) => setNewProgram({...newProgram, description: e.target.value})}
                    placeholder="Program details..."
                    rows={2}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Journey Type</Label>
                    <Select value={newProgram.journey_type} onValueChange={(v) => setNewProgram({...newProgram, journey_type: v})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="demo_first">Demo First (Service)</SelectItem>
                        <SelectItem value="direct_checkout">Direct Checkout (Product)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Commission Type</Label>
                    <Select value={newProgram.commission_type} onValueChange={(v) => setNewProgram({...newProgram, commission_type: v})}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="percentage">Percentage</SelectItem>
                        <SelectItem value="flat">Flat Amount</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Commission Value</Label>
                    <Input
                      type="number"
                      value={newProgram.commission_value}
                      onChange={(e) => setNewProgram({...newProgram, commission_value: parseFloat(e.target.value) || 0})}
                      placeholder={newProgram.commission_type === 'percentage' ? '10' : '50'}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Attribution Window (days)</Label>
                    <Input
                      type="number"
                      value={newProgram.attribution_window_days}
                      onChange={(e) => setNewProgram({...newProgram, attribution_window_days: parseInt(e.target.value) || 30})}
                    />
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={newProgram.auto_approve}
                    onChange={(e) => setNewProgram({...newProgram, auto_approve: e.target.checked})}
                    className="rounded"
                  />
                  <Label className="font-normal">Auto-approve commissions</Label>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowProgramDialog(false)}>Cancel</Button>
                <Button onClick={handleCreateProgram} disabled={saving}>
                  {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Create Program
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="w-4 h-4 mr-2" />
                Add Affiliate
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New Affiliate</DialogTitle>
                <DialogDescription>Create a new affiliate partner</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Name *</Label>
                    <Input
                      value={newAffiliate.name}
                      onChange={(e) => setNewAffiliate({...newAffiliate, name: e.target.value})}
                      placeholder="Full name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email *</Label>
                    <Input
                      type="email"
                      value={newAffiliate.email}
                      onChange={(e) => setNewAffiliate({...newAffiliate, email: e.target.value})}
                      placeholder="email@example.com"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Company</Label>
                    <Input
                      value={newAffiliate.company}
                      onChange={(e) => setNewAffiliate({...newAffiliate, company: e.target.value})}
                      placeholder="Company name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Phone</Label>
                    <Input
                      value={newAffiliate.phone}
                      onChange={(e) => setNewAffiliate({...newAffiliate, phone: e.target.value})}
                      placeholder="Phone number"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Website</Label>
                  <Input
                    value={newAffiliate.website}
                    onChange={(e) => setNewAffiliate({...newAffiliate, website: e.target.value})}
                    placeholder="https://..."
                  />
                </div>
                <div className="space-y-2">
                  <Label>Payout Method</Label>
                  <Select value={newAffiliate.payout_method} onValueChange={(v) => setNewAffiliate({...newAffiliate, payout_method: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual">Manual</SelectItem>
                      <SelectItem value="stripe">Stripe</SelectItem>
                      <SelectItem value="paypal">PayPal</SelectItem>
                      <SelectItem value="wise">Wise</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea
                    value={newAffiliate.notes}
                    onChange={(e) => setNewAffiliate({...newAffiliate, notes: e.target.value})}
                    placeholder="Internal notes..."
                    rows={2}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                <Button onClick={handleCreateAffiliate} disabled={saving}>
                  {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Create Affiliate
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Dashboard Stats */}
      {dashboard && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Affiliates</p>
                  <p className="text-2xl font-bold">{dashboard.affiliates?.total || 0}</p>
                  <p className="text-xs text-muted-foreground">{dashboard.affiliates?.active || 0} active</p>
                </div>
                <Users className="w-8 h-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Clicks</p>
                  <p className="text-2xl font-bold">{dashboard.clicks || 0}</p>
                  <p className="text-xs text-muted-foreground">Last 30 days</p>
                </div>
                <MousePointer className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending</p>
                  <p className="text-2xl font-bold">{formatCurrency(dashboard.commissions?.pending?.total)}</p>
                  <p className="text-xs text-muted-foreground">{dashboard.commissions?.pending?.count || 0} commissions</p>
                </div>
                <Clock className="w-8 h-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Approved</p>
                  <p className="text-2xl font-bold">{formatCurrency(dashboard.commissions?.approved?.total)}</p>
                  <p className="text-xs text-muted-foreground">{dashboard.commissions?.approved?.count || 0} to pay</p>
                </div>
                <CheckCircle className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Paid</p>
                  <p className="text-2xl font-bold">{formatCurrency(dashboard.commissions?.paid?.total)}</p>
                  <p className="text-xs text-muted-foreground">{dashboard.commissions?.paid?.count || 0} payouts</p>
                </div>
                <DollarSign className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="affiliates">Affiliates</TabsTrigger>
          <TabsTrigger value="programs">Programs</TabsTrigger>
          <TabsTrigger value="commissions">Commissions</TabsTrigger>
          <TabsTrigger value="links">Links</TabsTrigger>
          <TabsTrigger value="materials">Materials</TabsTrigger>
        </TabsList>

        {/* Affiliates Tab */}
        <TabsContent value="affiliates" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-4">
                <div className="relative flex-1 max-w-xs">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search affiliates..."
                    className="pl-9"
                  />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-40">
                    <Filter className="w-4 h-4 mr-2" />
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="paused">Paused</SelectItem>
                    <SelectItem value="banned">Banned</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Affiliates Table */}
          <Card>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-6 space-y-4">
                  {[1,2,3].map(i => <Skeleton key={i} className="h-16" />)}
                </div>
              ) : filteredAffiliates.length === 0 ? (
                <div className="text-center py-12">
                  <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-semibold mb-2">No Affiliates Found</h3>
                  <p className="text-muted-foreground mb-4">Get started by adding your first affiliate</p>
                  <Button onClick={() => setShowCreateDialog(true)}>
                    <UserPlus className="w-4 h-4 mr-2" />
                    Add Affiliate
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Affiliate</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Links</TableHead>
                      <TableHead>Clicks</TableHead>
                      <TableHead>Earnings</TableHead>
                      <TableHead>Paid</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredAffiliates.map(affiliate => {
                      const statusConfig = AFFILIATE_STATUS_CONFIG[affiliate.status] || AFFILIATE_STATUS_CONFIG.pending;
                      const StatusIcon = statusConfig.icon;
                      const pendingAmount = affiliate.commission_stats?.pending?.total || 0;
                      
                      return (
                        <TableRow key={affiliate.id} className="cursor-pointer" onClick={() => {
                          setSelectedAffiliate(affiliate);
                          setShowAffiliateSheet(true);
                        }}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{affiliate.name}</p>
                              <p className="text-sm text-muted-foreground">{affiliate.email}</p>
                              {affiliate.company && <p className="text-xs text-muted-foreground">{affiliate.company}</p>}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge className={statusConfig.color}>
                              <StatusIcon className="w-3 h-3 mr-1" />
                              {statusConfig.label}
                            </Badge>
                          </TableCell>
                          <TableCell>{affiliate.link_count || 0}</TableCell>
                          <TableCell>{affiliate.total_clicks || 0}</TableCell>
                          <TableCell>
                            <div>
                              <p className="font-medium">{formatCurrency(affiliate.total_earnings)}</p>
                              {pendingAmount > 0 && (
                                <p className="text-xs text-yellow-500">{formatCurrency(pendingAmount)} pending</p>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>{formatCurrency(affiliate.total_paid)}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              {affiliate.status === 'pending' && (
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleApproveAffiliate(affiliate.id);
                                  }}
                                >
                                  Approve
                                </Button>
                              )}
                              <ChevronRight className="w-4 h-4 text-muted-foreground" />
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Programs Tab */}
        <TabsContent value="programs" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {programs.map(program => (
              <Card key={program.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">{program.name}</CardTitle>
                      <CardDescription className="text-xs mt-1">
                        {program.journey_type === 'demo_first' ? '🎯 Demo First' : '🛒 Direct Checkout'}
                      </CardDescription>
                    </div>
                    <Badge variant={program.is_active ? 'default' : 'secondary'}>
                      {program.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {program.description && (
                    <p className="text-sm text-muted-foreground">{program.description}</p>
                  )}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="p-2 bg-muted/50 rounded">
                      <p className="text-muted-foreground text-xs">Commission</p>
                      <p className="font-semibold">
                        {program.commission_type === 'percentage' 
                          ? `${program.commission_value}%`
                          : formatCurrency(program.commission_value)}
                      </p>
                    </div>
                    <div className="p-2 bg-muted/50 rounded">
                      <p className="text-muted-foreground text-xs">Attribution</p>
                      <p className="font-semibold">{program.attribution_window_days} days</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{program.affiliate_count || 0} affiliates</span>
                    <span className={program.auto_approve ? 'text-green-500' : 'text-yellow-500'}>
                      {program.auto_approve ? '✓ Auto-approve' : '⏳ Manual approval'}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
            
            {programs.length === 0 && !loading && (
              <Card className="col-span-full text-center py-12">
                <CardContent>
                  <Settings className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-semibold mb-2">No Programs Yet</h3>
                  <p className="text-muted-foreground mb-4">Create your first affiliate program</p>
                  <Button onClick={() => setShowProgramDialog(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Program
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Commissions Tab */}
        <TabsContent value="commissions" className="space-y-4">
          <Card>
            <CardContent className="p-0">
              {loading ? (
                <div className="p-6 space-y-4">
                  {[1,2,3].map(i => <Skeleton key={i} className="h-16" />)}
                </div>
              ) : commissions.length === 0 ? (
                <div className="text-center py-12">
                  <DollarSign className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-semibold mb-2">No Commissions Yet</h3>
                  <p className="text-muted-foreground">Commissions will appear here when affiliates generate sales</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Affiliate</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Earned</TableHead>
                      <TableHead>Deal</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {commissions.map(commission => {
                      const statusConfig = COMMISSION_STATUS_CONFIG[commission.status];
                      return (
                        <TableRow key={commission.id}>
                          <TableCell className="font-medium">{commission.affiliate_name}</TableCell>
                          <TableCell className="font-semibold">{formatCurrency(commission.amount)}</TableCell>
                          <TableCell>
                            <Badge className={`${statusConfig.color} text-white`}>
                              {statusConfig.label}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {new Date(commission.earned_at).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {commission.deal_id ? 'Deal' : 'Direct'}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              {commission.status === 'pending' && (
                                <Button size="sm" variant="outline" onClick={() => handleApproveCommission(commission.id)}>
                                  Approve
                                </Button>
                              )}
                              {commission.status === 'approved' && (
                                <Button size="sm" variant="outline" onClick={() => handlePayCommission(commission.id)}>
                                  Mark Paid
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Links Tab */}
        <TabsContent value="links" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Affiliate Links</CardTitle>
              <CardDescription>All referral links generated by affiliates</CardDescription>
            </CardHeader>
            <CardContent>
              {affiliates.filter(a => a.links?.length > 0).length === 0 ? (
                <div className="text-center py-8">
                  <Link2 className="w-10 h-10 mx-auto text-muted-foreground mb-2" />
                  <p className="text-muted-foreground">No links created yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {affiliates.filter(a => a.links?.length > 0).flatMap(a => 
                    (a.links || []).map(link => (
                      <div key={link.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                        <div>
                          <p className="font-medium">{a.name}</p>
                          <p className="text-sm text-muted-foreground font-mono">/ref/{link.referral_code}</p>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <p className="font-semibold">{link.click_count} clicks</p>
                            <p className="text-xs text-muted-foreground">{link.conversion_count} conversions</p>
                          </div>
                          <Button variant="ghost" size="icon" onClick={() => copyToClipboard(link.referral_code)}>
                            <Copy className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Materials Tab */}
        <TabsContent value="materials" className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Select value={materialCategory} onValueChange={setMaterialCategory}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {MATERIAL_CATEGORIES.map(cat => (
                    <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <div className="flex items-center gap-1">
                <Button variant={viewMode === 'grid' ? 'secondary' : 'ghost'} size="icon" onClick={() => setViewMode('grid')}>
                  <Grid className="w-4 h-4" />
                </Button>
                <Button variant={viewMode === 'list' ? 'secondary' : 'ghost'} size="icon" onClick={() => setViewMode('list')}>
                  <List className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Dialog open={showUrlDialog} onOpenChange={setShowUrlDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Link2 className="w-4 h-4 mr-2" />
                    Add URL
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add URL Material</DialogTitle>
                    <DialogDescription>Add a link to external content</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Name *</Label>
                      <Input value={urlName} onChange={(e) => setUrlName(e.target.value)} placeholder="Material name" />
                    </div>
                    <div className="space-y-2">
                      <Label>URL *</Label>
                      <Input value={urlValue} onChange={(e) => setUrlValue(e.target.value)} placeholder="https://..." />
                    </div>
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Select value={urlCategory} onValueChange={setUrlCategory}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {MATERIAL_CATEGORIES.map(cat => (
                            <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Description</Label>
                      <Textarea value={urlDescription} onChange={(e) => setUrlDescription(e.target.value)} placeholder="Optional description" rows={2} />
                    </div>
                    <div className="space-y-2">
                      <Label>Tags</Label>
                      <Input value={urlTags} onChange={(e) => setUrlTags(e.target.value)} placeholder="Comma-separated tags" />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowUrlDialog(false)}>Cancel</Button>
                    <Button onClick={handleUrlCreate} disabled={uploading}>
                      {uploading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      Add URL
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
                <DialogTrigger asChild>
                  <Button>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload File
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Upload Material</DialogTitle>
                    <DialogDescription>Upload images, PDFs, or documents for affiliates</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>File *</Label>
                      <div className="border-2 border-dashed rounded-lg p-6 text-center">
                        {uploadFile ? (
                          <div className="flex items-center justify-center gap-2">
                            <FileText className="w-5 h-5" />
                            <span>{uploadFile.name}</span>
                            <Button variant="ghost" size="sm" onClick={() => setUploadFile(null)}>
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                        ) : (
                          <label className="cursor-pointer">
                            <Upload className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                            <p className="text-sm text-muted-foreground">Click to upload or drag and drop</p>
                            <p className="text-xs text-muted-foreground mt-1">Images, PDFs up to 50MB</p>
                            <input
                              type="file"
                              className="hidden"
                              accept="image/*,.pdf"
                              onChange={(e) => {
                                const file = e.target.files?.[0];
                                if (file) {
                                  setUploadFile(file);
                                  if (!uploadName) setUploadName(file.name.replace(/\.[^/.]+$/, ''));
                                }
                              }}
                            />
                          </label>
                        )}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Name *</Label>
                      <Input value={uploadName} onChange={(e) => setUploadName(e.target.value)} placeholder="Material name" />
                    </div>
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Select value={uploadCategory} onValueChange={setUploadCategory}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {MATERIAL_CATEGORIES.map(cat => (
                            <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Description</Label>
                      <Textarea value={uploadDescription} onChange={(e) => setUploadDescription(e.target.value)} placeholder="Optional description" rows={2} />
                    </div>
                    <div className="space-y-2">
                      <Label>Tags</Label>
                      <Input value={uploadTags} onChange={(e) => setUploadTags(e.target.value)} placeholder="Comma-separated tags" />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowUploadDialog(false)}>Cancel</Button>
                    <Button onClick={handleFileUpload} disabled={uploading || !uploadFile}>
                      {uploading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      Upload
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>

          {/* Category Pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <Badge
              variant={materialCategory === 'all' ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setMaterialCategory('all')}
            >
              All ({materials.length})
            </Badge>
            {materialCategories.map(cat => (
              <Badge
                key={cat.value}
                variant={materialCategory === cat.value ? 'default' : 'outline'}
                className="cursor-pointer"
                onClick={() => setMaterialCategory(cat.value)}
              >
                {cat.label} ({cat.count})
              </Badge>
            ))}
          </div>

          {/* Materials Grid/List */}
          {filteredMaterials.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Image className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="font-semibold mb-2">No Materials Found</h3>
                <p className="text-muted-foreground mb-4">Upload your first marketing material for affiliates</p>
                <Button onClick={() => setShowUploadDialog(true)}>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Material
                </Button>
              </CardContent>
            </Card>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredMaterials.map(material => (
                <Card key={material.id} className="overflow-hidden hover:shadow-lg transition-shadow">
                  <div className="aspect-video bg-muted relative flex items-center justify-center">
                    {material.material_type === 'image' && material.file_url ? (
                      <img src={material.file_url} alt={material.name} className="w-full h-full object-cover" />
                    ) : material.material_type === 'pdf' ? (
                      <FileText className="w-12 h-12 text-muted-foreground" />
                    ) : (
                      <Link2 className="w-12 h-12 text-muted-foreground" />
                    )}
                    <Badge className="absolute top-2 right-2 text-xs">{material.category?.replace('_', ' ')}</Badge>
                  </div>
                  <CardContent className="p-4">
                    <h3 className="font-semibold truncate">{material.name}</h3>
                    <p className="text-sm text-muted-foreground truncate">{material.description || 'No description'}</p>
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-xs text-muted-foreground">
                        {material.material_type === 'url' ? 'URL' : formatFileSize(material.file_size)}
                      </span>
                      <div className="flex items-center gap-1">
                        {material.file_url && (
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => window.open(material.file_url, '_blank')}>
                            <ExternalLink className="w-4 h-4" />
                          </Button>
                        )}
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => copyToClipboard(material.file_url || material.url)}>
                          <Copy className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDeleteMaterial(material.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="p-0">
                <div className="divide-y">
                  {filteredMaterials.map(material => (
                    <div key={material.id} className="flex items-center gap-4 p-4 hover:bg-muted/50">
                      <div className="w-12 h-12 rounded bg-muted flex items-center justify-center flex-shrink-0">
                        {material.material_type === 'image' ? <Image className="w-6 h-6 text-muted-foreground" /> :
                         material.material_type === 'pdf' ? <FileText className="w-6 h-6 text-muted-foreground" /> :
                         <Link2 className="w-6 h-6 text-muted-foreground" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium truncate">{material.name}</h3>
                        <p className="text-sm text-muted-foreground truncate">{material.description || 'No description'}</p>
                      </div>
                      <Badge variant="outline">{material.category?.replace('_', ' ')}</Badge>
                      <span className="text-sm text-muted-foreground w-20 text-right">
                        {material.material_type === 'url' ? 'URL' : formatFileSize(material.file_size)}
                      </span>
                      <div className="flex items-center gap-1">
                        {material.file_url && (
                          <Button variant="ghost" size="icon" onClick={() => window.open(material.file_url, '_blank')}>
                            <ExternalLink className="w-4 h-4" />
                          </Button>
                        )}
                        <Button variant="ghost" size="icon" onClick={() => copyToClipboard(material.file_url || material.url)}>
                          <Copy className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDeleteMaterial(material.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Affiliate Detail Sheet */}
      <Sheet open={showAffiliateSheet} onOpenChange={setShowAffiliateSheet}>
        <SheetContent className="w-full sm:max-w-lg">
          {selectedAffiliate && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedAffiliate.name}</SheetTitle>
                <SheetDescription>{selectedAffiliate.email}</SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="flex items-center gap-2">
                  <Badge className={AFFILIATE_STATUS_CONFIG[selectedAffiliate.status]?.color}>
                    {AFFILIATE_STATUS_CONFIG[selectedAffiliate.status]?.label}
                  </Badge>
                  {selectedAffiliate.company && (
                    <span className="text-sm text-muted-foreground">• {selectedAffiliate.company}</span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">Total Earnings</p>
                      <p className="text-xl font-bold">{formatCurrency(selectedAffiliate.total_earnings)}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4">
                      <p className="text-sm text-muted-foreground">Total Paid</p>
                      <p className="text-xl font-bold text-green-500">{formatCurrency(selectedAffiliate.total_paid)}</p>
                    </CardContent>
                  </Card>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Referral Links</h4>
                  {selectedAffiliate.links?.length > 0 ? (
                    <div className="space-y-2">
                      {selectedAffiliate.links.map(link => (
                        <div key={link.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                          <div>
                            <p className="font-mono text-sm">{link.referral_code}</p>
                            <p className="text-xs text-muted-foreground">{link.click_count} clicks • {link.conversion_count} conversions</p>
                          </div>
                          <Button variant="ghost" size="icon" onClick={() => copyToClipboard(link.referral_code)}>
                            <Copy className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No links created yet</p>
                  )}
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Recent Commissions</h4>
                  {selectedAffiliate.recent_commissions?.length > 0 ? (
                    <div className="space-y-2">
                      {selectedAffiliate.recent_commissions.map(comm => (
                        <div key={comm.id} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                          <div>
                            <p className="font-medium">{formatCurrency(comm.amount)}</p>
                            <p className="text-xs text-muted-foreground">{new Date(comm.earned_at).toLocaleDateString()}</p>
                          </div>
                          <Badge className={COMMISSION_STATUS_CONFIG[comm.status]?.color + ' text-white'}>
                            {comm.status}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No commissions yet</p>
                  )}
                </div>

                {selectedAffiliate.status === 'pending' && (
                  <Button className="w-full" onClick={() => {
                    handleApproveAffiliate(selectedAffiliate.id);
                    setShowAffiliateSheet(false);
                  }}>
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Approve Affiliate
                  </Button>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default AffiliatesPage;
