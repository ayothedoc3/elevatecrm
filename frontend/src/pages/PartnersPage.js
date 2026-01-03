import React, { useState, useEffect } from 'react';
import {
  Building2, Search, Plus, Edit, Trash2, MoreHorizontal,
  Package, Users, TrendingUp, CheckCircle, Clock, XCircle,
  ChevronLeft, ChevronRight, RefreshCw, Loader2, ExternalLink
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
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

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const statusColors = {
  active: 'bg-green-100 text-green-800',
  inactive: 'bg-gray-100 text-gray-800',
  prospect: 'bg-blue-100 text-blue-800'
};

const typeColors = {
  channel: 'bg-purple-100 text-purple-800',
  reseller: 'bg-blue-100 text-blue-800',
  technology: 'bg-indigo-100 text-indigo-800',
  strategic: 'bg-orange-100 text-orange-800'
};

const PartnersPage = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [partners, setPartners] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterType, setFilterType] = useState('all');
  
  // Dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showProductDialog, setShowProductDialog] = useState(false);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  const [selectedPartner, setSelectedPartner] = useState(null);
  const [saving, setSaving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  
  // Form state
  const [partnerForm, setPartnerForm] = useState({
    name: '',
    partner_type: 'channel',
    status: 'prospect',
    description: '',
    territory: '',
    primary_contact_name: '',
    primary_contact_email: '',
    primary_contact_phone: ''
  });
  
  const [productForm, setProductForm] = useState({
    name: '',
    description: '',
    category: '',
    sku: '',
    base_price: '',
    currency: 'USD',
    pricing_model: 'one_time',
    economic_unit_label: '',
    usage_volume_label: ''
  });

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  useEffect(() => {
    loadPartners();
  }, [page, search, filterStatus, filterType]);

  const loadPartners = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      if (search) params.append('search', search);
      if (filterStatus !== 'all') params.append('status', filterStatus);
      if (filterType !== 'all') params.append('partner_type', filterType);

      const response = await fetch(`${API_URL}/api/elev8/partners?${params}`, {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setPartners(data.partners || []);
        setTotal(data.total || 0);
      }
    } catch (error) {
      console.error('Error loading partners:', error);
      toast({ title: "Error", description: "Failed to load partners", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const loadPartnerDetails = async (partnerId) => {
    try {
      const response = await fetch(`${API_URL}/api/elev8/partners/${partnerId}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setSelectedPartner(data);
        setShowDetailSheet(true);
      }
    } catch (error) {
      console.error('Error loading partner:', error);
    }
  };

  const savePartner = async () => {
    setSaving(true);
    try {
      const url = editMode 
        ? `${API_URL}/api/elev8/partners/${selectedPartner.id}`
        : `${API_URL}/api/elev8/partners`;
      
      const response = await fetch(url, {
        method: editMode ? 'PUT' : 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(partnerForm)
      });

      if (response.ok) {
        toast({ title: "Success", description: `Partner ${editMode ? 'updated' : 'created'} successfully` });
        setShowCreateDialog(false);
        resetPartnerForm();
        loadPartners();
        if (editMode && selectedPartner) {
          loadPartnerDetails(selectedPartner.id);
        }
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to save partner", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to save partner", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const deletePartner = async (partnerId) => {
    if (!window.confirm('Are you sure you want to delete this partner?')) return;
    
    try {
      const response = await fetch(`${API_URL}/api/elev8/partners/${partnerId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        toast({ title: "Deleted", description: "Partner deleted successfully" });
        setShowDetailSheet(false);
        loadPartners();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to delete partner", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete partner", variant: "destructive" });
    }
  };

  const createProduct = async () => {
    if (!selectedPartner) return;
    
    setSaving(true);
    try {
      const payload = {
        ...productForm,
        partner_id: selectedPartner.id,
        base_price: productForm.base_price ? parseFloat(productForm.base_price) : null
      };

      const response = await fetch(`${API_URL}/api/elev8/products`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        toast({ title: "Success", description: "Product created successfully" });
        setShowProductDialog(false);
        resetProductForm();
        loadPartnerDetails(selectedPartner.id);
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to create product", variant: "destructive" });
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to create product", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const deleteProduct = async (productId) => {
    if (!window.confirm('Are you sure you want to delete this product?')) return;
    
    try {
      const response = await fetch(`${API_URL}/api/elev8/products/${productId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        toast({ title: "Deleted", description: "Product deleted successfully" });
        loadPartnerDetails(selectedPartner.id);
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete product", variant: "destructive" });
    }
  };

  const resetPartnerForm = () => {
    setPartnerForm({
      name: '',
      partner_type: 'channel',
      status: 'prospect',
      description: '',
      territory: '',
      primary_contact_name: '',
      primary_contact_email: '',
      primary_contact_phone: ''
    });
    setEditMode(false);
  };

  const resetProductForm = () => {
    setProductForm({
      name: '',
      description: '',
      category: '',
      sku: '',
      base_price: '',
      currency: 'USD',
      pricing_model: 'one_time',
      economic_unit_label: '',
      usage_volume_label: ''
    });
  };

  const openEditDialog = () => {
    if (!selectedPartner) return;
    setPartnerForm({
      name: selectedPartner.name || '',
      partner_type: selectedPartner.partner_type || 'channel',
      status: selectedPartner.status || 'prospect',
      description: selectedPartner.description || '',
      territory: selectedPartner.territory || '',
      primary_contact_name: selectedPartner.primary_contact_name || '',
      primary_contact_email: selectedPartner.primary_contact_email || '',
      primary_contact_phone: selectedPartner.primary_contact_phone || ''
    });
    setEditMode(true);
    setShowCreateDialog(true);
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Partner Management</h1>
          <p className="text-muted-foreground">Manage partners for Partner Sales motion</p>
        </div>
        <Button onClick={() => { resetPartnerForm(); setShowCreateDialog(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          New Partner
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">{total}</div>
                <p className="text-sm text-muted-foreground">Total Partners</p>
              </div>
              <Building2 className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">
                  {partners.filter(p => p.status === 'active').length}
                </div>
                <p className="text-sm text-muted-foreground">Active</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">
                  {partners.filter(p => p.status === 'prospect').length}
                </div>
                <p className="text-sm text-muted-foreground">Prospects</p>
              </div>
              <Clock className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold">
                  {partners.reduce((sum, p) => sum + (p.active_deals || 0), 0)}
                </div>
                <p className="text-sm text-muted-foreground">Active Deals</p>
              </div>
              <TrendingUp className="w-8 h-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search partners..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="prospect">Prospect</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="channel">Channel</SelectItem>
                <SelectItem value="reseller">Reseller</SelectItem>
                <SelectItem value="technology">Technology</SelectItem>
                <SelectItem value="strategic">Strategic</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={loadPartners}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Partners Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Partner</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Territory</TableHead>
                <TableHead>Products</TableHead>
                <TableHead>Active Deals</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : partners.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No partners found. Create your first partner to get started.
                  </TableCell>
                </TableRow>
              ) : (
                partners.map(partner => (
                  <TableRow 
                    key={partner.id} 
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => loadPartnerDetails(partner.id)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                          <Building2 className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{partner.name}</p>
                          <p className="text-sm text-muted-foreground truncate max-w-[200px]">
                            {partner.description || 'No description'}
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={typeColors[partner.partner_type]}>
                        {partner.partner_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusColors[partner.status]}>
                        {partner.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{partner.territory || '-'}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        <Package className="w-3 h-3 mr-1" />
                        {partner.products?.length || 0}
                      </Badge>
                    </TableCell>
                    <TableCell>{partner.active_deals || 0}</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); loadPartnerDetails(partner.id); }}>
                            <Edit className="w-4 h-4 mr-2" /> View Details
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            className="text-destructive"
                            onClick={(e) => { e.stopPropagation(); deletePartner(partner.id); }}
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
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} partners
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Create/Edit Partner Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editMode ? 'Edit Partner' : 'Create New Partner'}</DialogTitle>
            <DialogDescription>
              {editMode ? 'Update partner information' : 'Add a new partner for Partner Sales motion'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Partner Name *</Label>
              <Input
                value={partnerForm.name}
                onChange={(e) => setPartnerForm({...partnerForm, name: e.target.value})}
                placeholder="e.g., Frylow"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={partnerForm.partner_type} onValueChange={(v) => setPartnerForm({...partnerForm, partner_type: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="channel">Channel</SelectItem>
                    <SelectItem value="reseller">Reseller</SelectItem>
                    <SelectItem value="technology">Technology</SelectItem>
                    <SelectItem value="strategic">Strategic</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={partnerForm.status} onValueChange={(v) => setPartnerForm({...partnerForm, status: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="prospect">Prospect</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Territory</Label>
              <Input
                value={partnerForm.territory}
                onChange={(e) => setPartnerForm({...partnerForm, territory: e.target.value})}
                placeholder="e.g., North America"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={partnerForm.description}
                onChange={(e) => setPartnerForm({...partnerForm, description: e.target.value})}
                placeholder="Brief description of the partner..."
                rows={2}
              />
            </div>
            
            <div className="border-t pt-4">
              <h4 className="font-medium mb-3">Primary Contact</h4>
              <div className="space-y-3">
                <Input
                  value={partnerForm.primary_contact_name}
                  onChange={(e) => setPartnerForm({...partnerForm, primary_contact_name: e.target.value})}
                  placeholder="Contact Name"
                />
                <div className="grid grid-cols-2 gap-3">
                  <Input
                    value={partnerForm.primary_contact_email}
                    onChange={(e) => setPartnerForm({...partnerForm, primary_contact_email: e.target.value})}
                    placeholder="Email"
                    type="email"
                  />
                  <Input
                    value={partnerForm.primary_contact_phone}
                    onChange={(e) => setPartnerForm({...partnerForm, primary_contact_phone: e.target.value})}
                    placeholder="Phone"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => { setShowCreateDialog(false); resetPartnerForm(); }}>
              Cancel
            </Button>
            <Button onClick={savePartner} disabled={saving || !partnerForm.name}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              {editMode ? 'Save Changes' : 'Create Partner'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Product Dialog */}
      <Dialog open={showProductDialog} onOpenChange={setShowProductDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Add Product</DialogTitle>
            <DialogDescription>
              Add a new product for {selectedPartner?.name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Product Name *</Label>
              <Input
                value={productForm.name}
                onChange={(e) => setProductForm({...productForm, name: e.target.value})}
                placeholder="e.g., Oil Extender System"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Category</Label>
                <Input
                  value={productForm.category}
                  onChange={(e) => setProductForm({...productForm, category: e.target.value})}
                  placeholder="e.g., Equipment"
                />
              </div>
              <div className="space-y-2">
                <Label>SKU</Label>
                <Input
                  value={productForm.sku}
                  onChange={(e) => setProductForm({...productForm, sku: e.target.value})}
                  placeholder="e.g., FRY-001"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Base Price</Label>
                <Input
                  type="number"
                  value={productForm.base_price}
                  onChange={(e) => setProductForm({...productForm, base_price: e.target.value})}
                  placeholder="0.00"
                />
              </div>
              <div className="space-y-2">
                <Label>Currency</Label>
                <Select value={productForm.currency} onValueChange={(v) => setProductForm({...productForm, currency: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="GBP">GBP</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Pricing Model</Label>
                <Select value={productForm.pricing_model} onValueChange={(v) => setProductForm({...productForm, pricing_model: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="one_time">One-Time</SelectItem>
                    <SelectItem value="recurring">Recurring</SelectItem>
                    <SelectItem value="usage_based">Usage Based</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={productForm.description}
                onChange={(e) => setProductForm({...productForm, description: e.target.value})}
                placeholder="Product description..."
                rows={2}
              />
            </div>
            
            <div className="border-t pt-4">
              <h4 className="font-medium mb-3">Lead Scoring Labels</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Economic Unit Label</Label>
                  <Input
                    value={productForm.economic_unit_label}
                    onChange={(e) => setProductForm({...productForm, economic_unit_label: e.target.value})}
                    placeholder="e.g., fryers, locations"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Usage Volume Label</Label>
                  <Input
                    value={productForm.usage_volume_label}
                    onChange={(e) => setProductForm({...productForm, usage_volume_label: e.target.value})}
                    placeholder="e.g., gallons, users"
                  />
                </div>
              </div>
            </div>
          </div>
          
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => { setShowProductDialog(false); resetProductForm(); }}>
              Cancel
            </Button>
            <Button onClick={createProduct} disabled={saving || !productForm.name}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Add Product
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Partner Detail Sheet */}
      <Sheet open={showDetailSheet} onOpenChange={setShowDetailSheet}>
        <SheetContent className="w-[500px] sm:w-[600px] overflow-y-auto">
          {selectedPartner && (
            <>
              <SheetHeader>
                <div className="flex items-center justify-between">
                  <SheetTitle className="flex items-center gap-3">
                    {selectedPartner.name}
                    <Badge variant="outline" className={statusColors[selectedPartner.status]}>
                      {selectedPartner.status}
                    </Badge>
                  </SheetTitle>
                  <Button variant="outline" size="sm" onClick={openEditDialog}>
                    <Edit className="w-4 h-4 mr-1" /> Edit
                  </Button>
                </div>
                <SheetDescription>
                  {selectedPartner.description || 'No description'}
                </SheetDescription>
              </SheetHeader>
              
              <div className="mt-6 space-y-6">
                {/* Partner Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Type</p>
                    <Badge variant="outline" className={typeColors[selectedPartner.partner_type]}>
                      {selectedPartner.partner_type}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Territory</p>
                    <p className="font-medium">{selectedPartner.territory || '-'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Active Deals</p>
                    <p className="font-medium">{selectedPartner.active_deals || 0}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Won Deals</p>
                    <p className="font-medium">{selectedPartner.won_deals || 0}</p>
                  </div>
                </div>
                
                {/* Contact */}
                {selectedPartner.primary_contact_name && (
                  <div className="p-4 bg-muted rounded-lg">
                    <h4 className="font-medium mb-2">Primary Contact</h4>
                    <p className="font-medium">{selectedPartner.primary_contact_name}</p>
                    <p className="text-sm text-muted-foreground">{selectedPartner.primary_contact_email}</p>
                    <p className="text-sm text-muted-foreground">{selectedPartner.primary_contact_phone}</p>
                  </div>
                )}
                
                {/* Products */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium">Products ({selectedPartner.products?.length || 0})</h4>
                    <Button size="sm" onClick={() => setShowProductDialog(true)}>
                      <Plus className="w-4 h-4 mr-1" /> Add Product
                    </Button>
                  </div>
                  
                  {selectedPartner.products?.length > 0 ? (
                    <div className="space-y-2">
                      {selectedPartner.products.map(product => (
                        <div key={product.id} className="p-3 border rounded-lg flex items-center justify-between">
                          <div>
                            <p className="font-medium">{product.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {product.category} • {product.base_price ? `$${product.base_price}` : 'No price set'}
                            </p>
                          </div>
                          <Button variant="ghost" size="sm" onClick={() => deleteProduct(product.id)}>
                            <Trash2 className="w-4 h-4 text-destructive" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No products yet. Add a product to enable Partner Sales.
                    </p>
                  )}
                </div>
                
                {/* Delete */}
                <div className="pt-4 border-t">
                  <Button 
                    variant="destructive" 
                    className="w-full"
                    onClick={() => deletePartner(selectedPartner.id)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" /> Delete Partner
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default PartnersPage;
