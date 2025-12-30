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
import {
  Zap, Plus, Play, Pause, Trash2, Edit, MoreHorizontal,
  Mail, MessageSquare, Clock, CheckCircle2, XCircle, AlertTriangle,
  FileText, Tag, User, ArrowRight
} from 'lucide-react';

const triggerTypes = [
  { value: 'form_submitted', label: 'Form Submitted', icon: FileText },
  { value: 'deal_stage_changed', label: 'Deal Stage Changed', icon: ArrowRight },
  { value: 'deal_created', label: 'Deal Created', icon: Plus },
  { value: 'contact_created', label: 'Contact Created', icon: User },
  { value: 'message_received', label: 'Message Received', icon: MessageSquare },
  { value: 'manual', label: 'Manual Trigger', icon: Play },
];

const actionTypes = [
  { value: 'send_email', label: 'Send Email', icon: Mail },
  { value: 'send_sms', label: 'Send SMS', icon: MessageSquare },
  { value: 'create_task', label: 'Create Task', icon: CheckCircle2 },
  { value: 'add_tag', label: 'Add Tag', icon: Tag },
  { value: 'set_property', label: 'Set Property', icon: Edit },
  { value: 'delay', label: 'Wait/Delay', icon: Clock },
];

const WorkflowsPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [workflows, setWorkflows] = useState([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [newWorkflow, setNewWorkflow] = useState({
    name: '',
    description: '',
    trigger_type: 'form_submitted',
    trigger_config: {},
    actions: [],
    status: 'draft'
  });

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

  const handleCreateWorkflow = async () => {
    if (!newWorkflow.name) return;
    setCreating(true);
    try {
      await api.post('/workflows', newWorkflow);
      setShowCreateModal(false);
      setNewWorkflow({
        name: '',
        description: '',
        trigger_type: 'form_submitted',
        trigger_config: {},
        actions: [],
        status: 'draft'
      });
      fetchWorkflows();
    } catch (error) {
      console.error('Error creating workflow:', error);
    } finally {
      setCreating(false);
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
    } catch (error) {
      console.error('Error deleting workflow:', error);
    }
  };

  const addAction = (type) => {
    const action = { type, config: {}, delay_minutes: 0 };
    setNewWorkflow({
      ...newWorkflow,
      actions: [...newWorkflow.actions, action]
    });
  };

  const updateAction = (index, updates) => {
    const actions = [...newWorkflow.actions];
    actions[index] = { ...actions[index], ...updates };
    setNewWorkflow({ ...newWorkflow, actions });
  };

  const removeAction = (index) => {
    const actions = newWorkflow.actions.filter((_, i) => i !== index);
    setNewWorkflow({ ...newWorkflow, actions });
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-500/20 text-green-400"><Play className="w-3 h-3 mr-1" />Active</Badge>;
      case 'paused':
        return <Badge className="bg-amber-500/20 text-amber-400"><Pause className="w-3 h-3 mr-1" />Paused</Badge>;
      case 'draft':
        return <Badge variant="secondary"><Edit className="w-3 h-3 mr-1" />Draft</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getTriggerIcon = (type) => {
    const trigger = triggerTypes.find(t => t.value === type);
    return trigger?.icon || Zap;
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
          <h1 className="text-2xl font-bold">Automation Workflows</h1>
          <p className="text-muted-foreground">Create automated workflows to streamline your processes</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Workflow
        </Button>
      </div>

      {/* Workflows List */}
      {workflows.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Zap className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h2 className="text-xl font-semibold mb-2">No workflows yet</h2>
            <p className="text-muted-foreground mb-4">Create your first automation workflow</p>
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Create Workflow
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {workflows.map(workflow => {
            const TriggerIcon = getTriggerIcon(workflow.trigger_type);
            return (
              <Card key={workflow.id} className="hover:border-primary/50 transition-colors">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4">
                      <div className="p-3 rounded-lg bg-primary/10">
                        <TriggerIcon className="w-6 h-6 text-primary" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold">{workflow.name}</h3>
                          {getStatusBadge(workflow.status)}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {workflow.description || 'No description'}
                        </p>
                        <div className="flex items-center gap-4 mt-3 text-sm">
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <TriggerIcon className="w-4 h-4" />
                            {triggerTypes.find(t => t.value === workflow.trigger_type)?.label}
                          </span>
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <Zap className="w-4 h-4" />
                            {workflow.actions?.length || 0} actions
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-right mr-4">
                        <p className="text-2xl font-bold">{workflow.total_runs}</p>
                        <p className="text-xs text-muted-foreground">Total Runs</p>
                      </div>
                      <div className="text-right mr-4">
                        <p className="text-lg text-green-500">{workflow.successful_runs}</p>
                        <p className="text-xs text-muted-foreground">Successful</p>
                      </div>
                      {workflow.status === 'active' ? (
                        <Button variant="outline" size="sm" onClick={() => handleUpdateStatus(workflow.id, 'paused')}>
                          <Pause className="w-4 h-4" />
                        </Button>
                      ) : (
                        <Button variant="outline" size="sm" onClick={() => handleUpdateStatus(workflow.id, 'active')}>
                          <Play className="w-4 h-4" />
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" onClick={() => handleDeleteWorkflow(workflow.id)}>
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Workflow Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Workflow</DialogTitle>
          </DialogHeader>
          <div className="space-y-6">
            <div className="space-y-2">
              <Label>Workflow Name</Label>
              <Input
                value={newWorkflow.name}
                onChange={(e) => setNewWorkflow({ ...newWorkflow, name: e.target.value })}
                placeholder="e.g., Welcome Email Sequence"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                value={newWorkflow.description}
                onChange={(e) => setNewWorkflow({ ...newWorkflow, description: e.target.value })}
                placeholder="Describe what this workflow does..."
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Trigger</Label>
              <Select
                value={newWorkflow.trigger_type}
                onValueChange={(value) => setNewWorkflow({ ...newWorkflow, trigger_type: value })}
              >
                <SelectTrigger>
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
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>Actions</Label>
                <Select onValueChange={addAction}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Add action..." />
                  </SelectTrigger>
                  <SelectContent>
                    {actionTypes.map(action => (
                      <SelectItem key={action.value} value={action.value}>
                        <div className="flex items-center gap-2">
                          <action.icon className="w-4 h-4" />
                          {action.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {newWorkflow.actions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                  <Zap className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No actions added yet</p>
                  <p className="text-sm">Add actions to define what happens when this workflow triggers</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {newWorkflow.actions.map((action, index) => {
                    const actionType = actionTypes.find(a => a.value === action.type);
                    const ActionIcon = actionType?.icon || Zap;
                    return (
                      <Card key={index}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                                <span className="text-sm font-medium">{index + 1}</span>
                              </div>
                              <div>
                                <div className="flex items-center gap-2">
                                  <ActionIcon className="w-4 h-4" />
                                  <span className="font-medium">{actionType?.label}</span>
                                </div>
                                
                                {action.type === 'send_email' && (
                                  <div className="mt-2 space-y-2">
                                    <Input
                                      placeholder="Subject"
                                      value={action.config.subject || ''}
                                      onChange={(e) => updateAction(index, { config: { ...action.config, subject: e.target.value } })}
                                      className="text-sm"
                                    />
                                    <Textarea
                                      placeholder="Email body..."
                                      value={action.config.body || ''}
                                      onChange={(e) => updateAction(index, { config: { ...action.config, body: e.target.value } })}
                                      rows={2}
                                      className="text-sm"
                                    />
                                  </div>
                                )}
                                
                                {action.type === 'send_sms' && (
                                  <Textarea
                                    placeholder="SMS message..."
                                    value={action.config.body || ''}
                                    onChange={(e) => updateAction(index, { config: { ...action.config, body: e.target.value } })}
                                    rows={2}
                                    className="mt-2 text-sm"
                                  />
                                )}
                                
                                {action.type === 'delay' && (
                                  <div className="flex items-center gap-2 mt-2">
                                    <Input
                                      type="number"
                                      value={action.delay_minutes || 0}
                                      onChange={(e) => updateAction(index, { delay_minutes: parseInt(e.target.value) || 0 })}
                                      className="w-20 text-sm"
                                    />
                                    <span className="text-sm text-muted-foreground">minutes</span>
                                  </div>
                                )}
                                
                                {action.type === 'add_tag' && (
                                  <Input
                                    placeholder="Tag name"
                                    value={action.config.tag || ''}
                                    onChange={(e) => updateAction(index, { config: { ...action.config, tag: e.target.value } })}
                                    className="mt-2 text-sm"
                                  />
                                )}
                              </div>
                            </div>
                            <Button variant="ghost" size="sm" onClick={() => removeAction(index)}>
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <Switch
                checked={newWorkflow.status === 'active'}
                onCheckedChange={(checked) => setNewWorkflow({ ...newWorkflow, status: checked ? 'active' : 'draft' })}
              />
              <Label>Activate immediately</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button onClick={handleCreateWorkflow} disabled={creating || !newWorkflow.name}>
              {creating ? 'Creating...' : 'Create Workflow'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default WorkflowsPage;
