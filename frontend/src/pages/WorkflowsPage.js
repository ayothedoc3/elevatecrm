import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { ScrollArea } from '../components/ui/scroll-area';
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '../components/ui/sheet';
import { Label } from '../components/ui/label';
import {
  Zap, Plus, Play, Pause, Trash2, Edit, X,
  Mail, MessageSquare, Clock, CheckCircle2, 
  FileText, Tag, User, ArrowRight, ArrowDown, GripVertical,
  Settings, Eye, ChevronRight, AlertCircle
} from 'lucide-react';

const triggerTypes = [
  { value: 'form_submitted', label: 'Form Submitted', icon: FileText, color: 'bg-blue-500' },
  { value: 'deal_stage_changed', label: 'Deal Stage Changed', icon: ArrowRight, color: 'bg-violet-500' },
  { value: 'deal_created', label: 'Deal Created', icon: Plus, color: 'bg-emerald-500' },
  { value: 'contact_created', label: 'Contact Created', icon: User, color: 'bg-amber-500' },
  { value: 'message_received', label: 'Message Received', icon: MessageSquare, color: 'bg-pink-500' },
  { value: 'manual', label: 'Manual Trigger', icon: Play, color: 'bg-slate-500' },
  // Affiliate Triggers
  { value: 'affiliate_link_clicked', label: 'Affiliate Link Clicked', icon: Zap, color: 'bg-orange-500', category: 'affiliate' },
  { value: 'affiliate_signup', label: 'New Affiliate Signup', icon: User, color: 'bg-orange-500', category: 'affiliate' },
  { value: 'affiliate_approved', label: 'Affiliate Approved', icon: CheckCircle2, color: 'bg-green-500', category: 'affiliate' },
  { value: 'commission_earned', label: 'Commission Earned', icon: Tag, color: 'bg-emerald-500', category: 'affiliate' },
  { value: 'commission_paid', label: 'Commission Paid', icon: CheckCircle2, color: 'bg-green-500', category: 'affiliate' },
  { value: 'landing_page_view', label: 'Landing Page Viewed', icon: Eye, color: 'bg-blue-500', category: 'affiliate' },
  { value: 'landing_page_conversion', label: 'Landing Page Conversion', icon: ArrowRight, color: 'bg-purple-500', category: 'affiliate' },
];

const actionTypes = [
  { value: 'send_email', label: 'Send Email', icon: Mail, color: 'bg-blue-500' },
  { value: 'send_sms', label: 'Send SMS', icon: MessageSquare, color: 'bg-green-500' },
  { value: 'create_task', label: 'Create Task', icon: CheckCircle2, color: 'bg-violet-500' },
  { value: 'add_tag', label: 'Add Tag', icon: Tag, color: 'bg-amber-500' },
  { value: 'set_property', label: 'Set Property', icon: Edit, color: 'bg-pink-500' },
  { value: 'delay', label: 'Wait/Delay', icon: Clock, color: 'bg-slate-500' },
  // Affiliate Actions
  { value: 'approve_affiliate', label: 'Approve Affiliate', icon: CheckCircle2, color: 'bg-green-500', category: 'affiliate' },
  { value: 'create_commission', label: 'Create Commission', icon: Tag, color: 'bg-emerald-500', category: 'affiliate' },
  { value: 'notify_affiliate', label: 'Notify Affiliate', icon: Mail, color: 'bg-orange-500', category: 'affiliate' },
  { value: 'update_affiliate_status', label: 'Update Affiliate Status', icon: Edit, color: 'bg-amber-500', category: 'affiliate' },
];

// Workflow Card Component
const WorkflowCard = ({ workflow, onSelect, onStatusChange, onDelete }) => {
  const trigger = triggerTypes.find(t => t.value === workflow.trigger_type);
  const TriggerIcon = trigger?.icon || Zap;

  return (
    <Card 
      className="cursor-pointer hover:border-primary/50 hover:shadow-lg transition-all group"
      onClick={() => onSelect(workflow)}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-lg ${trigger?.color || 'bg-primary'}/20`}>
              <TriggerIcon className={`w-6 h-6 ${trigger?.color?.replace('bg-', 'text-') || 'text-primary'}`} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-semibold">{workflow.name}</h3>
                <StatusBadge status={workflow.status} />
              </div>
              <p className="text-sm text-muted-foreground line-clamp-1">
                {workflow.description || 'No description'}
              </p>
              <div className="flex items-center gap-4 mt-3 text-sm">
                <span className="flex items-center gap-1 text-muted-foreground">
                  <TriggerIcon className="w-4 h-4" />
                  {trigger?.label}
                </span>
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Zap className="w-4 h-4" />
                  {workflow.actions?.length || 0} actions
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-2xl font-bold">{workflow.total_runs || 0}</p>
              <p className="text-xs text-muted-foreground">Total Runs</p>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
              {workflow.status === 'active' ? (
                <Button variant="outline" size="sm" onClick={() => onStatusChange(workflow.id, 'paused')}>
                  <Pause className="w-4 h-4" />
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={() => onStatusChange(workflow.id, 'active')}>
                  <Play className="w-4 h-4" />
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => onDelete(workflow.id)}>
                <Trash2 className="w-4 h-4 text-red-500" />
              </Button>
            </div>
            <ChevronRight className="w-5 h-5 text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Status Badge Component
const StatusBadge = ({ status }) => {
  switch (status) {
    case 'active':
      return <Badge className="bg-green-500/20 text-green-400 border-green-500/30"><Play className="w-3 h-3 mr-1" />Active</Badge>;
    case 'paused':
      return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30"><Pause className="w-3 h-3 mr-1" />Paused</Badge>;
    case 'draft':
      return <Badge variant="secondary"><Edit className="w-3 h-3 mr-1" />Draft</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
};

// Visual Node Component
const WorkflowNode = ({ type, data, index, isLast, onEdit, onDelete, isDragging }) => {
  const config = type === 'trigger' 
    ? triggerTypes.find(t => t.value === data.trigger_type)
    : actionTypes.find(a => a.value === data.type);
  
  const Icon = config?.icon || Zap;
  const colorClass = config?.color || 'bg-primary';
  
  return (
    <div className="relative">
      {/* Connector Line */}
      {index > 0 && (
        <div className="absolute left-1/2 -top-6 transform -translate-x-1/2 flex flex-col items-center">
          <div className="w-0.5 h-6 bg-border" />
        </div>
      )}
      
      {/* Node */}
      <div 
        className={`relative bg-card border rounded-xl p-4 shadow-sm hover:shadow-md transition-all cursor-pointer group ${isDragging ? 'opacity-50' : ''}`}
        onClick={() => onEdit(index)}
      >
        <div className="flex items-center gap-3">
          {type !== 'trigger' && (
            <div className="cursor-grab text-muted-foreground hover:text-foreground">
              <GripVertical className="w-4 h-4" />
            </div>
          )}
          <div className={`p-2 rounded-lg ${colorClass}/20`}>
            <Icon className={`w-5 h-5 ${colorClass.replace('bg-', 'text-')}`} />
          </div>
          <div className="flex-1">
            <p className="font-medium text-sm">{config?.label || data.type}</p>
            {type === 'action' && data.config && (
              <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                {data.config.subject || data.config.body || data.config.tag || `${data.delay_minutes} min delay`}
              </p>
            )}
          </div>
          <Badge variant="outline" className="text-xs">
            {type === 'trigger' ? 'Trigger' : `Step ${index}`}
          </Badge>
          {type === 'action' && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => { e.stopPropagation(); onDelete(index - 1); }}
            >
              <X className="w-4 h-4 text-red-500" />
            </Button>
          )}
        </div>
      </div>
      
      {/* Arrow Down */}
      {!isLast && (
        <div className="absolute left-1/2 -bottom-6 transform -translate-x-1/2 flex flex-col items-center">
          <ArrowDown className="w-4 h-4 text-muted-foreground" />
        </div>
      )}
    </div>
  );
};

// Action Editor Panel
const ActionEditor = ({ action, index, onUpdate, onClose }) => {
  const [localAction, setLocalAction] = useState(action);
  const actionType = actionTypes.find(a => a.value === localAction.type);
  const ActionIcon = actionType?.icon || Zap;

  const handleSave = () => {
    onUpdate(index, localAction);
    onClose();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 pb-4 border-b">
        <div className={`p-2 rounded-lg ${actionType?.color}/20`}>
          <ActionIcon className={`w-5 h-5 ${actionType?.color?.replace('bg-', 'text-')}`} />
        </div>
        <div>
          <p className="font-medium">{actionType?.label}</p>
          <p className="text-sm text-muted-foreground">Step {index + 1}</p>
        </div>
      </div>

      {localAction.type === 'send_email' && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Subject</Label>
            <Input
              value={localAction.config?.subject || ''}
              onChange={(e) => setLocalAction({ 
                ...localAction, 
                config: { ...localAction.config, subject: e.target.value } 
              })}
              placeholder="Enter email subject..."
            />
          </div>
          <div className="space-y-2">
            <Label>Email Body</Label>
            <Textarea
              value={localAction.config?.body || ''}
              onChange={(e) => setLocalAction({ 
                ...localAction, 
                config: { ...localAction.config, body: e.target.value } 
              })}
              placeholder="Enter email content..."
              rows={6}
            />
          </div>
        </div>
      )}

      {localAction.type === 'send_sms' && (
        <div className="space-y-2">
          <Label>SMS Message</Label>
          <Textarea
            value={localAction.config?.body || ''}
            onChange={(e) => setLocalAction({ 
              ...localAction, 
              config: { ...localAction.config, body: e.target.value } 
            })}
            placeholder="Enter SMS message..."
            rows={4}
          />
          <p className="text-xs text-muted-foreground">Max 160 characters for single SMS</p>
        </div>
      )}

      {localAction.type === 'delay' && (
        <div className="space-y-2">
          <Label>Wait Duration</Label>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              value={localAction.delay_minutes || 0}
              onChange={(e) => setLocalAction({ 
                ...localAction, 
                delay_minutes: parseInt(e.target.value) || 0 
              })}
              className="w-24"
            />
            <span className="text-muted-foreground">minutes</span>
          </div>
        </div>
      )}

      {localAction.type === 'add_tag' && (
        <div className="space-y-2">
          <Label>Tag Name</Label>
          <Input
            value={localAction.config?.tag || ''}
            onChange={(e) => setLocalAction({ 
              ...localAction, 
              config: { ...localAction.config, tag: e.target.value } 
            })}
            placeholder="Enter tag name..."
          />
        </div>
      )}

      {localAction.type === 'create_task' && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Task Title</Label>
            <Input
              value={localAction.config?.title || ''}
              onChange={(e) => setLocalAction({ 
                ...localAction, 
                config: { ...localAction.config, title: e.target.value } 
              })}
              placeholder="Enter task title..."
            />
          </div>
          <div className="space-y-2">
            <Label>Due in (days)</Label>
            <Input
              type="number"
              value={localAction.config?.due_days || 1}
              onChange={(e) => setLocalAction({ 
                ...localAction, 
                config: { ...localAction.config, due_days: parseInt(e.target.value) || 1 } 
              })}
              className="w-24"
            />
          </div>
        </div>
      )}

      {localAction.type === 'set_property' && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Property Name</Label>
            <Input
              value={localAction.config?.property || ''}
              onChange={(e) => setLocalAction({ 
                ...localAction, 
                config: { ...localAction.config, property: e.target.value } 
              })}
              placeholder="e.g., lifecycle_stage"
            />
          </div>
          <div className="space-y-2">
            <Label>Value</Label>
            <Input
              value={localAction.config?.value || ''}
              onChange={(e) => setLocalAction({ 
                ...localAction, 
                config: { ...localAction.config, value: e.target.value } 
              })}
              placeholder="Enter value..."
            />
          </div>
        </div>
      )}

      <div className="flex gap-2 pt-4">
        <Button variant="outline" className="flex-1" onClick={onClose}>Cancel</Button>
        <Button className="flex-1" onClick={handleSave}>Save Changes</Button>
      </div>
    </div>
  );
};

// Visual Workflow Builder
const WorkflowBuilder = ({ workflow, onSave, onClose }) => {
  const [localWorkflow, setLocalWorkflow] = useState(workflow || {
    name: '',
    description: '',
    trigger_type: 'form_submitted',
    trigger_config: {},
    actions: [],
    status: 'draft'
  });
  const [editingAction, setEditingAction] = useState(null);
  const [showActionPicker, setShowActionPicker] = useState(false);

  const addAction = (type) => {
    const action = { type, config: {}, delay_minutes: 0 };
    setLocalWorkflow({
      ...localWorkflow,
      actions: [...localWorkflow.actions, action]
    });
    setShowActionPicker(false);
  };

  const updateAction = (index, updates) => {
    const actions = [...localWorkflow.actions];
    actions[index] = { ...actions[index], ...updates };
    setLocalWorkflow({ ...localWorkflow, actions });
  };

  const removeAction = (index) => {
    const actions = localWorkflow.actions.filter((_, i) => i !== index);
    setLocalWorkflow({ ...localWorkflow, actions });
  };

  const moveAction = (fromIndex, toIndex) => {
    const actions = [...localWorkflow.actions];
    const [removed] = actions.splice(fromIndex, 1);
    actions.splice(toIndex, 0, removed);
    setLocalWorkflow({ ...localWorkflow, actions });
  };

  return (
    <div className="flex h-full">
      {/* Builder Canvas */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <div className="flex-1 max-w-md">
            <Input
              value={localWorkflow.name}
              onChange={(e) => setLocalWorkflow({ ...localWorkflow, name: e.target.value })}
              placeholder="Workflow name..."
              className="text-lg font-semibold border-none shadow-none focus-visible:ring-0 px-0"
            />
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 mr-4">
              <Switch
                checked={localWorkflow.status === 'active'}
                onCheckedChange={(checked) => setLocalWorkflow({ ...localWorkflow, status: checked ? 'active' : 'draft' })}
              />
              <Label className="text-sm">Active</Label>
            </div>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
            <Button onClick={() => onSave(localWorkflow)} disabled={!localWorkflow.name}>
              Save Workflow
            </Button>
          </div>
        </div>

        {/* Canvas */}
        <ScrollArea className="flex-1 p-8">
          <div className="max-w-md mx-auto space-y-8">
            {/* Trigger Node */}
            <div>
              <p className="text-xs text-muted-foreground mb-3 text-center">WHEN THIS HAPPENS...</p>
              <div className="relative bg-card border-2 border-primary/50 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/20">
                    <Zap className="w-5 h-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <Label className="text-xs text-muted-foreground">Trigger</Label>
                    <Select
                      value={localWorkflow.trigger_type}
                      onValueChange={(value) => setLocalWorkflow({ ...localWorkflow, trigger_type: value })}
                    >
                      <SelectTrigger className="border-none shadow-none p-0 h-auto font-medium">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {triggerTypes.map(trigger => (
                          <SelectItem key={trigger.value} value={trigger.value}>
                            <div className="flex items-center gap-2">
                              <trigger.icon className="w-4 h-4" />
                              {trigger.label}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>

            {/* Connector */}
            <div className="flex flex-col items-center">
              <div className="w-0.5 h-8 bg-border" />
              <ArrowDown className="w-4 h-4 text-muted-foreground" />
            </div>

            {/* Actions */}
            <div>
              <p className="text-xs text-muted-foreground mb-3 text-center">THEN DO THIS...</p>
              
              {localWorkflow.actions.length === 0 ? (
                <div className="border-2 border-dashed rounded-xl p-8 text-center">
                  <Zap className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-50" />
                  <p className="text-muted-foreground mb-4">No actions added yet</p>
                  <Button onClick={() => setShowActionPicker(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add First Action
                  </Button>
                </div>
              ) : (
                <div className="space-y-6">
                  {localWorkflow.actions.map((action, index) => (
                    <WorkflowNode
                      key={index}
                      type="action"
                      data={action}
                      index={index + 1}
                      isLast={index === localWorkflow.actions.length - 1}
                      onEdit={() => setEditingAction(index)}
                      onDelete={removeAction}
                    />
                  ))}
                  
                  {/* Add Action Button */}
                  <div className="flex flex-col items-center">
                    <div className="w-0.5 h-4 bg-border" />
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="rounded-full"
                      onClick={() => setShowActionPicker(true)}
                    >
                      <Plus className="w-4 h-4 mr-1" />
                      Add Action
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </ScrollArea>
      </div>

      {/* Right Panel - Action Editor */}
      {editingAction !== null && (
        <div className="w-80 border-l bg-muted/30 p-4">
          <ActionEditor
            action={localWorkflow.actions[editingAction]}
            index={editingAction}
            onUpdate={updateAction}
            onClose={() => setEditingAction(null)}
          />
        </div>
      )}

      {/* Action Picker Dialog */}
      <Dialog open={showActionPicker} onOpenChange={setShowActionPicker}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Action</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            {actionTypes.map(action => (
              <Card 
                key={action.value}
                className="cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => addAction(action.value)}
              >
                <CardContent className="p-4 flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${action.color}/20`}>
                    <action.icon className={`w-5 h-5 ${action.color.replace('bg-', 'text-')}`} />
                  </div>
                  <span className="font-medium text-sm">{action.label}</span>
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Main Page Component
const WorkflowsPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState(null);

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    try {
      const response = await api.get('/workflows');
      setWorkflows(response.data.workflows);
    } catch (error) {
      console.error('Error fetching workflows:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveWorkflow = async (workflowData) => {
    try {
      if (editingWorkflow?.id) {
        await api.put(`/workflows/${editingWorkflow.id}`, workflowData);
      } else {
        await api.post('/workflows', workflowData);
      }
      setShowBuilder(false);
      setEditingWorkflow(null);
      fetchWorkflows();
    } catch (error) {
      console.error('Error saving workflow:', error);
    }
  };

  const handleUpdateStatus = async (workflowId, status) => {
    try {
      await api.put(`/workflows/${workflowId}`, { status });
      fetchWorkflows();
    } catch (error) {
      console.error('Error updating workflow:', error);
    }
  };

  const handleDeleteWorkflow = async (workflowId) => {
    if (!window.confirm('Are you sure you want to delete this workflow?')) return;
    try {
      await api.delete(`/workflows/${workflowId}`);
      fetchWorkflows();
      if (selectedWorkflow?.id === workflowId) {
        setSelectedWorkflow(null);
      }
    } catch (error) {
      console.error('Error deleting workflow:', error);
    }
  };

  const handleSelectWorkflow = (workflow) => {
    setEditingWorkflow(workflow);
    setShowBuilder(true);
  };

  const handleCreateNew = () => {
    setEditingWorkflow(null);
    setShowBuilder(true);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map(i => (
          <Card key={i}>
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <Skeleton className="w-12 h-12 rounded-lg" />
                <div className="flex-1">
                  <Skeleton className="h-5 w-48 mb-2" />
                  <Skeleton className="h-4 w-64" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Show full-screen builder when creating/editing
  if (showBuilder) {
    return (
      <div className="fixed inset-0 bg-background z-50">
        <WorkflowBuilder
          workflow={editingWorkflow}
          onSave={handleSaveWorkflow}
          onClose={() => {
            setShowBuilder(false);
            setEditingWorkflow(null);
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Automation Workflows</h1>
          <p className="text-muted-foreground">Create automated workflows with visual drag-and-drop builder</p>
        </div>
        <Button onClick={handleCreateNew}>
          <Plus className="w-4 h-4 mr-2" />
          New Workflow
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold">{workflows.length}</p>
              </div>
              <Zap className="w-6 h-6 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active</p>
                <p className="text-2xl font-bold text-green-500">
                  {workflows.filter(w => w.status === 'active').length}
                </p>
              </div>
              <Play className="w-6 h-6 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Paused</p>
                <p className="text-2xl font-bold text-amber-500">
                  {workflows.filter(w => w.status === 'paused').length}
                </p>
              </div>
              <Pause className="w-6 h-6 text-amber-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Runs</p>
                <p className="text-2xl font-bold">
                  {workflows.reduce((sum, w) => sum + (w.total_runs || 0), 0)}
                </p>
              </div>
              <CheckCircle2 className="w-6 h-6 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Workflows List */}
      {workflows.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Zap className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h2 className="text-xl font-semibold mb-2">No workflows yet</h2>
            <p className="text-muted-foreground mb-4">Create your first automation workflow with our visual builder</p>
            <Button onClick={handleCreateNew}>
              <Plus className="w-4 h-4 mr-2" />
              Create Workflow
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {workflows.map(workflow => (
            <WorkflowCard
              key={workflow.id}
              workflow={workflow}
              onSelect={handleSelectWorkflow}
              onStatusChange={handleUpdateStatus}
              onDelete={handleDeleteWorkflow}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default WorkflowsPage;
