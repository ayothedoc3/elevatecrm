import React, { useState, useEffect } from 'react';
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
import {
  Plus, Box, Trash2, Edit2, Settings, ChevronRight, 
  Database, Layers, Hash, Type, Calendar, Mail, Phone,
  Link2, List, CheckSquare, FileText, Loader2, Search, X
} from 'lucide-react';
import { toast } from 'sonner';

const FIELD_TYPES = [
  { value: 'text', label: 'Text', icon: Type },
  { value: 'number', label: 'Number', icon: Hash },
  { value: 'currency', label: 'Currency', icon: Hash },
  { value: 'date', label: 'Date', icon: Calendar },
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'phone', label: 'Phone', icon: Phone },
  { value: 'url', label: 'URL', icon: Link2 },
  { value: 'select', label: 'Dropdown', icon: List },
  { value: 'checkbox', label: 'Checkbox', icon: CheckSquare },
  { value: 'textarea', label: 'Long Text', icon: FileText },
];

const ICON_OPTIONS = [
  'Box', 'Package', 'ShoppingCart', 'Building', 'Truck', 
  'Tag', 'Bookmark', 'Star', 'Heart', 'Flag'
];

const COLOR_OPTIONS = [
  '#6366F1', '#8B5CF6', '#EC4899', '#F43F5E', '#F97316',
  '#EAB308', '#22C55E', '#14B8A6', '#06B6D4', '#3B82F6'
];

const CustomObjectsPage = () => {
  const { token } = useAuth();
  const [objects, setObjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedObject, setSelectedObject] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showRecordSheet, setShowRecordSheet] = useState(false);
  const [records, setRecords] = useState([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [showRecordDialog, setShowRecordDialog] = useState(false);
  const [recordFormData, setRecordFormData] = useState({});
  const [saving, setSaving] = useState(false);
  
  // New object form state
  const [newObject, setNewObject] = useState({
    name: '',
    slug: '',
    description: '',
    icon: 'Box',
    color: '#6366F1',
    fields: [{ name: 'name', label: 'Name', field_type: 'text', is_required: true }]
  });
  const [newField, setNewField] = useState({ name: '', label: '', field_type: 'text', is_required: false });

  const api = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  useEffect(() => {
    fetchObjects();
  }, []);

  const fetchObjects = async () => {
    setLoading(true);
    try {
      const response = await api.get('/custom-objects');
      setObjects(response.data);
    } catch (error) {
      console.error('Error fetching objects:', error);
      toast.error('Failed to load custom objects');
    } finally {
      setLoading(false);
    }
  };

  const fetchRecords = async (objectId) => {
    setRecordsLoading(true);
    try {
      const response = await api.get(`/custom-objects/${objectId}/records`);
      setRecords(response.data.records || []);
    } catch (error) {
      console.error('Error fetching records:', error);
      toast.error('Failed to load records');
    } finally {
      setRecordsLoading(false);
    }
  };

  const handleCreateObject = async () => {
    if (!newObject.name.trim()) {
      toast.error('Object name is required');
      return;
    }
    
    setSaving(true);
    try {
      const slug = newObject.slug || newObject.name.toLowerCase().replace(/\s+/g, '_');
      await api.post('/custom-objects', {
        ...newObject,
        slug,
        plural_name: `${newObject.name}s`
      });
      toast.success('Custom object created');
      setShowCreateDialog(false);
      setNewObject({
        name: '',
        slug: '',
        description: '',
        icon: 'Box',
        color: '#6366F1',
        fields: [{ name: 'name', label: 'Name', field_type: 'text', is_required: true }]
      });
      fetchObjects();
    } catch (error) {
      console.error('Error creating object:', error);
      toast.error(error.response?.data?.detail || 'Failed to create object');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteObject = async (objectId) => {
    if (!window.confirm('Are you sure you want to delete this object? All records will be lost.')) return;
    
    try {
      await api.delete(`/custom-objects/${objectId}`);
      toast.success('Object deleted');
      setSelectedObject(null);
      fetchObjects();
    } catch (error) {
      console.error('Error deleting object:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete object');
    }
  };

  const handleSelectObject = (obj) => {
    setSelectedObject(obj);
    setShowRecordSheet(true);
    fetchRecords(obj.id);
  };

  const handleAddField = () => {
    if (!newField.name.trim() || !newField.label.trim()) {
      toast.error('Field name and label are required');
      return;
    }
    
    setNewObject(prev => ({
      ...prev,
      fields: [...prev.fields, { ...newField, display_order: prev.fields.length }]
    }));
    setNewField({ name: '', label: '', field_type: 'text', is_required: false });
  };

  const handleRemoveField = (index) => {
    if (index === 0) return; // Don't remove the default name field
    setNewObject(prev => ({
      ...prev,
      fields: prev.fields.filter((_, i) => i !== index)
    }));
  };

  const handleOpenRecordDialog = (record = null) => {
    if (record) {
      setSelectedRecord(record);
      setRecordFormData(record.data);
    } else {
      setSelectedRecord(null);
      setRecordFormData({});
    }
    setShowRecordDialog(true);
  };

  const handleSaveRecord = async () => {
    setSaving(true);
    try {
      if (selectedRecord) {
        await api.put(`/custom-objects/${selectedObject.id}/records/${selectedRecord.id}`, {
          data: recordFormData
        });
        toast.success('Record updated');
      } else {
        await api.post(`/custom-objects/${selectedObject.id}/records`, {
          data: recordFormData
        });
        toast.success('Record created');
      }
      setShowRecordDialog(false);
      fetchRecords(selectedObject.id);
    } catch (error) {
      console.error('Error saving record:', error);
      toast.error(error.response?.data?.detail || 'Failed to save record');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRecord = async (recordId) => {
    if (!window.confirm('Delete this record?')) return;
    
    try {
      await api.delete(`/custom-objects/${selectedObject.id}/records/${recordId}`);
      toast.success('Record deleted');
      fetchRecords(selectedObject.id);
    } catch (error) {
      console.error('Error deleting record:', error);
      toast.error('Failed to delete record');
    }
  };

  const renderFieldInput = (field, value, onChange) => {
    switch (field.field_type) {
      case 'textarea':
        return (
          <Textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            rows={3}
          />
        );
      case 'number':
      case 'currency':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => onChange(parseFloat(e.target.value) || '')}
            placeholder={field.placeholder}
          />
        );
      case 'date':
        return (
          <Input
            type="date"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
          />
        );
      case 'email':
        return (
          <Input
            type="email"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || 'email@example.com'}
          />
        );
      case 'checkbox':
        return (
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={value || false}
              onChange={(e) => onChange(e.target.checked)}
              className="w-4 h-4 rounded"
            />
            <span className="text-sm">{field.label}</span>
          </div>
        );
      case 'select':
        const options = field.config?.options || [];
        return (
          <Select value={value || ''} onValueChange={onChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select..." />
            </SelectTrigger>
            <SelectContent>
              {options.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      default:
        return (
          <Input
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
          />
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Custom Objects</h1>
          <p className="text-muted-foreground">Create and manage custom data structures</p>
        </div>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Create Object
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create Custom Object</DialogTitle>
              <DialogDescription>
                Define a new data structure for your CRM
              </DialogDescription>
            </DialogHeader>
            
            <Tabs defaultValue="basics" className="mt-4">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="basics">Basic Info</TabsTrigger>
                <TabsTrigger value="fields">Fields</TabsTrigger>
              </TabsList>
              
              <TabsContent value="basics" className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Object Name *</Label>
                    <Input
                      value={newObject.name}
                      onChange={(e) => setNewObject({...newObject, name: e.target.value})}
                      placeholder="e.g. Product"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>API Slug</Label>
                    <Input
                      value={newObject.slug}
                      onChange={(e) => setNewObject({...newObject, slug: e.target.value})}
                      placeholder="Auto-generated from name"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={newObject.description}
                    onChange={(e) => setNewObject({...newObject, description: e.target.value})}
                    placeholder="What is this object used for?"
                    rows={2}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Icon</Label>
                    <Select value={newObject.icon} onValueChange={(v) => setNewObject({...newObject, icon: v})}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {ICON_OPTIONS.map(icon => (
                          <SelectItem key={icon} value={icon}>{icon}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Color</Label>
                    <div className="flex gap-2 flex-wrap">
                      {COLOR_OPTIONS.map(color => (
                        <button
                          key={color}
                          type="button"
                          className={`w-6 h-6 rounded-full border-2 ${newObject.color === color ? 'border-foreground' : 'border-transparent'}`}
                          style={{ backgroundColor: color }}
                          onClick={() => setNewObject({...newObject, color})}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="fields" className="space-y-4 mt-4">
                {/* Existing fields */}
                <div className="space-y-2">
                  <Label>Object Fields</Label>
                  {newObject.fields.map((field, index) => (
                    <div key={index} className="flex items-center gap-2 p-2 bg-muted rounded-lg">
                      <div className="flex-1">
                        <span className="font-medium">{field.label}</span>
                        <span className="text-xs text-muted-foreground ml-2">({field.field_type})</span>
                        {field.is_required && <Badge variant="outline" className="ml-2 text-xs">Required</Badge>}
                      </div>
                      {index > 0 && (
                        <Button variant="ghost" size="icon" onClick={() => handleRemoveField(index)}>
                          <X className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
                
                {/* Add new field */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Add Field</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        value={newField.name}
                        onChange={(e) => setNewField({...newField, name: e.target.value.toLowerCase().replace(/\s+/g, '_')})}
                        placeholder="field_name"
                      />
                      <Input
                        value={newField.label}
                        onChange={(e) => setNewField({...newField, label: e.target.value})}
                        placeholder="Display Label"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Select value={newField.field_type} onValueChange={(v) => setNewField({...newField, field_type: v})}>
                        <SelectTrigger className="flex-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {FIELD_TYPES.map(type => (
                            <SelectItem key={type.value} value={type.value}>
                              <div className="flex items-center gap-2">
                                <type.icon className="w-4 h-4" />
                                {type.label}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={newField.is_required}
                          onChange={(e) => setNewField({...newField, is_required: e.target.checked})}
                          className="w-4 h-4"
                        />
                        <span className="text-sm">Required</span>
                      </div>
                      <Button variant="outline" onClick={handleAddField}>
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
            
            <DialogFooter className="mt-4">
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
              <Button onClick={handleCreateObject} disabled={saving}>
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
                Create Object
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Objects Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      ) : objects.length === 0 ? (
        <Card className="text-center py-12">
          <CardContent>
            <Database className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="font-semibold text-lg mb-2">No Custom Objects</h3>
            <p className="text-muted-foreground mb-4">
              Create your first custom object to store additional data
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Object
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {objects.map(obj => (
            <Card 
              key={obj.id} 
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => handleSelectObject(obj)}
            >
              <CardHeader className="flex flex-row items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${obj.color}20` }}
                >
                  <Box className="w-5 h-5" style={{ color: obj.color }} />
                </div>
                <div className="flex-1">
                  <CardTitle className="text-base">{obj.name}</CardTitle>
                  <CardDescription className="text-xs">
                    {obj.record_count} record{obj.record_count !== 1 ? 's' : ''} • {obj.fields?.length || 0} fields
                  </CardDescription>
                </div>
                <ChevronRight className="w-5 h-5 text-muted-foreground" />
              </CardHeader>
              {obj.description && (
                <CardContent className="pt-0">
                  <p className="text-sm text-muted-foreground line-clamp-2">{obj.description}</p>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Records Sheet */}
      <Sheet open={showRecordSheet} onOpenChange={setShowRecordSheet}>
        <SheetContent className="w-full sm:max-w-2xl">
          {selectedObject && (
            <>
              <SheetHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-10 h-10 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${selectedObject.color}20` }}
                    >
                      <Box className="w-5 h-5" style={{ color: selectedObject.color }} />
                    </div>
                    <div>
                      <SheetTitle>{selectedObject.plural_name || `${selectedObject.name}s`}</SheetTitle>
                      <SheetDescription>{selectedObject.description}</SheetDescription>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="icon" onClick={() => handleDeleteObject(selectedObject.id)}>
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </SheetHeader>
              
              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="relative flex-1 max-w-xs">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input placeholder="Search records..." className="pl-9" />
                  </div>
                  <Button onClick={() => handleOpenRecordDialog()}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Record
                  </Button>
                </div>
                
                <ScrollArea className="h-[calc(100vh-240px)]">
                  {recordsLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map(i => (
                        <Skeleton key={i} className="h-16" />
                      ))}
                    </div>
                  ) : records.length === 0 ? (
                    <div className="text-center py-12">
                      <Layers className="w-10 h-10 mx-auto text-muted-foreground mb-2" />
                      <p className="text-muted-foreground">No records yet</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {selectedObject.fields?.filter(f => f.show_in_list).map(field => (
                            <TableHead key={field.id}>{field.label}</TableHead>
                          ))}
                          <TableHead className="w-[80px]">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {records.map(record => (
                          <TableRow key={record.id} className="cursor-pointer" onClick={() => handleOpenRecordDialog(record)}>
                            {selectedObject.fields?.filter(f => f.show_in_list).map(field => (
                              <TableCell key={field.id}>
                                {field.field_type === 'checkbox' 
                                  ? (record.data[field.name] ? '✓' : '-')
                                  : record.data[field.name] || '-'
                                }
                              </TableCell>
                            ))}
                            <TableCell>
                              <Button 
                                variant="ghost" 
                                size="icon"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteRecord(record.id);
                                }}
                              >
                                <Trash2 className="w-4 h-4 text-muted-foreground hover:text-red-500" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </ScrollArea>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Record Dialog */}
      <Dialog open={showRecordDialog} onOpenChange={setShowRecordDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {selectedRecord ? 'Edit Record' : 'New Record'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {selectedObject?.fields?.map(field => (
              <div key={field.id} className="space-y-2">
                <Label className="flex items-center gap-1">
                  {field.label}
                  {field.is_required && <span className="text-red-500">*</span>}
                </Label>
                {renderFieldInput(
                  field,
                  recordFormData[field.name],
                  (value) => setRecordFormData(prev => ({ ...prev, [field.name]: value }))
                )}
                {field.help_text && (
                  <p className="text-xs text-muted-foreground">{field.help_text}</p>
                )}
              </div>
            ))}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRecordDialog(false)}>Cancel</Button>
            <Button onClick={handleSaveRecord} disabled={saving}>
              {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {selectedRecord ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default CustomObjectsPage;
