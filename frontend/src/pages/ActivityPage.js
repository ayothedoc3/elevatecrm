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
import { ScrollArea } from '../components/ui/scroll-area';
import { Skeleton } from '../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Activity, Plus, Filter, Search, Phone, Mail, MessageSquare,
  Calendar, FileText, ArrowRight, CheckCircle, XCircle, Clock,
  User, Building, Target, Edit2, Trash2, Loader2, RefreshCw,
  ChevronLeft, ChevronRight, AlertCircle, DollarSign, Send
} from 'lucide-react';
import { toast } from 'sonner';
import { format, formatDistanceToNow, isToday, isYesterday, parseISO } from 'date-fns';

const EVENT_TYPE_CONFIG = {
  note: { icon: FileText, color: 'text-gray-500', bg: 'bg-gray-500/20', label: 'Note' },
  task: { icon: CheckCircle, color: 'text-blue-500', bg: 'bg-blue-500/20', label: 'Task' },
  call_log: { icon: Phone, color: 'text-green-500', bg: 'bg-green-500/20', label: 'Call' },
  meeting: { icon: Calendar, color: 'text-purple-500', bg: 'bg-purple-500/20', label: 'Meeting' },
  email_sent: { icon: Send, color: 'text-blue-400', bg: 'bg-blue-400/20', label: 'Email Sent' },
  email_received: { icon: Mail, color: 'text-cyan-500', bg: 'bg-cyan-500/20', label: 'Email Received' },
  sms_sent: { icon: MessageSquare, color: 'text-green-400', bg: 'bg-green-400/20', label: 'SMS Sent' },
  sms_received: { icon: MessageSquare, color: 'text-teal-500', bg: 'bg-teal-500/20', label: 'SMS Received' },
  stage_changed: { icon: ArrowRight, color: 'text-orange-500', bg: 'bg-orange-500/20', label: 'Stage Changed' },
  deal_created: { icon: Target, color: 'text-indigo-500', bg: 'bg-indigo-500/20', label: 'Deal Created' },
  deal_won: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-600/20', label: 'Deal Won' },
  deal_lost: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/20', label: 'Deal Lost' },
  contact_created: { icon: User, color: 'text-blue-500', bg: 'bg-blue-500/20', label: 'Contact Created' },
  payment_completed: { icon: DollarSign, color: 'text-green-500', bg: 'bg-green-500/20', label: 'Payment Completed' },
  form_submitted: { icon: FileText, color: 'text-purple-500', bg: 'bg-purple-500/20', label: 'Form Submitted' },
};

const ActivityPage = () => {
  const { token } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filterType, setFilterType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newEvent, setNewEvent] = useState({
    event_type: 'note',
    title: '',
    description: '',
    visibility: 'internal_only'
  });
  
  const pageSize = 20;

  const api = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      let url = `/timeline?page=${page}&page_size=${pageSize}`;
      if (filterType !== 'all') {
        url += `&event_type=${filterType}`;
      }
      const response = await api.get(url);
      setEvents(response.data.events || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching events:', error);
      toast.error('Failed to load activity timeline');
    } finally {
      setLoading(false);
    }
  }, [page, filterType]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const handleCreateEvent = async () => {
    if (!newEvent.title.trim()) {
      toast.error('Title is required');
      return;
    }
    
    setCreating(true);
    try {
      await api.post('/timeline', newEvent);
      toast.success('Activity logged');
      setShowCreateDialog(false);
      setNewEvent({ event_type: 'note', title: '', description: '', visibility: 'internal_only' });
      fetchEvents();
    } catch (error) {
      console.error('Error creating event:', error);
      toast.error('Failed to log activity');
    } finally {
      setCreating(false);
    }
  };

  const formatEventDate = (dateString) => {
    const date = parseISO(dateString);
    if (isToday(date)) return `Today at ${format(date, 'h:mm a')}`;
    if (isYesterday(date)) return `Yesterday at ${format(date, 'h:mm a')}`;
    return format(date, 'MMM d, yyyy • h:mm a');
  };

  const getEventConfig = (type) => {
    return EVENT_TYPE_CONFIG[type] || { icon: Activity, color: 'text-gray-500', bg: 'bg-gray-500/20', label: type };
  };

  const groupEventsByDate = (events) => {
    const groups = {};
    events.forEach(event => {
      const date = parseISO(event.created_at);
      let key;
      if (isToday(date)) key = 'Today';
      else if (isYesterday(date)) key = 'Yesterday';
      else key = format(date, 'EEEE, MMM d');
      
      if (!groups[key]) groups[key] = [];
      groups[key].push(event);
    });
    return groups;
  };

  const totalPages = Math.ceil(total / pageSize);
  const groupedEvents = groupEventsByDate(events);

  // Filter events by search query
  const filteredEvents = searchQuery 
    ? events.filter(e => 
        e.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.description?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : events;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Activity className="w-6 h-6" />
            Activity Timeline
          </h1>
          <p className="text-muted-foreground">All activity across your CRM</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchEvents} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Log Activity
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Log Activity</DialogTitle>
                <DialogDescription>Create a new activity entry</DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Activity Type</Label>
                  <Select value={newEvent.event_type} onValueChange={(v) => setNewEvent({...newEvent, event_type: v})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="note">📝 Note</SelectItem>
                      <SelectItem value="task">✅ Task</SelectItem>
                      <SelectItem value="call_log">📞 Call</SelectItem>
                      <SelectItem value="meeting">📅 Meeting</SelectItem>
                      <SelectItem value="email_sent">📧 Email Sent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label>Title *</Label>
                  <Input
                    value={newEvent.title}
                    onChange={(e) => setNewEvent({...newEvent, title: e.target.value})}
                    placeholder="Brief description..."
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Details</Label>
                  <Textarea
                    value={newEvent.description}
                    onChange={(e) => setNewEvent({...newEvent, description: e.target.value})}
                    placeholder="Additional details..."
                    rows={3}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label>Visibility</Label>
                  <Select value={newEvent.visibility} onValueChange={(v) => setNewEvent({...newEvent, visibility: v})}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="internal_only">Internal Only</SelectItem>
                      <SelectItem value="client_visible">Client Visible</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancel</Button>
                <Button onClick={handleCreateEvent} disabled={creating}>
                  {creating && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Log Activity
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Activities</p>
                <p className="text-2xl font-bold">{total}</p>
              </div>
              <Activity className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Calls Today</p>
                <p className="text-2xl font-bold">
                  {events.filter(e => e.event_type === 'call_log' && isToday(parseISO(e.created_at))).length}
                </p>
              </div>
              <Phone className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Emails Today</p>
                <p className="text-2xl font-bold">
                  {events.filter(e => (e.event_type === 'email_sent' || e.event_type === 'email_received') && isToday(parseISO(e.created_at))).length}
                </p>
              </div>
              <Mail className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Stage Changes</p>
                <p className="text-2xl font-bold">
                  {events.filter(e => e.event_type === 'stage_changed').length}
                </p>
              </div>
              <ArrowRight className="w-8 h-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search activities..."
                className="pl-9"
              />
            </div>
            
            <Select value={filterType} onValueChange={(v) => { setFilterType(v); setPage(1); }}>
              <SelectTrigger className="w-48">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Activities</SelectItem>
                <SelectItem value="note">Notes</SelectItem>
                <SelectItem value="task">Tasks</SelectItem>
                <SelectItem value="call_log">Calls</SelectItem>
                <SelectItem value="meeting">Meetings</SelectItem>
                <SelectItem value="email_sent">Emails Sent</SelectItem>
                <SelectItem value="email_received">Emails Received</SelectItem>
                <SelectItem value="stage_changed">Stage Changes</SelectItem>
                <SelectItem value="deal_created">Deals Created</SelectItem>
                <SelectItem value="contact_created">Contacts Created</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card>
        <CardContent className="py-6">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex gap-4">
                  <Skeleton className="w-10 h-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredEvents.length === 0 ? (
            <div className="text-center py-12">
              <Activity className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-semibold text-lg mb-2">No Activities Found</h3>
              <p className="text-muted-foreground mb-4">
                {filterType !== 'all' ? 'No activities match your filter' : 'Start logging activities to see them here'}
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Log Activity
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(groupEventsByDate(filteredEvents)).map(([date, dateEvents]) => (
                <div key={date}>
                  <h3 className="text-sm font-semibold text-muted-foreground mb-3 sticky top-0 bg-card py-2">
                    {date}
                  </h3>
                  <div className="space-y-1">
                    {dateEvents.map((event, index) => {
                      const config = getEventConfig(event.event_type);
                      const Icon = config.icon;
                      
                      return (
                        <div key={event.id} className="flex gap-4 p-3 rounded-lg hover:bg-muted/50 transition-colors group">
                          <div className={`w-10 h-10 rounded-full ${config.bg} flex items-center justify-center flex-shrink-0`}>
                            <Icon className={`w-5 h-5 ${config.color}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <p className="font-medium">{event.title}</p>
                                {event.description && (
                                  <p className="text-sm text-muted-foreground line-clamp-2 mt-1">{event.description}</p>
                                )}
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <Badge variant="outline" className="text-xs">
                                  {config.label}
                                </Badge>
                              </div>
                            </div>
                            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {format(parseISO(event.created_at), 'h:mm a')}
                              </span>
                              {event.actor_name && (
                                <span className="flex items-center gap-1">
                                  <User className="w-3 h-3" />
                                  {event.actor_name}
                                </span>
                              )}
                              {event.visibility === 'client_visible' && (
                                <Badge variant="secondary" className="text-xs">Client Visible</Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ActivityPage;
