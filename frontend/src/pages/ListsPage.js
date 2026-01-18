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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Label } from '../components/ui/label';
import {
  List, Plus, Trash2, Edit, MoreVertical, Search, RefreshCw,
  Users, Filter, ChevronRight, Zap, ListFilter
} from 'lucide-react';

// List Card Component
const ListCard = ({ list, onSelect, onDelete }) => {
  const getTypeColor = (type) => {
    switch (type) {
      case 'static':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'smart':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <Card
      className="cursor-pointer hover:border-primary/50 hover:shadow-lg transition-all group"
      onClick={() => onSelect(list)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${list.type === 'smart' ? 'bg-purple-500/20' : 'bg-blue-500/20'}`}>
              {list.type === 'smart' ? (
                <Zap className="w-5 h-5 text-purple-500" />
              ) : (
                <List className="w-5 h-5 text-blue-500" />
              )}
            </div>
            <div>
              <CardTitle className="text-base">{list.name}</CardTitle>
              <CardDescription className="text-xs">{list.description || 'No description'}</CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={getTypeColor(list.type)}>
              {list.type === 'smart' ? 'Smart' : 'Static'}
            </Badge>
            <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
              <span className="text-muted-foreground">Contacts</span>
              <span className="font-semibold">{list.contact_count || 0}</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
              <span className="text-muted-foreground">Created</span>
              <span className="font-semibold text-xs">
                {list.created_at ? new Date(list.created_at).toLocaleDateString() : '-'}
              </span>
            </div>
          </div>

          {list.type === 'smart' && list.filters && (
            <div className="flex items-center gap-2 text-xs">
              <ListFilter className="w-3 h-3 text-muted-foreground" />
              <span className="text-muted-foreground">
                {Object.keys(list.filters || {}).length} filter(s) applied
              </span>
            </div>
          )}

          <div className="flex items-center gap-2 pt-2 border-t" onClick={e => e.stopPropagation()}>
            <div className="flex-1" />
            <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => onDelete(list.id)}>
              <Trash2 className="w-3 h-3 text-red-500" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Create List Dialog
const CreateListDialog = ({ open, onClose, onCreate }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState('static');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;

    setLoading(true);
    try {
      await onCreate({
        name: name.trim(),
        description: description.trim(),
        type,
        filters: type === 'smart' ? {} : null
      });
      setName('');
      setDescription('');
      setType('static');
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New List</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">List Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Newsletter Subscribers"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              rows={2}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="type">List Type</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="static">
                  <div className="flex items-center gap-2">
                    <List className="w-4 h-4" />
                    <span>Static List</span>
                  </div>
                </SelectItem>
                <SelectItem value="smart">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4" />
                    <span>Smart List (Dynamic)</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {type === 'static'
                ? 'Manually add or remove contacts from this list.'
                : 'Contacts are automatically added based on filter criteria.'}
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleCreate} disabled={!name.trim() || loading}>
            {loading ? 'Creating...' : 'Create List'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Main ListsPage Component
const ListsPage = () => {
  const { api } = useAuth();
  const [lists, setLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedList, setSelectedList] = useState(null);

  // Fetch lists
  const fetchLists = async () => {
    setLoading(true);
    try {
      const response = await api.get('/lists');
      setLists(response.data.lists || []);
    } catch (error) {
      console.error('Error fetching lists:', error);
      setLists([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLists();
  }, []);

  // Create new list
  const handleCreateList = async (listData) => {
    try {
      await api.post('/lists', listData);
      fetchLists();
    } catch (error) {
      console.error('Error creating list:', error);
    }
  };

  // Delete list
  const handleDeleteList = async (listId) => {
    if (!window.confirm('Are you sure you want to delete this list?')) return;

    try {
      await api.delete(`/lists/${listId}`);
      fetchLists();
    } catch (error) {
      console.error('Error deleting list:', error);
    }
  };

  // Filter lists
  const filteredLists = lists.filter(list => {
    const matchesSearch = list.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (list.description && list.description.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesType = typeFilter === 'all' || list.type === typeFilter;
    return matchesSearch && matchesType;
  });

  // Loading skeleton
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-48 rounded-lg" />
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
          <h1 className="text-2xl font-bold">Marketing Lists</h1>
          <p className="text-muted-foreground">Manage your contact lists and segments</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Create List
        </Button>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search lists..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="static">Static Lists</SelectItem>
            <SelectItem value="smart">Smart Lists</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={fetchLists}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-blue-500/20">
                <List className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{lists.length}</p>
                <p className="text-sm text-muted-foreground">Total Lists</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-purple-500/20">
                <Zap className="w-6 h-6 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {lists.filter(l => l.type === 'smart').length}
                </p>
                <p className="text-sm text-muted-foreground">Smart Lists</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-green-500/20">
                <Users className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {lists.reduce((sum, l) => sum + (l.contact_count || 0), 0)}
                </p>
                <p className="text-sm text-muted-foreground">Total Contacts</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Lists Table/Grid */}
      {filteredLists.length === 0 ? (
        <Card className="py-12">
          <CardContent className="text-center">
            <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
              <List className="w-6 h-6 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium mb-2">No lists found</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery || typeFilter !== 'all'
                ? 'Try adjusting your search or filters'
                : 'Create your first marketing list to get started'}
            </p>
            {!searchQuery && typeFilter === 'all' && (
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create List
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredLists.map(list => (
            <ListCard
              key={list.id}
              list={list}
              onSelect={setSelectedList}
              onDelete={handleDeleteList}
            />
          ))}
        </div>
      )}

      {/* Create List Dialog */}
      <CreateListDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onCreate={handleCreateList}
      />
    </div>
  );
};

export default ListsPage;
