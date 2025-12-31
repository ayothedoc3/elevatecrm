import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '../components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Skeleton } from '../components/ui/skeleton';
import { Separator } from '../components/ui/separator';
import { Switch } from '../components/ui/switch';
import {
  Wand2, Plus, Search, Filter, Eye, Edit, Trash2, Copy, ExternalLink,
  RefreshCw, Loader2, Globe, FileText, LayoutTemplate, Sparkles,
  ChevronRight, MoreVertical, Clock, Check, X, ArrowUp, ArrowDown,
  Palette, Type, Image, MousePointerClick, Star, HelpCircle, Target, Zap
} from 'lucide-react';
import { toast } from 'sonner';

const PAGE_TYPES = [
  { value: 'affiliate_recruitment', label: 'Affiliate Recruitment', icon: Target },
  { value: 'affiliate_product', label: 'Affiliate Product', icon: Star },
  { value: 'product_sales', label: 'Product Sales', icon: Zap },
  { value: 'demo_booking', label: 'Demo Booking', icon: MousePointerClick },
  { value: 'lead_magnet', label: 'Lead Magnet', icon: FileText },
  { value: 'generic', label: 'Generic Page', icon: LayoutTemplate }
];

const CTA_TYPES = [
  { value: 'signup', label: 'Sign Up' },
  { value: 'book_demo', label: 'Book Demo' },
  { value: 'checkout', label: 'Checkout' },
  { value: 'download', label: 'Download' }
];

const TONES = [
  { value: 'professional', label: 'Professional' },
  { value: 'bold', label: 'Bold & Energetic' },
  { value: 'friendly', label: 'Friendly & Casual' },
  { value: 'premium', label: 'Premium & Luxurious' }
];

const AI_MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o (Recommended)', provider: 'OpenAI' },
  { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini (Fast)', provider: 'OpenAI' },
  { value: 'gpt-5.2', label: 'GPT-5.2 (Latest)', provider: 'OpenAI' }
];

const LandingPagesPage = () => {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [pages, setPages] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [total, setTotal] = useState(0);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [selectedPage, setSelectedPage] = useState(null);
  const [editingSection, setEditingSection] = useState(null);
  const [editingSectionIndex, setEditingSectionIndex] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [generatedSchema, setGeneratedSchema] = useState(null);
  const [activeTab, setActiveTab] = useState('pages');

  // Generation form
  const [genForm, setGenForm] = useState({
    page_type: 'generic',
    page_goal: '',
    target_audience: '',
    offer_details: '',
    cta_type: 'signup',
    tone: 'professional',
    brand_name: '',
    brand_colors: { primary: '#FF6B35', secondary: '#1A1A2E', accent: '#4ECDC4' },
    affiliate_program_id: '',
    product_features: '',
    additional_context: '',
    ai_model: 'gpt-4o'
  });

  // Create form
  const [createForm, setCreateForm] = useState({
    name: '',
    page_type: 'generic',
    affiliate_program_id: ''
  });

  const api = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [pagesRes, programsRes] = await Promise.all([
        api.get('/landing-pages'),
        api.get('/affiliates/programs')
      ]);
      setPages(pagesRes.data.pages || []);
      setTotal(pagesRes.data.total || 0);
      setPrograms(programsRes.data.programs || []);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Failed to load landing pages');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleGenerate = async () => {
    if (!genForm.page_goal || !genForm.target_audience || !genForm.offer_details) {
      toast.error('Please fill in all required fields');
      return;
    }

    setGenerating(true);
    try {
      const response = await api.post('/landing-pages/generate', {
        ...genForm,
        product_features: genForm.product_features ? genForm.product_features.split('\n').filter(Boolean) : []
      });

      setGeneratedSchema(response.data.page_schema);
      setActiveTab('preview');
      toast.success('Landing page generated!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate page');
    } finally {
      setGenerating(false);
    }
  };

  const handleSavePage = async () => {
    if (!createForm.name || !generatedSchema) {
      toast.error('Please provide a name for the page');
      return;
    }

    setSaving(true);
    try {
      await api.post('/landing-pages', {
        name: createForm.name,
        page_type: genForm.page_type,
        page_schema: generatedSchema,
        affiliate_program_id: genForm.affiliate_program_id || null
      });

      toast.success('Landing page saved!');
      setShowCreateDialog(false);
      setGeneratedSchema(null);
      setActiveTab('pages');
      resetForms();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save page');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async (pageId) => {
    try {
      const response = await api.post(`/landing-pages/${pageId}/publish`);
      toast.success(`Page published at ${response.data.url}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to publish page');
    }
  };

  const handleUnpublish = async (pageId) => {
    try {
      await api.post(`/landing-pages/${pageId}/unpublish`);
      toast.success('Page unpublished');
      fetchData();
    } catch (error) {
      toast.error('Failed to unpublish page');
    }
  };

  const handleDelete = async (pageId) => {
    if (!window.confirm('Are you sure you want to delete this page?')) return;
    try {
      await api.delete(`/landing-pages/${pageId}`);
      toast.success('Page deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete page');
    }
  };

  const resetForms = () => {
    setGenForm({
      page_type: 'generic',
      page_goal: '',
      target_audience: '',
      offer_details: '',
      cta_type: 'signup',
      tone: 'professional',
      brand_name: '',
      brand_colors: { primary: '#FF6B35', secondary: '#1A1A2E', accent: '#4ECDC4' },
      affiliate_program_id: '',
      product_features: '',
      additional_context: '',
      ai_model: 'gpt-4o'
    });
    setCreateForm({ name: '', page_type: 'generic', affiliate_program_id: '' });
  };

  const copySlug = async (slug) => {
    const url = `${window.location.origin}/pages/${slug}`;
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(url);
        toast.success('URL copied to clipboard');
      } else {
        // Fallback for non-secure contexts or blocked clipboard
        const textArea = document.createElement('textarea');
        textArea.value = url;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        try {
          document.execCommand('copy');
          toast.success('URL copied to clipboard');
        } catch (err) {
          // If all else fails, show the URL in a prompt
          toast.info(`Copy this URL: ${url}`);
          prompt('Copy this URL:', url);
        }
        document.body.removeChild(textArea);
      }
    } catch (err) {
      // Show URL in prompt as final fallback
      toast.info(`Copy this URL: ${url}`);
      prompt('Copy this URL:', url);
    }
  };

  const handlePreview = async (page) => {
    setSelectedPage(page);
    // Fetch full page data if needed
    try {
      const response = await api.get(`/landing-pages/${page.id}`);
      setSelectedPage(response.data);
      setShowPreviewDialog(true);
    } catch (error) {
      toast.error('Failed to load page preview');
    }
  };

  const handleEditPage = async (page) => {
    try {
      const response = await api.get(`/landing-pages/${page.id}`);
      setSelectedPage(response.data);
      setShowEditDialog(true);
    } catch (error) {
      toast.error('Failed to load page for editing');
    }
  };

  const handleEditSection = (section, index) => {
    setEditingSection({ ...section });
    setEditingSectionIndex(index);
  };

  const handleSaveSection = async () => {
    if (!selectedPage || editingSectionIndex === null) return;
    
    setSaving(true);
    try {
      const updatedSections = [...selectedPage.page_schema.sections];
      updatedSections[editingSectionIndex] = editingSection;
      
      const updatedSchema = {
        ...selectedPage.page_schema,
        sections: updatedSections
      };
      
      await api.put(`/landing-pages/${selectedPage.id}`, {
        page_schema: updatedSchema
      });
      
      setSelectedPage({
        ...selectedPage,
        page_schema: updatedSchema
      });
      
      setEditingSection(null);
      setEditingSectionIndex(null);
      toast.success('Section updated!');
      fetchData();
    } catch (error) {
      toast.error('Failed to save section');
    } finally {
      setSaving(false);
    }
  };

  const handleMoveSection = async (fromIndex, direction) => {
    if (!selectedPage) return;
    
    const toIndex = direction === 'up' ? fromIndex - 1 : fromIndex + 1;
    if (toIndex < 0 || toIndex >= selectedPage.page_schema.sections.length) return;
    
    const sections = [...selectedPage.page_schema.sections];
    [sections[fromIndex], sections[toIndex]] = [sections[toIndex], sections[fromIndex]];
    
    // Update order numbers
    sections.forEach((s, i) => s.order = i + 1);
    
    const updatedSchema = { ...selectedPage.page_schema, sections };
    
    try {
      await api.put(`/landing-pages/${selectedPage.id}`, { page_schema: updatedSchema });
      setSelectedPage({ ...selectedPage, page_schema: updatedSchema });
      toast.success('Section moved');
    } catch (error) {
      toast.error('Failed to move section');
    }
  };

  const handleDeleteSection = async (index) => {
    if (!selectedPage || !window.confirm('Delete this section?')) return;
    
    const sections = selectedPage.page_schema.sections.filter((_, i) => i !== index);
    sections.forEach((s, i) => s.order = i + 1);
    
    const updatedSchema = { ...selectedPage.page_schema, sections };
    
    try {
      await api.put(`/landing-pages/${selectedPage.id}`, { page_schema: updatedSchema });
      setSelectedPage({ ...selectedPage, page_schema: updatedSchema });
      toast.success('Section deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete section');
    }
  };

  const filteredPages = pages.filter(p => {
    if (statusFilter !== 'all' && p.status !== statusFilter) return false;
    if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'published': return <Badge className="bg-green-100 text-green-800">Published</Badge>;
      case 'draft': return <Badge variant="outline">Draft</Badge>;
      case 'archived': return <Badge variant="secondary">Archived</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  const renderSectionPreview = (section) => {
    const sectionStyles = {
      hero: 'bg-gradient-to-r from-orange-500 to-red-500 text-white',
      features: 'bg-gray-50 dark:bg-gray-800',
      benefits: 'bg-white dark:bg-gray-900',
      social_proof: 'bg-gray-100 dark:bg-gray-800',
      faq: 'bg-white dark:bg-gray-900',
      cta: 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
    };

    return (
      <div key={section.order} className={`p-6 rounded-lg mb-4 ${sectionStyles[section.type] || 'bg-gray-50'}`}>
        <Badge className="mb-2">{section.type.toUpperCase()}</Badge>
        {section.headline && <h3 className="text-xl font-bold mb-2">{section.headline}</h3>}
        {section.subheadline && <p className="text-sm opacity-80 mb-3">{section.subheadline}</p>}
        {section.body_text && <p className="mb-3">{section.body_text}</p>}
        {section.items && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
            {section.items.slice(0, 3).map((item, idx) => (
              <div key={idx} className="p-3 bg-white/10 rounded">
                <p className="font-semibold">{item.title || item.question}</p>
                <p className="text-sm opacity-80">{item.description || item.answer}</p>
              </div>
            ))}
          </div>
        )}
        {section.cta_text && (
          <Button className="mt-4" variant={section.type === 'cta' ? 'secondary' : 'default'}>
            {section.cta_text}
          </Button>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <LayoutTemplate className="w-6 h-6" />
            Landing Page Builder
          </h1>
          <p className="text-muted-foreground">Create AI-powered landing pages for affiliates and products</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button onClick={() => { resetForms(); setGeneratedSchema(null); setActiveTab('generate'); }}>
                <Wand2 className="w-4 h-4 mr-2" />
                Create with AI
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-orange-500" />
                  AI Landing Page Generator
                </DialogTitle>
                <DialogDescription>Generate a high-converting landing page in seconds</DialogDescription>
              </DialogHeader>
              
              <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="generate">1. Configure</TabsTrigger>
                  <TabsTrigger value="preview" disabled={!generatedSchema}>2. Preview</TabsTrigger>
                  <TabsTrigger value="save" disabled={!generatedSchema}>3. Save</TabsTrigger>
                </TabsList>

                <ScrollArea className="flex-1 mt-4">
                  {/* Generate Tab */}
                  <TabsContent value="generate" className="space-y-4 pr-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Page Type *</Label>
                        <Select value={genForm.page_type} onValueChange={(v) => setGenForm({...genForm, page_type: v})}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {PAGE_TYPES.map(t => (
                              <SelectItem key={t.value} value={t.value}>
                                <div className="flex items-center gap-2">
                                  <t.icon className="w-4 h-4" />
                                  {t.label}
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>AI Model</Label>
                        <Select value={genForm.ai_model} onValueChange={(v) => setGenForm({...genForm, ai_model: v})}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {AI_MODELS.map(m => (
                              <SelectItem key={m.value} value={m.value}>
                                <div className="flex items-center justify-between w-full">
                                  <span>{m.label}</span>
                                  <Badge variant="outline" className="ml-2 text-xs">{m.provider}</Badge>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Page Goal *</Label>
                      <Textarea
                        value={genForm.page_goal}
                        onChange={(e) => setGenForm({...genForm, page_goal: e.target.value})}
                        placeholder="e.g., Recruit affiliates for Frylow oil-saving product with 10% commission"
                        rows={2}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Target Audience *</Label>
                      <Textarea
                        value={genForm.target_audience}
                        onChange={(e) => setGenForm({...genForm, target_audience: e.target.value})}
                        placeholder="e.g., Restaurant owners, food bloggers, culinary influencers looking for passive income"
                        rows={2}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Offer Details *</Label>
                      <Textarea
                        value={genForm.offer_details}
                        onChange={(e) => setGenForm({...genForm, offer_details: e.target.value})}
                        placeholder="e.g., 10% commission on every sale, 30-day cookie, marketing materials provided, dedicated support"
                        rows={2}
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>CTA Type</Label>
                        <Select value={genForm.cta_type} onValueChange={(v) => setGenForm({...genForm, cta_type: v})}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {CTA_TYPES.map(t => (
                              <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Tone</Label>
                        <Select value={genForm.tone} onValueChange={(v) => setGenForm({...genForm, tone: v})}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {TONES.map(t => (
                              <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <Separator />

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Brand Name</Label>
                        <Input
                          value={genForm.brand_name}
                          onChange={(e) => setGenForm({...genForm, brand_name: e.target.value})}
                          placeholder="e.g., Frylow"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Affiliate Program</Label>
                        <Select value={genForm.affiliate_program_id || "none"} onValueChange={(v) => setGenForm({...genForm, affiliate_program_id: v === "none" ? "" : v})}>
                          <SelectTrigger><SelectValue placeholder="Select program (optional)" /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">None</SelectItem>
                            {programs.map(p => (
                              <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Product Features (one per line)</Label>
                      <Textarea
                        value={genForm.product_features}
                        onChange={(e) => setGenForm({...genForm, product_features: e.target.value})}
                        placeholder="Saves up to 50% on oil costs&#10;Easy installation&#10;30-day money back guarantee"
                        rows={3}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Additional Context</Label>
                      <Textarea
                        value={genForm.additional_context}
                        onChange={(e) => setGenForm({...genForm, additional_context: e.target.value})}
                        placeholder="Any additional information to help generate better copy..."
                        rows={2}
                      />
                    </div>
                  </TabsContent>

                  {/* Preview Tab */}
                  <TabsContent value="preview" className="pr-4">
                    {generatedSchema ? (
                      <div className="space-y-4">
                        <Card>
                          <CardHeader>
                            <CardTitle className="text-lg">{generatedSchema.page_title}</CardTitle>
                            <CardDescription>{generatedSchema.meta_description}</CardDescription>
                          </CardHeader>
                        </Card>
                        
                        <div className="space-y-2">
                          {generatedSchema.sections?.map(section => renderSectionPreview(section))}
                        </div>

                        {generatedSchema.conversion_rationale && (
                          <Card>
                            <CardHeader>
                              <CardTitle className="text-sm flex items-center gap-2">
                                <Sparkles className="w-4 h-4" />
                                AI Conversion Strategy
                              </CardTitle>
                            </CardHeader>
                            <CardContent>
                              <p className="text-sm text-muted-foreground">{generatedSchema.conversion_rationale}</p>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-12">
                        <Wand2 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                        <p>Generate a page first to preview</p>
                      </div>
                    )}
                  </TabsContent>

                  {/* Save Tab */}
                  <TabsContent value="save" className="pr-4">
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label>Page Name *</Label>
                        <Input
                          value={createForm.name}
                          onChange={(e) => setCreateForm({...createForm, name: e.target.value})}
                          placeholder="e.g., Frylow Affiliate Recruitment Page"
                        />
                      </div>
                      
                      <Card>
                        <CardContent className="pt-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium">Ready to save</p>
                              <p className="text-sm text-muted-foreground">
                                {generatedSchema?.sections?.length || 0} sections generated
                              </p>
                            </div>
                            <Badge>{genForm.page_type.replace('_', ' ')}</Badge>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </TabsContent>
                </ScrollArea>
              </Tabs>

              <DialogFooter className="mt-4">
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                {activeTab === 'generate' && (
                  <Button onClick={handleGenerate} disabled={generating}>
                    {generating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Wand2 className="w-4 h-4 mr-2" />
                        Generate Page
                      </>
                    )}
                  </Button>
                )}
                {activeTab === 'preview' && generatedSchema && (
                  <Button onClick={() => setActiveTab('save')}>
                    Continue to Save
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </Button>
                )}
                {activeTab === 'save' && (
                  <Button onClick={handleSavePage} disabled={saving || !createForm.name}>
                    {saving ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4 mr-2" />
                        Save Page
                      </>
                    )}
                  </Button>
                )}
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search pages..."
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="published">Published</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Pages Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-48" />)}
        </div>
      ) : filteredPages.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <LayoutTemplate className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-semibold mb-2">No Landing Pages</h3>
            <p className="text-muted-foreground mb-4">Create your first AI-powered landing page</p>
            <Button onClick={() => { resetForms(); setGeneratedSchema(null); setActiveTab('generate'); setShowCreateDialog(true); }}>
              <Wand2 className="w-4 h-4 mr-2" />
              Create with AI
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPages.map(page => (
            <Card key={page.id} className="overflow-hidden hover:shadow-lg transition-shadow">
              <div className="h-32 bg-gradient-to-br from-orange-500 to-red-500 p-4 flex items-end">
                <h3 className="font-bold text-white text-lg truncate">{page.name}</h3>
              </div>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  {getStatusBadge(page.status)}
                  <span className="text-xs text-muted-foreground">v{page.version}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                  <span className="flex items-center gap-1">
                    <Eye className="w-3 h-3" />
                    {page.view_count || 0}
                  </span>
                  <span className="flex items-center gap-1">
                    <MousePointerClick className="w-3 h-3" />
                    {page.conversion_count || 0}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground truncate mb-3">
                  /{page.slug}
                </p>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => handlePreview(page)}>
                    <Eye className="w-3 h-3" />
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleEditPage(page)}>
                    <Edit className="w-3 h-3" />
                  </Button>
                  {page.status === 'draft' ? (
                    <Button size="sm" className="flex-1" onClick={() => handlePublish(page.id)}>
                      <Globe className="w-3 h-3 mr-1" />
                      Publish
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" className="flex-1" onClick={() => handleUnpublish(page.id)}>
                      Unpublish
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={() => copySlug(page.slug)}>
                    <Copy className="w-3 h-3" />
                  </Button>
                  <Button size="sm" variant="outline" className="text-destructive" onClick={() => handleDelete(page.id)}>
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Preview Dialog */}
      <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5" />
              Page Preview: {selectedPage?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedPage?.status === 'published' ? (
                <span className="text-green-600">Published at /{selectedPage?.slug}</span>
              ) : (
                <span className="text-muted-foreground">Draft - not yet published</span>
              )}
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="flex-1 mt-4">
            {selectedPage?.page_schema ? (
              <div className="space-y-4 pr-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">{selectedPage.page_schema.page_title}</CardTitle>
                    <CardDescription>{selectedPage.page_schema.meta_description}</CardDescription>
                  </CardHeader>
                </Card>
                
                <div className="space-y-2">
                  {selectedPage.page_schema.sections?.map(section => renderSectionPreview(section))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p>No content available</p>
              </div>
            )}
          </ScrollArea>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowPreviewDialog(false)}>Close</Button>
            {selectedPage?.status === 'published' && (
              <Button onClick={() => window.open(`/pages/${selectedPage.slug}`, '_blank')}>
                <ExternalLink className="w-4 h-4 mr-2" />
                Open Page
              </Button>
            )}
            {selectedPage?.status === 'draft' && (
              <Button onClick={() => { handlePublish(selectedPage.id); setShowPreviewDialog(false); }}>
                <Globe className="w-4 h-4 mr-2" />
                Publish Page
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="w-5 h-5" />
              Edit Page: {selectedPage?.name}
            </DialogTitle>
            <DialogDescription>
              Edit sections, reorder, or delete them
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="flex-1 mt-4">
            {selectedPage?.page_schema?.sections ? (
              <div className="space-y-4 pr-4">
                {selectedPage.page_schema.sections.map((section, index) => (
                  <Card key={index} className="overflow-hidden">
                    <CardHeader className="py-3 px-4 bg-muted flex flex-row items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge>{section.type.toUpperCase()}</Badge>
                        <span className="text-sm text-muted-foreground">Order: {section.order}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => handleMoveSection(index, 'up')}
                          disabled={index === 0}
                        >
                          <ArrowUp className="w-4 h-4" />
                        </Button>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => handleMoveSection(index, 'down')}
                          disabled={index === selectedPage.page_schema.sections.length - 1}
                        >
                          <ArrowDown className="w-4 h-4" />
                        </Button>
                        <Button 
                          size="sm" 
                          variant="ghost"
                          onClick={() => handleEditSection(section, index)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          className="text-destructive"
                          onClick={() => handleDeleteSection(index)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    
                    {editingSectionIndex === index ? (
                      <CardContent className="p-4 space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Headline</Label>
                            <Input 
                              value={editingSection?.headline || ''} 
                              onChange={(e) => setEditingSection({...editingSection, headline: e.target.value})}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Subheadline</Label>
                            <Input 
                              value={editingSection?.subheadline || ''} 
                              onChange={(e) => setEditingSection({...editingSection, subheadline: e.target.value})}
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label>Body Text</Label>
                          <Textarea 
                            value={editingSection?.body_text || ''} 
                            onChange={(e) => setEditingSection({...editingSection, body_text: e.target.value})}
                            rows={3}
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>CTA Text</Label>
                            <Input 
                              value={editingSection?.cta_text || ''} 
                              onChange={(e) => setEditingSection({...editingSection, cta_text: e.target.value})}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>CTA URL</Label>
                            <Input 
                              value={editingSection?.cta_url || ''} 
                              onChange={(e) => setEditingSection({...editingSection, cta_url: e.target.value})}
                            />
                          </div>
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button variant="outline" onClick={() => { setEditingSection(null); setEditingSectionIndex(null); }}>
                            Cancel
                          </Button>
                          <Button onClick={handleSaveSection} disabled={saving}>
                            {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                            Save Section
                          </Button>
                        </div>
                      </CardContent>
                    ) : (
                      <CardContent className="p-4">
                        {section.headline && <p className="font-semibold">{section.headline}</p>}
                        {section.subheadline && <p className="text-sm text-muted-foreground">{section.subheadline}</p>}
                        {section.body_text && <p className="text-sm mt-2 line-clamp-2">{section.body_text}</p>}
                        {section.cta_text && (
                          <Badge variant="outline" className="mt-2">CTA: {section.cta_text}</Badge>
                        )}
                      </CardContent>
                    )}
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <p>No sections to edit</p>
              </div>
            )}
          </ScrollArea>

          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>Close</Button>
            <Button onClick={() => { setShowEditDialog(false); handlePreview(selectedPage); }}>
              <Eye className="w-4 h-4 mr-2" />
              Preview
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LandingPagesPage;
