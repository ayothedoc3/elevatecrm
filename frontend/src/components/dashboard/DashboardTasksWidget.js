/**
 * Dashboard Tasks Widget
 * Displays today's tasks and SLA breaches on the dashboard
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckSquare, AlertTriangle, Clock, ChevronRight,
  Phone, Mail, Video, FileText, Target, Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';

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

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
};

// Task Item Component - moved outside to prevent re-rendering issues
const TaskItem = ({ task }) => {
  const Icon = taskTypeIcons[task.task_type] || CheckSquare;
  const isOverdue = task.status === 'overdue';

  return (
    <div className={`flex items-center gap-3 p-3 rounded-lg transition-colors hover:bg-muted/50 ${isOverdue ? 'bg-red-50' : ''}`}>
      <div className={`p-2 rounded-lg ${isOverdue ? 'bg-red-100' : 'bg-slate-100'}`}>
        <Icon className={`w-4 h-4 ${isOverdue ? 'text-red-600' : 'text-slate-600'}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm truncate">{task.title}</p>
        <p className="text-xs text-muted-foreground">
          {task.deal_name || task.lead_name || formatDate(task.due_date)}
        </p>
      </div>
      <Badge className={priorityColors[task.priority]} variant="secondary">
        {task.priority}
      </Badge>
    </div>
  );
};

const DashboardTasksWidget = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({
    overdue: [],
    dueToday: [],
    slaBreaches: 0,
    slaAtRisk: 0
  });

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [tasksRes, slaRes] = await Promise.all([
          fetch(`${API_URL}/api/elev8/tasks/my-tasks`, { headers: getAuthHeaders() }),
          fetch(`${API_URL}/api/elev8/sla/status?entity_type=deals`, { headers: getAuthHeaders() })
        ]);

        if (tasksRes.ok) {
          const tasks = await tasksRes.json();
          setData(prev => ({
            ...prev,
            overdue: tasks.overdue || [],
            dueToday: tasks.due_today || []
          }));
        }

        if (slaRes.ok) {
          const sla = await slaRes.json();
          setData(prev => ({
            ...prev,
            slaBreaches: sla.breached_count || 0,
            slaAtRisk: sla.at_risk_count || 0
          }));
        }
      } catch (error) {
        console.error('Error fetching dashboard tasks:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const TaskItem = ({ task }) => {
    const Icon = taskTypeIcons[task.task_type] || CheckSquare;
    const isOverdue = task.status === 'overdue';

    return (
      <div className={`flex items-center gap-3 p-3 rounded-lg transition-colors hover:bg-muted/50 ${isOverdue ? 'bg-red-50' : ''}`}>
        <div className={`p-2 rounded-lg ${isOverdue ? 'bg-red-100' : 'bg-slate-100'}`}>
          <Icon className={`w-4 h-4 ${isOverdue ? 'text-red-600' : 'text-slate-600'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{task.title}</p>
          <p className="text-xs text-muted-foreground">
            {task.deal_name || task.lead_name || formatDate(task.due_date)}
          </p>
        </div>
        <Badge className={priorityColors[task.priority]} variant="secondary">
          {task.priority}
        </Badge>
      </div>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const totalTasks = data.overdue.length + data.dueToday.length;
  const hasAlerts = data.overdue.length > 0 || data.slaBreaches > 0;

  return (
    <Card className={hasAlerts ? 'border-orange-200' : ''}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <CheckSquare className="w-5 h-5" />
              Today&apos;s Tasks
            </CardTitle>
            <CardDescription>
              {totalTasks} task{totalTasks !== 1 ? 's' : ''} pending
            </CardDescription>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => navigate('/tasks')}
            data-testid="view-all-tasks-btn"
          >
            View All
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Alert Summary */}
        {hasAlerts && (
          <div className="flex gap-3 mb-4">
            {data.overdue.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-2 bg-red-50 text-red-700 rounded-lg text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-medium">{data.overdue.length} Overdue</span>
              </div>
            )}
            {data.slaBreaches > 0 && (
              <div className="flex items-center gap-2 px-3 py-2 bg-orange-50 text-orange-700 rounded-lg text-sm">
                <Clock className="w-4 h-4" />
                <span className="font-medium">{data.slaBreaches} SLA Breach{data.slaBreaches !== 1 ? 'es' : ''}</span>
              </div>
            )}
            {data.slaAtRisk > 0 && (
              <div className="flex items-center gap-2 px-3 py-2 bg-yellow-50 text-yellow-700 rounded-lg text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-medium">{data.slaAtRisk} At Risk</span>
              </div>
            )}
          </div>
        )}

        {/* Task List */}
        <ScrollArea className="h-[200px]">
          <div className="space-y-2">
            {/* Overdue Tasks */}
            {data.overdue.map(task => (
              <TaskItem key={task.id} task={task} />
            ))}
            
            {/* Due Today Tasks */}
            {data.dueToday.map(task => (
              <TaskItem key={task.id} task={task} />
            ))}

            {totalTasks === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <CheckSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No tasks for today!</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default DashboardTasksWidget;
