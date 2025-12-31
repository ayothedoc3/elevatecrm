import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { ScrollArea } from '../../components/ui/scroll-area';
import { Skeleton } from '../../components/ui/skeleton';
import {
  Flame, LogOut, Link2, DollarSign, MousePointerClick, Users, TrendingUp,
  Copy, ExternalLink, Plus, RefreshCw, Image, Download, FileText, Loader2,
  ChevronRight, ArrowUpRight, ArrowDownRight, BarChart3, Eye, Package
} from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AffiliateDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [affiliate, setAffiliate] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [links, setLinks] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [commissions, setCommissions] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedProgram, setSelectedProgram] = useState('');
  const [customSlug, setCustomSlug] = useState('');
  const [landingPageUrl, setLandingPageUrl] = useState('');

  const token = localStorage.getItem('affiliate_token');
  const api = axios.create({
    baseURL: `${BACKEND_URL}/api/affiliate-portal`,
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchData = useCallback(async () => {
    if (!token) {
      navigate('/affiliate-portal/login');
      return;
    }

    setLoading(true);
    try {
      const [dashRes, linksRes, progsRes, commsRes, matsRes] = await Promise.all([
        api.get('/dashboard'),
        api.get('/links'),
        api.get('/programs'),
        api.get('/commissions?page_size=10'),
        api.get('/materials?page_size=12')
      ]);

      setDashboard(dashRes.data);
      setAffiliate(dashRes.data.affiliate);
      setLinks(linksRes.data.links || []);
      setPrograms(progsRes.data.programs || []);
      setCommissions(commsRes.data.commissions || []);
      setMaterials(matsRes.data.materials || []);
    } catch (error) {
      if (error.response?.status === 401) {
        localStorage.removeItem('affiliate_token');
        localStorage.removeItem('affiliate_data');
        navigate('/affiliate-portal/login');
      } else {
        toast.error('Failed to load data');
      }
    } finally {
      setLoading(false);
    }
  }, [token, navigate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleLogout = () => {
    localStorage.removeItem('affiliate_token');
    localStorage.removeItem('affiliate_data');
    navigate('/affiliate-portal/login');
  };

  const createLink = async () => {
    if (!selectedProgram) {
      toast.error('Please select a program');
      return;
    }

    setCreating(true);
    try {
      await api.post('/links', {
        program_id: selectedProgram,
        custom_slug: customSlug || undefined,
        landing_page_url: landingPageUrl || undefined
      });

      toast.success('Referral link created!');
      setShowLinkDialog(false);
      setSelectedProgram('');
      setCustomSlug('');
      setLandingPageUrl('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create link');
    } finally {
      setCreating(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(`${window.location.origin}/ref/${text}`);
    toast.success('Link copied!');
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount || 0);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-7xl mx-auto p-6 space-y-6">
          <Skeleton className="h-10 w-48" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32" />)}
          </div>
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-500 rounded-lg flex items-center justify-center">
              <Flame className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold">Affiliate Portal</h1>
              <p className="text-sm text-muted-foreground">Welcome, {affiliate?.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={fetchData}>
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button variant="outline" onClick={handleLogout}>
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Earnings</p>
                  <p className="text-2xl font-bold">{formatCurrency(affiliate?.total_earnings)}</p>
                </div>
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                  <DollarSign className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Clicks</p>
                  <p className="text-2xl font-bold">{dashboard?.stats?.total_clicks || 0}</p>
                </div>
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                  <MousePointerClick className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Conversions</p>
                  <p className="text-2xl font-bold">{dashboard?.stats?.total_conversions || 0}</p>
                </div>
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Conversion Rate</p>
                  <p className="text-2xl font-bold">{dashboard?.stats?.conversion_rate || 0}%</p>
                </div>
                <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-full flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-orange-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="links" className="space-y-4">
          <TabsList>
            <TabsTrigger value="links">My Links</TabsTrigger>
            <TabsTrigger value="programs">Programs</TabsTrigger>
            <TabsTrigger value="commissions">Commissions</TabsTrigger>
            <TabsTrigger value="materials">Marketing Materials</TabsTrigger>
          </TabsList>

          {/* Links Tab */}
          <TabsContent value="links" className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Your Referral Links</h2>
              <Dialog open={showLinkDialog} onOpenChange={setShowLinkDialog}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Link
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Referral Link</DialogTitle>
                    <DialogDescription>Generate a new referral link for a program</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Program *</Label>
                      <Select value={selectedProgram} onValueChange={setSelectedProgram}>
                        <SelectTrigger><SelectValue placeholder="Select a program" /></SelectTrigger>
                        <SelectContent>
                          {programs.map(prog => (
                            <SelectItem key={prog.id} value={prog.id}>
                              {prog.name} ({prog.commission_type === 'percentage' ? `${prog.commission_value}%` : formatCurrency(prog.commission_value)})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Custom Slug (optional)</Label>
                      <Input
                        value={customSlug}
                        onChange={(e) => setCustomSlug(e.target.value)}
                        placeholder="my-custom-link"
                      />
                      <p className="text-xs text-muted-foreground">Leave empty for auto-generated code</p>
                    </div>
                    <div className="space-y-2">
                      <Label>Landing Page URL (optional)</Label>
                      <Input
                        value={landingPageUrl}
                        onChange={(e) => setLandingPageUrl(e.target.value)}
                        placeholder="https://yoursite.com/landing"
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setShowLinkDialog(false)}>Cancel</Button>
                    <Button onClick={createLink} disabled={creating}>
                      {creating && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      Create Link
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>

            {links.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Link2 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-semibold mb-2">No Referral Links</h3>
                  <p className="text-muted-foreground mb-4">Create your first referral link to start earning</p>
                  <Button onClick={() => setShowLinkDialog(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Link
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {links.map(link => (
                  <Card key={link.id}>
                    <CardContent className="py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <code className="bg-muted px-2 py-1 rounded text-sm font-mono">
                              {link.referral_code}
                            </code>
                            <Badge variant={link.is_active ? 'default' : 'secondary'}>
                              {link.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                            {link.program && (
                              <Badge variant="outline">{link.program.name}</Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground truncate max-w-md">
                            {link.full_url || `${window.location.origin}/ref/${link.referral_code}`}
                          </p>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="text-center">
                            <p className="text-xl font-bold">{link.click_count}</p>
                            <p className="text-xs text-muted-foreground">Clicks</p>
                          </div>
                          <div className="text-center">
                            <p className="text-xl font-bold">{link.conversion_count}</p>
                            <p className="text-xs text-muted-foreground">Conversions</p>
                          </div>
                          <Button variant="outline" size="icon" onClick={() => copyToClipboard(link.referral_code)}>
                            <Copy className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Programs Tab */}
          <TabsContent value="programs" className="space-y-4">
            <h2 className="text-lg font-semibold">Available Programs</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {programs.map(prog => (
                <Card key={prog.id}>
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-lg">{prog.name}</CardTitle>
                        <CardDescription>{prog.description}</CardDescription>
                      </div>
                      <Badge>{prog.journey_type === 'demo_first' ? 'Demo First' : 'Direct Checkout'}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Commission</p>
                        <p className="font-semibold">
                          {prog.commission_type === 'percentage' ? `${prog.commission_value}%` : formatCurrency(prog.commission_value)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Cookie Duration</p>
                        <p className="font-semibold">{prog.cookie_duration_days} days</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Attribution</p>
                        <p className="font-semibold capitalize">{prog.attribution_model?.replace('_', ' ')}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Min Payout</p>
                        <p className="font-semibold">{formatCurrency(prog.min_payout_threshold)}</p>
                      </div>
                    </div>
                    <Button className="w-full mt-4" variant={prog.has_link ? 'outline' : 'default'} onClick={() => {
                      if (!prog.has_link) {
                        setSelectedProgram(prog.id);
                        setShowLinkDialog(true);
                      }
                    }}>
                      {prog.has_link ? 'Link Created' : 'Create Link'}
                      <ChevronRight className="w-4 h-4 ml-2" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Commissions Tab */}
          <TabsContent value="commissions" className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Your Commissions</h2>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="bg-yellow-100 text-yellow-800">
                  Pending: {formatCurrency(dashboard?.pending_payout)}
                </Badge>
              </div>
            </div>
            
            {commissions.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <DollarSign className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-semibold mb-2">No Commissions Yet</h3>
                  <p className="text-muted-foreground">Share your links to start earning</p>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-0">
                  <div className="divide-y">
                    {commissions.map(comm => (
                      <div key={comm.id} className="flex items-center justify-between p-4">
                        <div>
                          <p className="font-medium">{comm.program_name}</p>
                          <p className="text-sm text-muted-foreground">
                            {new Date(comm.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex items-center gap-4">
                          <Badge variant={
                            comm.status === 'paid' ? 'default' :
                            comm.status === 'approved' ? 'secondary' :
                            'outline'
                          }>
                            {comm.status}
                          </Badge>
                          <span className="font-semibold">{formatCurrency(comm.amount)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Materials Tab */}
          <TabsContent value="materials" className="space-y-4">
            <h2 className="text-lg font-semibold">Marketing Materials</h2>
            {materials.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Image className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-semibold mb-2">No Materials Available</h3>
                  <p className="text-muted-foreground">Marketing materials will appear here</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {materials.map(mat => (
                  <Card key={mat.id} className="overflow-hidden">
                    <div className="aspect-video bg-muted flex items-center justify-center">
                      {mat.material_type === 'image' && mat.file_url ? (
                        <img src={mat.file_url} alt={mat.name} className="w-full h-full object-cover" />
                      ) : mat.material_type === 'pdf' ? (
                        <FileText className="w-8 h-8 text-muted-foreground" />
                      ) : (
                        <Package className="w-8 h-8 text-muted-foreground" />
                      )}
                    </div>
                    <CardContent className="p-3">
                      <p className="font-medium text-sm truncate">{mat.name}</p>
                      <div className="flex items-center justify-between mt-2">
                        <Badge variant="outline" className="text-xs">{mat.category?.replace('_', ' ')}</Badge>
                        {mat.file_url && (
                          <Button variant="ghost" size="icon" className="h-7 w-7" asChild>
                            <a href={mat.file_url} target="_blank" rel="noopener noreferrer">
                              <Download className="w-3 h-3" />
                            </a>
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AffiliateDashboard;
