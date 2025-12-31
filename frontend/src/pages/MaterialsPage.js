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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Skeleton } from '../components/ui/skeleton';
import {
  Image, FileText, Link2, Video, Upload, Search, Filter,
  Download, Trash2, Edit, Eye, Plus, RefreshCw, Grid,
  List, ExternalLink, Copy, MoreVertical, Loader2, X
} from 'lucide-react';
import { toast } from 'sonner';

const CATEGORIES = [
  { value: 'banners', label: 'Banners', icon: Image },
  { value: 'social_posts', label: 'Social Posts', icon: Image },
  { value: 'email_templates', label: 'Email Templates', icon: FileText },
  { value: 'logos', label: 'Logos', icon: Image },
  { value: 'product_images', label: 'Product Images', icon: Image },
  { value: 'sales_sheets', label: 'Sales Sheets', icon: FileText },
  { value: 'videos', label: 'Videos', icon: Video },
  { value: 'other', label: 'Other', icon: FileText }
];

const TYPE_ICONS = {
  image: Image,
  pdf: FileText,
  url: Link2,
  video: Video
};

const MaterialsPage = () => {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [materials, setMaterials] = useState([]);
  const [categories, setCategories] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [viewMode, setViewMode] = useState('grid');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showUrlDialog, setShowUrlDialog] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState(null);

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

  const api = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchMaterials = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 20 };
      if (selectedCategory !== 'all') params.category = selectedCategory;
      if (searchQuery) params.search = searchQuery;
      
      const response = await api.get('/materials', { params });
      setMaterials(response.data.materials || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching materials:', error);
      toast.error('Failed to load materials');
    } finally {
      setLoading(false);
    }
  }, [page, selectedCategory, searchQuery]);

  const fetchCategories = useCallback(async () => {
    try {
      const response = await api.get('/materials/categories');
      setCategories(response.data.categories || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  }, []);

  useEffect(() => {
    fetchMaterials();
    fetchCategories();
  }, [fetchMaterials, fetchCategories]);

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
      resetUploadForm();
      fetchMaterials();
      fetchCategories();
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
      resetUrlForm();
      fetchMaterials();
      fetchCategories();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create URL material');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (materialId) => {
    if (!window.confirm('Are you sure you want to delete this material?')) return;

    try {
      await api.delete(`/materials/${materialId}`);
      toast.success('Material deleted');
      fetchMaterials();
      fetchCategories();
    } catch (error) {
      toast.error('Failed to delete material');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const resetUploadForm = () => {
    setUploadFile(null);
    setUploadName('');
    setUploadDescription('');
    setUploadCategory('other');
    setUploadTags('');
  };

  const resetUrlForm = () => {
    setUrlName('');
    setUrlDescription('');
    setUrlCategory('other');
    setUrlValue('');
    setUrlTags('');
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getCategoryIcon = (category) => {
    const cat = CATEGORIES.find(c => c.value === category);
    return cat ? cat.icon : FileText;
  };

  const getTypeIcon = (type) => TYPE_ICONS[type] || FileText;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Image className="w-6 h-6" />
            Marketing Materials
          </h1>
          <p className="text-muted-foreground">Manage marketing assets for affiliates</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => { fetchMaterials(); fetchCategories(); }} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
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
                      {CATEGORIES.map(cat => (
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
                <DialogDescription>Upload images, PDFs, or documents</DialogDescription>
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
                      {CATEGORIES.map(cat => (
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

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search materials..."
                className="pl-9"
              />
            </div>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-48">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {CATEGORIES.map(cat => (
                  <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-1 ml-auto">
              <Button
                variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
                size="icon"
                onClick={() => setViewMode('grid')}
              >
                <Grid className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                size="icon"
                onClick={() => setViewMode('list')}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Category Pills */}
      <div className="flex items-center gap-2 flex-wrap">
        <Badge
          variant={selectedCategory === 'all' ? 'default' : 'outline'}
          className="cursor-pointer"
          onClick={() => setSelectedCategory('all')}
        >
          All ({total})
        </Badge>
        {categories.map(cat => (
          <Badge
            key={cat.value}
            variant={selectedCategory === cat.value ? 'default' : 'outline'}
            className="cursor-pointer"
            onClick={() => setSelectedCategory(cat.value)}
          >
            {cat.label} ({cat.count})
          </Badge>
        ))}
      </div>

      {/* Materials Grid/List */}
      {loading ? (
        <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4' : 'space-y-2'}>
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className={viewMode === 'grid' ? 'h-48' : 'h-16'} />
          ))}
        </div>
      ) : materials.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Image className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-semibold mb-2">No Materials Found</h3>
            <p className="text-muted-foreground mb-4">Upload your first marketing material</p>
            <Button onClick={() => setShowUploadDialog(true)}>
              <Upload className="w-4 h-4 mr-2" />
              Upload Material
            </Button>
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {materials.map(material => {
            const TypeIcon = getTypeIcon(material.material_type);
            return (
              <Card key={material.id} className="overflow-hidden hover:shadow-lg transition-shadow">
                <div className="aspect-video bg-muted relative flex items-center justify-center">
                  {material.material_type === 'image' && material.file_url ? (
                    <img
                      src={material.file_url}
                      alt={material.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentElement.querySelector('.fallback-icon')?.classList.remove('hidden');
                      }}
                    />
                  ) : null}
                  <TypeIcon className={`w-12 h-12 text-muted-foreground ${material.material_type === 'image' && material.file_url ? 'hidden fallback-icon' : ''}`} />
                  <Badge className="absolute top-2 right-2 text-xs">
                    {material.category?.replace('_', ' ')}
                  </Badge>
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
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDelete(material.id)}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y">
              {materials.map(material => {
                const TypeIcon = getTypeIcon(material.material_type);
                return (
                  <div key={material.id} className="flex items-center gap-4 p-4 hover:bg-muted/50">
                    <div className="w-12 h-12 rounded bg-muted flex items-center justify-center flex-shrink-0">
                      <TypeIcon className="w-6 h-6 text-muted-foreground" />
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
                      <Button variant="ghost" size="icon" className="text-destructive" onClick={() => handleDelete(material.id)}>
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <Button variant="outline" size="sm" disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(p => p + 1)}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
};

export default MaterialsPage;
