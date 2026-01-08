/**
 * Tasks & SLA Management Page
 * 
 * Per Elev8 PRD Section 8:
 * - Task management for sales interactions
 * - SLA monitoring and compliance
 * - Overdue tracking and escalation
 */

import React, { useState, useEffect } from 'react';
import {
  CheckSquare, Clock, AlertTriangle, Plus, Filter, Search,
  Calendar, User, Target, FileText, Phone, Mail, Video,
  MoreVertical, Check, X, Loader2, RefreshCw, AlertCircle,
  ChevronRight, Briefcase, TrendingDown, TrendingUp, Timer
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { ScrollArea } from '../components/ui/scroll-area';
import { useToast } from '../hooks/use-toast';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Task type icons
const taskTypeIcons = {
  call: Phone,
  email: Mail,
  meeting: Video,
  follow_up: Clock,
  demo: Target,
  proposal: FileText,
  contract: FileText,
  review: CheckSquare,
  other: CheckSquare
};

// Priority colors
const priorityColors = {
  low: 'bg-gray-100 text-gray-700',
  medium: 'bg-blue-100 text-blue-700',
  high: 'bg-orange-100 text-orange-700',
  urgent: 'bg-red-100 text-red-700'
};

// Status colors
const statusColors = {
  pending: 'bg-yellow-100 text-yellow-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500'
};

const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const formatDateTime = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString('en-US', { 
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
  });
};

// Task Card Component - moved outside to prevent re-rendering issues
const TaskCard = ({ task, showActions = true, onComplete, onDelete }) => {
  const Icon = taskTypeIcons[task.task_type] || CheckSquare;
  const isOverdue = task.is_overdue || task.status === 'overdue';
  
  return (
    <Card className={`${isOverdue ? 'border-red-300 bg-red-50/50' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1">
            <div className={`p-2 rounded-lg ${isOverdue ? 'bg-red-100' : 'bg-slate-100'}`}>
              <Icon className={`w-4 h-4 ${isOverdue ? 'text-red-600' : 'text-slate-600'}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="font-medium text-sm truncate">{task.title}</h4>
                <Badge className={priorityColors[task.priority]} variant="secondary">
                  {task.priority}
                </Badge>
                <Badge className={statusColors[task.status]} variant="secondary">
                  {task.status?.replace('_', ' ')}
                </Badge>
              </div>
              {task.description && (
                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{task.description}</p>
              )}
              <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {formatDate(task.due_date)}
                </span>
                {task.deal_name && (
                  <span className="flex items-center gap-1">
                    <Briefcase className="w-3 h-3" />
                    {task.deal_name}
                  </span>
                )}
                {task.lead_name && (
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {task.lead_name}
                  </span>
                )}
                {task.assigned_to_name && (
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {task.assigned_to_name}
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {showActions && task.status !== 'completed' && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onComplete && onComplete(task)}>
                  <Check className="w-4 h-4 mr-2" />
                  Mark Complete
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={() => onDelete && onDelete(task.id)}
                  className="text-red-600"
                >
                  <X className="w-4 h-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const TasksPage = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('my-tasks');
  
  // Data state
  const [myTasks, setMyTasks] = useState({ overdue: [], due_today: [], upcoming: [] });
  const [allTasks, setAllTasks] = useState([]);
  const [slaStatus, setSlaStatus] = useState(null);
  const [slaConfig, setSlaConfig] = useState([]);
  
  // Filter state
  const [filters, setFilters] = useState({
    status: '',
    priority: '',
    search: ''
  });
  
  // Dialog state
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCompleteDialog, setShowCompleteDialog] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [completionNotes, setCompletionNotes] = useState('');
  const [saving, setSaving] = useState(false);
  
  // New task form
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    task_type: 'follow_up',
    priority: 'medium',
    due_date: '',
    deal_id: '',
    lead_id: ''
  });

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [myTasksRes, allTasksRes, slaStatusRes, slaConfigRes] = await Promise.all([
        fetch(`${API_URL}/api/elev8/tasks/my-tasks`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/tasks?page_size=50`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/sla/status?entity_type=deals`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/sla/config`, { headers: getAuthHeaders() })
      ]);
      
      if (myTasksRes.ok) setMyTasks(await myTasksRes.json());
      if (allTasksRes.ok) {
        const data = await allTasksRes.json();
        setAllTasks(data.tasks || []);
      }
      if (slaStatusRes.ok) setSlaStatus(await slaStatusRes.json());
      if (slaConfigRes.ok) {
        const data = await slaConfigRes.json();
        setSlaConfig(data.sla_configs || []);
      }
    } catch (error) {
      console.error('Error loading tasks:', error);
      toast({ title: "Error", description: "Failed to load tasks", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateTask = async () => {
    if (!newTask.title || !newTask.due_date) {
      toast({ title: "Error", description: "Title and due date are required", variant: "destructive" });
      return;
    }
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/tasks`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(newTask)
      });
      
      if (response.ok) {
        toast({ title: "Success", description: "Task created successfully" });
        setShowCreateDialog(false);
        setNewTask({
          title: '',
          description: '',
          task_type: 'follow_up',
          priority: 'medium',
          due_date: '',
          deal_id: '',
          lead_id: ''
        });
        loadData();
      } else {
        const error = await response.json();
        toast({ title: "Error", description: error.detail || "Failed to create task", variant: "destructive" });
      }
    } catch (error) {
      console.error('Error creating task:', error);
      toast({ title: "Error", description: "Failed to create task", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleCompleteTask = async () => {
    if (!selectedTask) return;
    
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/tasks/${selectedTask.id}/complete?notes=${encodeURIComponent(completionNotes)}`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        toast({ title: "Success", description: "Task completed" });
        setShowCompleteDialog(false);
        setSelectedTask(null);
        setCompletionNotes('');
        loadData();
      } else {
        toast({ title: "Error", description: "Failed to complete task", variant: "destructive" });
      }
    } catch (error) {
      console.error('Error completing task:', error);
      toast({ title: "Error", description: "Failed to complete task", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTask = async (taskId) => {
    try {
      const response = await fetch(`${API_URL}/api/elev8/tasks/${taskId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        toast({ title: "Success", description: "Task deleted" });
        loadData();
      }
    } catch (error) {
      console.error('Error deleting task:', error);
    }
  };

  const filteredTasks = allTasks.filter(task => {
    if (filters.status && filters.status !== 'all' && task.status !== filters.status) return false;
    if (filters.priority && filters.priority !== 'all' && task.priority !== filters.priority) return false;
    if (filters.search) {
      const search = filters.search.toLowerCase();
      return (
        task.title?.toLowerCase().includes(search) ||
        task.deal_name?.toLowerCase().includes(search) ||
        task.lead_name?.toLowerCase().includes(search)
      );
    }
    return true;
  });

  const TaskCard = ({ task, showActions = true }) => {
    const Icon = taskTypeIcons[task.task_type] || CheckSquare;
    const isOverdue = task.is_overdue || task.status === 'overdue';
    
    return (
      <Card className={`${isOverdue ? 'border-red-300 bg-red-50/50' : ''}`}>
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 flex-1">
              <div className={`p-2 rounded-lg ${isOverdue ? 'bg-red-100' : 'bg-slate-100'}`}>
                <Icon className={`w-4 h-4 ${isOverdue ? 'text-red-600' : 'text-slate-600'}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h4 className="font-medium text-sm truncate">{task.title}</h4>
                  <Badge className={priorityColors[task.priority]} variant="secondary">
                    {task.priority}
                  </Badge>
                  <Badge className={statusColors[task.status]} variant="secondary">
                    {task.status?.replace('_', ' ')}
                  </Badge>
                </div>
                {task.description && (
                  <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{task.description}</p>
                )}
                <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(task.due_date)}
                  </span>
                  {task.deal_name && (
                    <span className="flex items-center gap-1">
                      <Briefcase className="w-3 h-3" />
                      {task.deal_name}
                    </span>
                  )}
                  {task.lead_name && (
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {task.lead_name}
                    </span>
                  )}
                  {task.assigned_to_name && (
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {task.assigned_to_name}
                    </span>
                  )}
                </div>
              </div>
            </div>
            
            {showActions && task.status !== 'completed' && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreVertical className="w-4 h-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => {
                    setSelectedTask(task);
                    setShowCompleteDialog(true);
                  }}>
                    <Check className="w-4 h-4 mr-2" />
                    Mark Complete
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={() => handleDeleteTask(task.id)}
                    className="text-red-600"
                  >
                    <X className="w-4 h-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="tasks-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tasks & SLAs</h1>
          <p className="text-muted-foreground">Manage tasks and monitor SLA compliance</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowCreateDialog(true)} data-testid="create-task-btn">
            <Plus className="w-4 h-4 mr-2" />
            New Task
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Overdue Tasks</p>
                <p className="text-2xl font-bold text-red-600">{myTasks.overdue?.length || 0}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-full">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Due Today</p>
                <p className="text-2xl font-bold text-orange-600">{myTasks.due_today?.length || 0}</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-full">
                <Clock className="w-5 h-5 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Upcoming</p>
                <p className="text-2xl font-bold">{myTasks.upcoming?.length || 0}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <Calendar className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">SLA Breaches</p>
                <p className="text-2xl font-bold text-red-600">{slaStatus?.breached_count || 0}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-full">
                <AlertCircle className="w-5 h-5 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="my-tasks" data-testid="my-tasks-tab">
            <CheckSquare className="w-4 h-4 mr-2" />
            My Tasks
          </TabsTrigger>
          <TabsTrigger value="all-tasks" data-testid="all-tasks-tab">
            <FileText className="w-4 h-4 mr-2" />
            All Tasks
          </TabsTrigger>
          <TabsTrigger value="sla" data-testid="sla-tab">
            <Timer className="w-4 h-4 mr-2" />
            SLA Monitor
          </TabsTrigger>
        </TabsList>

        {/* My Tasks Tab */}
        <TabsContent value="my-tasks" className="mt-4 space-y-6">
          {/* Overdue */}
          {myTasks.overdue?.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-red-600 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Overdue ({myTasks.overdue.length})
              </h3>
              <div className="space-y-3">
                {myTasks.overdue.map(task => (
                  <TaskCard key={task.id} task={task} />
                ))}
              </div>
            </div>
          )}

          {/* Due Today */}
          {myTasks.due_today?.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-orange-600 mb-3 flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Due Today ({myTasks.due_today.length})
              </h3>
              <div className="space-y-3">
                {myTasks.due_today.map(task => (
                  <TaskCard key={task.id} task={task} />
                ))}
              </div>
            </div>
          )}

          {/* Upcoming */}
          {myTasks.upcoming?.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Upcoming ({myTasks.upcoming.length})
              </h3>
              <div className="space-y-3">
                {myTasks.upcoming.map(task => (
                  <TaskCard key={task.id} task={task} />
                ))}
              </div>
            </div>
          )}

          {myTasks.total_pending === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <CheckSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No pending tasks. You&apos;re all caught up!</p>
            </div>
          )}
        </TabsContent>

        {/* All Tasks Tab */}
        <TabsContent value="all-tasks" className="mt-4">
          {/* Filters */}
          <div className="flex items-center gap-3 mb-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search tasks..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-10"
              />
            </div>
            <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="overdue">Overdue</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filters.priority} onValueChange={(v) => setFilters({ ...filters, priority: v })}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priority</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-3">
            {filteredTasks.length > 0 ? (
              filteredTasks.map(task => (
                <TaskCard key={task.id} task={task} />
              ))
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No tasks found</p>
              </div>
            )}
          </div>
        </TabsContent>

        {/* SLA Monitor Tab */}
        <TabsContent value="sla" className="mt-4 space-y-6">
          {/* SLA Overview */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-green-500" />
                  Compliant
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-green-600">{slaStatus?.compliant_count || 0}</p>
                <p className="text-sm text-muted-foreground">Within SLA</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  At Risk
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-orange-600">{slaStatus?.at_risk_count || 0}</p>
                <p className="text-sm text-muted-foreground">Approaching breach</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <TrendingDown className="w-4 h-4 text-red-500" />
                  Breached
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold text-red-600">{slaStatus?.breached_count || 0}</p>
                <p className="text-sm text-muted-foreground">SLA violated</p>
              </CardContent>
            </Card>
          </div>

          {/* SLA Compliance Progress */}
          {slaStatus?.total_count > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Overall SLA Compliance</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Compliance Rate</span>
                    <span className="font-medium">
                      {Math.round((slaStatus.compliant_count / slaStatus.total_count) * 100)}%
                    </span>
                  </div>
                  <Progress 
                    value={(slaStatus.compliant_count / slaStatus.total_count) * 100} 
                    className="h-2"
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {/* Breached Items */}
          {slaStatus?.breached_items?.length > 0 && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-sm text-red-600 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  SLA Breaches - Immediate Action Required
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {slaStatus.breached_items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                      <div>
                        <p className="font-medium text-sm">{item.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {item.hours_since_activity} hours since last activity
                        </p>
                      </div>
                      <Badge variant="destructive">
                        +{item.breach_hours}h over SLA
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* At Risk Items */}
          {slaStatus?.at_risk_items?.length > 0 && (
            <Card className="border-orange-200">
              <CardHeader>
                <CardTitle className="text-sm text-orange-600 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  At Risk - Approaching SLA Breach
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {slaStatus.at_risk_items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                      <div>
                        <p className="font-medium text-sm">{item.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {item.hours_since_activity} hours since last activity
                        </p>
                      </div>
                      <Badge variant="outline" className="border-orange-300 text-orange-700">
                        {item.hours_to_breach}h remaining
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* SLA Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">SLA Configuration</CardTitle>
              <CardDescription>Current SLA rules for your workspace</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {slaConfig.map((config, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 border rounded-lg">
                    <div>
                      <p className="font-medium text-sm">{config.name}</p>
                      <p className="text-xs text-muted-foreground">
                        Applies to: {config.applies_to}
                        {config.source && ` • Source: ${config.source}`}
                        {config.stage && ` • Stage: ${config.stage}`}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-sm">{config.max_hours}h</p>
                      {config.escalation_hours && (
                        <p className="text-xs text-muted-foreground">
                          Escalate at {config.escalation_hours}h
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Task Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Create New Task</DialogTitle>
            <DialogDescription>
              Add a new task to track follow-ups and activities
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Title *</label>
              <Input
                placeholder="Task title..."
                value={newTask.title}
                onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                data-testid="task-title-input"
              />
            </div>
            
            <div>
              <label className="text-sm font-medium">Description</label>
              <Textarea
                placeholder="Task description..."
                value={newTask.description}
                onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                rows={3}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Type</label>
                <Select value={newTask.task_type} onValueChange={(v) => setNewTask({ ...newTask, task_type: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="call">Call</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="meeting">Meeting</SelectItem>
                    <SelectItem value="follow_up">Follow Up</SelectItem>
                    <SelectItem value="demo">Demo</SelectItem>
                    <SelectItem value="proposal">Proposal</SelectItem>
                    <SelectItem value="contract">Contract</SelectItem>
                    <SelectItem value="review">Review</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <label className="text-sm font-medium">Priority</label>
                <Select value={newTask.priority} onValueChange={(v) => setNewTask({ ...newTask, priority: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div>
              <label className="text-sm font-medium">Due Date *</label>
              <Input
                type="datetime-local"
                value={newTask.due_date}
                onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                data-testid="task-due-date-input"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateTask} disabled={saving} data-testid="save-task-btn">
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              Create Task
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Complete Task Dialog */}
      <Dialog open={showCompleteDialog} onOpenChange={setShowCompleteDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Complete Task</DialogTitle>
            <DialogDescription>
              Mark &quot;{selectedTask?.title}&quot; as completed
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Completion Notes (Optional)</label>
              <Textarea
                placeholder="Add any notes about task completion..."
                value={completionNotes}
                onChange={(e) => setCompletionNotes(e.target.value)}
                rows={3}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCompleteDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCompleteTask} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
              Mark Complete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TasksPage;
