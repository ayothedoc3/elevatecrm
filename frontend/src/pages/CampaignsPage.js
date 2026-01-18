import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../components/ui/dropdown-menu';
import { Label } from '../components/ui/label';
import {
  Mail, Plus, Trash2, Edit, MoreVertical, Search, RefreshCw,
  Send, Calendar, Eye, MousePointer, Clock, CheckCircle,
  PauseCircle, PlayCircle, Copy, FileText
} from 'lucide-react';

// Campaign Card Component
const CampaignCard = ({ campaign, onEdit, onDelete, onSend, onDuplicate }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'draft':
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      case 'scheduled':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'sending':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'sent':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'paused':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'cancelled':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'draft':
        return <FileText className="w-3 h-3" />;
      case 'scheduled':
        return <Clock className="w-3 h-3" />;
      case 'sending':
        return <Send className="w-3 h-3" />;
      case 'sent':
        return <CheckCircle className="w-3 h-3" />;
      case 'paused':
        return <PauseCircle className="w-3 h-3" />;
      default:
        return <Mail className="w-3 h-3" />;
    }
  };

  // Calculate open rate
  const openRate = campaign.sent_count > 0
    ? ((campaign.open_count / campaign.sent_count) * 100).toFixed(1)
    : 0;

  return (
    <Card className="hover:border-primary/50 hover:shadow-lg transition-all">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${campaign.campaign_type === 'sms' ? 'bg-purple-500/20' : 'bg-blue-500/20'}`}>
              <Mail className={`w-5 h-5 ${campaign.campaign_type === 'sms' ? 'text-purple-500' : 'text-blue-500'}`} />
            </div>
            <div>
              <CardTitle className="text-base">{campaign.name}</CardTitle>
              <CardDescription className="text-xs truncate max-w-[200px]">
                {campaign.subject || 'No subject'}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`flex items-center gap-1 ${getStatusColor(campaign.status)}`}>
              {getStatusIcon(campaign.status)}
              <span className="capitalize">{campaign.status}</span>
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onEdit(campaign)}>
                  <Edit className="w-4 h-4 mr-2" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDuplicate(campaign.id)}>
                  <Copy className="w-4 h-4 mr-2" />
                  Duplicate
                </DropdownMenuItem>
                {campaign.status === 'draft' && (
                  <DropdownMenuItem onClick={() => onSend(campaign.id)}>
                    <Send className="w-4 h-4 mr-2" />
                    Send Now
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-red-500"
                  onClick={() => onDelete(campaign.id)}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-2 text-center">
            <div className="p-2 bg-muted/50 rounded-lg">
              <Send className="w-4 h-4 mx-auto mb-1 text-muted-foreground" />
              <p className="text-lg font-semibold">{campaign.sent_count || 0}</p>
              <p className="text-xs text-muted-foreground">Sent</p>
            </div>
            <div className="p-2 bg-muted/50 rounded-lg">
              <Eye className="w-4 h-4 mx-auto mb-1 text-muted-foreground" />
              <p className="text-lg font-semibold">{campaign.open_count || 0}</p>
              <p className="text-xs text-muted-foreground">Opens</p>
            </div>
            <div className="p-2 bg-muted/50 rounded-lg">
              <MousePointer className="w-4 h-4 mx-auto mb-1 text-muted-foreground" />
              <p className="text-lg font-semibold">{campaign.click_count || 0}</p>
              <p className="text-xs text-muted-foreground">Clicks</p>
            </div>
            <div className="p-2 bg-muted/50 rounded-lg">
              <p className="text-lg font-semibold">{openRate}%</p>
              <p className="text-xs text-muted-foreground">Open Rate</p>
            </div>
          </div>

          {/* Date info */}
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
            <span>
              {campaign.sent_at
                ? `Sent ${new Date(campaign.sent_at).toLocaleDateString()}`
                : campaign.scheduled_at
                ? `Scheduled ${new Date(campaign.scheduled_at).toLocaleDateString()}`
                : `Created ${new Date(campaign.created_at).toLocaleDateString()}`}
            </span>
            <Badge variant="outline" className="text-xs">
              {campaign.campaign_type === 'sms' ? 'SMS' : 'Email'}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Create Campaign Dialog
const CreateCampaignDialog = ({ open, onClose, onCreate }) => {
  const [name, setName] = useState('');
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [campaignType, setCampaignType] = useState('email');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;

    setLoading(true);
    try {
      await onCreate({
        name: name.trim(),
        subject: subject.trim(),
        content: content.trim(),
        campaign_type: campaignType
      });
      setName('');
      setSubject('');
      setContent('');
      setCampaignType('email');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create New Campaign</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Campaign Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., January Newsletter"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Campaign Type</Label>
              <Select value={campaignType} onValueChange={setCampaignType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4" />
                      <span>Email Campaign</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="sms">
                    <div className="flex items-center gap-2">
                      <Send className="w-4 h-4" />
                      <span>SMS Campaign</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          {campaignType === 'email' && (
            <div className="space-y-2">
              <Label htmlFor="subject">Email Subject</Label>
              <Input
                id="subject"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Enter email subject line..."
              />
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="content">Content</Label>
            <Textarea
              id="content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder={campaignType === 'email' ? 'Write your email content here...' : 'Write your SMS message here...'}
              rows={6}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!name.trim() || loading}>
            {loading ? 'Creating...' : 'Create Campaign'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Main CampaignsPage Component
const CampaignsPage = () => {
  const { api } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [stats, setStats] = useState({
    total_campaigns: 0,
    draft_count: 0,
    scheduled_count: 0,
    sent_count: 0,
    total_emails_sent: 0,
    total_opens: 0,
    total_clicks: 0
  });

  // Fetch campaigns
  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const response = await api.get('/campaigns');
      setCampaigns(response.data.campaigns || []);
    } catch (error) {
      console.error('Error fetching campaigns:', error);
      setCampaigns([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await api.get('/campaigns/stats/overview');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  useEffect(() => {
    fetchCampaigns();
    fetchStats();
  }, []);

  // Create new campaign
  const handleCreateCampaign = async (campaignData) => {
    try {
      await api.post('/campaigns', campaignData);
      fetchCampaigns();
      fetchStats();
    } catch (error) {
      console.error('Error creating campaign:', error);
    }
  };

  // Delete campaign
  const handleDeleteCampaign = async (campaignId) => {
    if (!window.confirm('Are you sure you want to delete this campaign?')) return;

    try {
      await api.delete(`/campaigns/${campaignId}`);
      fetchCampaigns();
      fetchStats();
    } catch (error) {
      console.error('Error deleting campaign:', error);
    }
  };

  // Send campaign
  const handleSendCampaign = async (campaignId) => {
    if (!window.confirm('Are you sure you want to send this campaign now?')) return;

    try {
      await api.post(`/campaigns/${campaignId}/send`);
      fetchCampaigns();
      fetchStats();
    } catch (error) {
      console.error('Error sending campaign:', error);
    }
  };

  // Duplicate campaign
  const handleDuplicateCampaign = async (campaignId) => {
    try {
      await api.post(`/campaigns/${campaignId}/duplicate`);
      fetchCampaigns();
      fetchStats();
    } catch (error) {
      console.error('Error duplicating campaign:', error);
    }
  };

  // Edit campaign (placeholder for now)
  const handleEditCampaign = (campaign) => {
    console.log('Edit campaign:', campaign);
    // TODO: Implement edit dialog
  };

  // Filter campaigns
  const filteredCampaigns = campaigns.filter(campaign => {
    const matchesSearch = campaign.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (campaign.subject && campaign.subject.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesStatus = statusFilter === 'all' || campaign.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-64 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Email Campaigns</h1>
          <p className="text-muted-foreground">Create and manage your marketing campaigns</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Create Campaign
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-blue-500/20">
                <Mail className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total_campaigns}</p>
                <p className="text-sm text-muted-foreground">Total Campaigns</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-green-500/20">
                <Send className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total_emails_sent}</p>
                <p className="text-sm text-muted-foreground">Emails Sent</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-purple-500/20">
                <Eye className="w-6 h-6 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total_opens}</p>
                <p className="text-sm text-muted-foreground">Total Opens</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-orange-500/20">
                <MousePointer className="w-6 h-6 text-orange-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total_clicks}</p>
                <p className="text-sm text-muted-foreground">Total Clicks</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
            <SelectItem value="sent">Sent</SelectItem>
            <SelectItem value="paused">Paused</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={fetchCampaigns}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Campaigns Grid */}
      {filteredCampaigns.length === 0 ? (
        <Card className="py-12">
          <CardContent className="text-center">
            <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
              <Mail className="w-6 h-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium mb-2">No campaigns found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery || statusFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first email campaign to get started'}
            </p>
            {!searchQuery && statusFilter === 'all' && (
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Campaign
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCampaigns.map(campaign => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              onEdit={handleEditCampaign}
              onDelete={handleDeleteCampaign}
              onSend={handleSendCampaign}
              onDuplicate={handleDuplicateCampaign}
            />
          ))}
        </div>
      )}

      {/* Create Campaign Dialog */}
      <CreateCampaignDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onCreate={handleCreateCampaign}
      />
    </div>
  );
};

export default CampaignsPage;
