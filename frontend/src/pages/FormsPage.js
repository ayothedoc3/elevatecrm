import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  FileText, Plus, Trash2, Edit, ExternalLink, Copy, Eye,
  GripVertical, Type, Mail, Phone, Hash, Calendar, CheckSquare,
  List, AlignLeft, Upload
} from 'lucide-react';

const fieldTypes = [
  { value: 'text', label: 'Text', icon: Type },
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'phone', label: 'Phone', icon: Phone },
  { value: 'number', label: 'Number', icon: Hash },
  { value: 'textarea', label: 'Long Text', icon: AlignLeft },
  { value: 'select', label: 'Dropdown', icon: List },
  { value: 'checkbox', label: 'Checkbox', icon: CheckSquare },
  { value: 'date', label: 'Date', icon: Calendar },
];

const mappingOptions = [
  { value: '', label: 'No mapping' },
  { value: 'first_name', label: 'First Name' },
  { value: 'last_name', label: 'Last Name' },
  { value: 'email', label: 'Email' },
  { value: 'phone', label: 'Phone' },
  { value: 'company_name', label: 'Company' },
];

const FormsPage = () => {
  const { api, tenant } = useAuth();
  const [loading, setLoading] = useState(true);
  const [forms, setForms] = useState([]);
  const [pipelines, setPipelines] = useState([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedForm, setSelectedForm] = useState(null);
  const [newForm, setNewForm] = useState({
    name: '',
    description: '',
    slug: '',
    fields: [],
    submit_button_text: 'Submit',
    success_message: 'Thank you for your submission!',
    create_contact: true,
    create_deal: false,
    assign_pipeline_id: '',
    is_active: true,
    is_public: true
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [formsRes, pipelinesRes] = await Promise.all([
        api.get('/forms'),
        api.get('/pipelines')
      ]);
      setForms(formsRes.data.forms);
      setPipelines(pipelinesRes.data.pipelines);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateForm = async () => {
    if (!newForm.name || !newForm.slug) return;
    setCreating(true);
    try {
      await api.post('/forms', newForm);
      setShowCreateModal(false);
      setNewForm({
        name: '',
        description: '',
        slug: '',
        fields: [],
        submit_button_text: 'Submit',
        success_message: 'Thank you for your submission!',
        create_contact: true,
        create_deal: false,
        assign_pipeline_id: '',
        is_active: true,
        is_public: true
      });
      fetchData();
    } catch (error) {
      console.error('Error creating form:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteForm = async (formId) => {
    if (!window.confirm('Are you sure you want to delete this form?')) return;
    try {
      await api.delete(`/forms/${formId}`);
      fetchData();
    } catch (error) {
      console.error('Error deleting form:', error);
    }
  };

  const addField = (type) => {
    const field = {
      id: `field_${Date.now()}`,
      type,
      label: `New ${fieldTypes.find(f => f.value === type)?.label} Field`,
      placeholder: '',
      required: false,
      mapping: ''
    };
    setNewForm({
      ...newForm,
      fields: [...newForm.fields, field]
    });
  };

  const updateField = (index, updates) => {
    const fields = [...newForm.fields];
    fields[index] = { ...fields[index], ...updates };
    setNewForm({ ...newForm, fields });
  };

  const removeField = (index) => {
    const fields = newForm.fields.filter((_, i) => i !== index);
    setNewForm({ ...newForm, fields });
  };

  const generateSlug = (name) => {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
  };

  const getFormUrl = (form) => {
    const baseUrl = window.location.origin;
    return `${baseUrl}/api/public/forms/${tenant}/${form.slug}`;
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map(i => (
          <Card key={i}>
            <CardContent className="p-6">
              <Skeleton className="h-6 w-48 mb-2" />
              <Skeleton className="h-4 w-64" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Forms</h1>
          <p className="text-muted-foreground">Create forms to capture leads and customer information</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Form
        </Button>
      </div>

      {/* Forms List */}
      {forms.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h2 className="text-xl font-semibold mb-2">No forms yet</h2>
            <p className="text-muted-foreground mb-4">Create your first form to start capturing leads</p>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Form
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {forms.map(form => (
            <Card key={form.id} className="hover:border-primary/50 transition-colors">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{form.name}</CardTitle>
                    <CardDescription>{form.description || 'No description'}</CardDescription>
                  </div>
                  <div className="flex items-center gap-1">
                    {form.is_active ? (
                      <Badge className="bg-green-500/20 text-green-400">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Fields</span>
                    <span className="font-medium">{form.fields?.length || 0}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Submissions</span>
                    <span className="font-medium">{form.submission_count}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <code className="bg-muted px-2 py-1 rounded flex-1 truncate">
                      /{form.slug}
                    </code>
                    <Button variant="ghost" size="sm" onClick={() => copyToClipboard(getFormUrl(form))}>
                      <Copy className="w-3 h-3" />
                    </Button>
                  </div>
                  <div className="flex gap-2 pt-2 border-t">
                    <Button variant="outline" size="sm" className="flex-1">
                      <Edit className="w-3 h-3 mr-1" />
                      Edit
                    </Button>
                    <Button variant="outline" size="sm">
                      <Eye className="w-3 h-3" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteForm(form.id)}>
                      <Trash2 className="w-3 h-3 text-red-500" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Form Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Form</DialogTitle>
          </DialogHeader>
          
          <Tabs defaultValue="basic">
            <TabsList className="mb-4">
              <TabsTrigger value="basic">Basic Info</TabsTrigger>
              <TabsTrigger value="fields">Fields ({newForm.fields.length})</TabsTrigger>
              <TabsTrigger value="settings">Settings</TabsTrigger>
            </TabsList>
            
            <TabsContent value="basic" className="space-y-4">
              <div className="space-y-2">
                <Label>Form Name</Label>
                <Input
                  value={newForm.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    setNewForm({ 
                      ...newForm, 
                      name,
                      slug: newForm.slug || generateSlug(name)
                    });
                  }}
                  placeholder="e.g., Contact Form"
                />
              </div>
              
              <div className="space-y-2">
                <Label>URL Slug</Label>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground text-sm">/forms/</span>
                  <Input
                    value={newForm.slug}
                    onChange={(e) => setNewForm({ ...newForm, slug: generateSlug(e.target.value) })}
                    placeholder="contact-form"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={newForm.description}
                  onChange={(e) => setNewForm({ ...newForm, description: e.target.value })}
                  placeholder="Describe the purpose of this form..."
                  rows={2}
                />
              </div>
              
              <div className="space-y-2">
                <Label>Submit Button Text</Label>
                <Input
                  value={newForm.submit_button_text}
                  onChange={(e) => setNewForm({ ...newForm, submit_button_text: e.target.value })}
                  placeholder="Submit"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Success Message</Label>
                <Textarea
                  value={newForm.success_message}
                  onChange={(e) => setNewForm({ ...newForm, success_message: e.target.value })}
                  placeholder="Thank you for your submission!"
                  rows={2}
                />
              </div>
            </TabsContent>
            
            <TabsContent value="fields" className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Form Fields</Label>
                <Select onValueChange={addField}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Add field..." />
                  </SelectTrigger>
                  <SelectContent>
                    {fieldTypes.map(field => (
                      <SelectItem key={field.value} value={field.value}>
                        <div className="flex items-center gap-2">
                          <field.icon className="w-4 h-4" />
                          {field.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {newForm.fields.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                  <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No fields added yet</p>
                  <p className="text-sm">Add fields to your form using the dropdown above</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {newForm.fields.map((field, index) => {
                    const fieldType = fieldTypes.find(f => f.value === field.type);
                    const FieldIcon = fieldType?.icon || Type;
                    return (
                      <Card key={field.id}>
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <div className="pt-2 cursor-grab text-muted-foreground">
                              <GripVertical className="w-4 h-4" />
                            </div>
                            <div className="flex-1 space-y-3">
                              <div className="flex items-center gap-2">
                                <FieldIcon className="w-4 h-4 text-muted-foreground" />
                                <Input
                                  value={field.label}
                                  onChange={(e) => updateField(index, { label: e.target.value })}
                                  className="font-medium"
                                  placeholder="Field label"
                                />
                              </div>
                              <div className="grid grid-cols-2 gap-3">
                                <div>
                                  <Label className="text-xs">Placeholder</Label>
                                  <Input
                                    value={field.placeholder || ''}
                                    onChange={(e) => updateField(index, { placeholder: e.target.value })}
                                    placeholder="Placeholder text..."
                                    className="text-sm"
                                  />
                                </div>
                                <div>
                                  <Label className="text-xs">Map to CRM Field</Label>
                                  <Select
                                    value={field.mapping || ''}
                                    onValueChange={(value) => updateField(index, { mapping: value })}
                                  >
                                    <SelectTrigger className="text-sm">
                                      <SelectValue placeholder="Select mapping..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {mappingOptions.map(opt => (
                                        <SelectItem key={opt.value} value={opt.value}>
                                          {opt.label}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                              </div>
                              <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2">
                                  <Switch
                                    checked={field.required}
                                    onCheckedChange={(checked) => updateField(index, { required: checked })}
                                  />
                                  <Label className="text-sm">Required</Label>
                                </div>
                              </div>
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => removeField(index)}>
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="settings" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">CRM Integration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Create Contact</Label>
                      <p className="text-sm text-muted-foreground">Automatically create a contact on submission</p>
                    </div>
                    <Switch
                      checked={newForm.create_contact}
                      onCheckedChange={(checked) => setNewForm({ ...newForm, create_contact: checked })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Create Deal</Label>
                      <p className="text-sm text-muted-foreground">Automatically create a deal on submission</p>
                    </div>
                    <Switch
                      checked={newForm.create_deal}
                      onCheckedChange={(checked) => setNewForm({ ...newForm, create_deal: checked })}
                    />
                  </div>
                  
                  {newForm.create_deal && (
                    <div className="space-y-2">
                      <Label>Assign to Pipeline</Label>
                      <Select
                        value={newForm.assign_pipeline_id}
                        onValueChange={(value) => setNewForm({ ...newForm, assign_pipeline_id: value })}
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
                  )}
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Visibility</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Active</Label>
                      <p className="text-sm text-muted-foreground">Form accepts submissions</p>
                    </div>
                    <Switch
                      checked={newForm.is_active}
                      onCheckedChange={(checked) => setNewForm({ ...newForm, is_active: checked })}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Public</Label>
                      <p className="text-sm text-muted-foreground">Form can be embedded externally</p>
                    </div>
                    <Switch
                      checked={newForm.is_public}
                      onCheckedChange={(checked) => setNewForm({ ...newForm, is_public: checked })}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button onClick={handleCreateForm} disabled={creating || !newForm.name || !newForm.slug}>
              {creating ? 'Creating...' : 'Create Form'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FormsPage;
