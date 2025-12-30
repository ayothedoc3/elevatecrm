import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
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
  SheetDescription,
} from '../components/ui/sheet';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Search, Plus, Mail, Phone, Building, User, MoreHorizontal,
  ChevronLeft, ChevronRight, Filter, Download, MapPin, Calendar,
  Target, DollarSign, Clock, Edit, Trash2, MessageSquare, Flame
} from 'lucide-react';

const ContactsPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [contacts, setContacts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedContact, setSelectedContact] = useState(null);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  const [contactDeals, setContactDeals] = useState([]);
  const [newContact, setNewContact] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    company_name: '',
    lifecycle_stage: 'lead'
  });

  useEffect(() => {
    fetchContacts();
  }, [page, search]);

  const fetchContacts = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      if (search) params.append('search', search);
      
      const response = await api.get(`/contacts?${params}`);
      setContacts(response.data.contacts);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Error fetching contacts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchContactDeals = async (contactId) => {
    try {
      const response = await api.get(`/deals?contact_id=${contactId}`);
      setContactDeals(response.data.deals || []);
    } catch (error) {
      console.error('Error fetching contact deals:', error);
      setContactDeals([]);
    }
  };

  const handleContactClick = async (contact) => {
    setSelectedContact(contact);
    setShowDetailSheet(true);
    await fetchContactDeals(contact.id);
  };

  const closeDetailSheet = () => {
    setShowDetailSheet(false);
    setSelectedContact(null);
    setContactDeals([]);
  };

  const handleCreateContact = async () => {
    setCreating(true);
    try {
      await api.post('/contacts', newContact);
      setShowCreateModal(false);
      setNewContact({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        company_name: '',
        lifecycle_stage: 'lead'
      });
      fetchContacts();
    } catch (error) {
      console.error('Error creating contact:', error);
    } finally {
      setCreating(false);
    }
  };

  const getLifecycleBadge = (stage) => {
    const colors = {
      lead: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      subscriber: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      opportunity: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      customer: 'bg-green-500/20 text-green-400 border-green-500/30',
      evangelist: 'bg-pink-500/20 text-pink-400 border-pink-500/30'
    };
    return (
      <Badge className={colors[stage] || 'bg-gray-500/20 text-gray-400'}>
        {stage}
      </Badge>
    );
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0
    }).format(value || 0);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Contacts</h1>
          <p className="text-muted-foreground">{total} total contacts</p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Add Contact
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search contacts..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button variant="outline">
              <Filter className="w-4 h-4 mr-2" />
              Filters
            </Button>
            <Button variant="outline">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Contact</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Lifecycle Stage</TableHead>
                <TableHead>Created</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <TableRow key={i}>
                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-28" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                    <TableCell><Skeleton className="h-4 w-8" /></TableCell>
                  </TableRow>
                ))
              ) : contacts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No contacts found
                  </TableCell>
                </TableRow>
              ) : (
                contacts.map(contact => (
                  <TableRow 
                    key={contact.id} 
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleContactClick(contact)}
                  >
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-orange-500/10 flex items-center justify-center">
                          <User className="w-5 h-5 text-orange-500" />
                        </div>
                        <div>
                          <p className="font-medium">{contact.full_name}</p>
                          {contact.job_title && (
                            <p className="text-xs text-muted-foreground">{contact.job_title}</p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Mail className="w-3 h-3 text-muted-foreground" />
                        {contact.email || '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Phone className="w-3 h-3 text-muted-foreground" />
                        {contact.phone || '-'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Building className="w-3 h-3 text-muted-foreground" />
                        {contact.company_name || '-'}
                      </div>
                    </TableCell>
                    <TableCell>{getLifecycleBadge(contact.lifecycle_stage)}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(contact.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" onClick={(e) => e.stopPropagation()}>
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <p className="text-sm text-muted-foreground">
                Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, total)} of {total}
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

      {/* Contact Detail Sheet */}
      <Sheet open={showDetailSheet} onOpenChange={setShowDetailSheet}>
        <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col">
          {selectedContact && (
            <>
              <SheetHeader className="p-6 border-b">
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 rounded-full bg-orange-500/10 flex items-center justify-center">
                    <User className="w-8 h-8 text-orange-500" />
                  </div>
                  <div className="flex-1">
                    <SheetTitle className="text-xl">{selectedContact.full_name}</SheetTitle>
                    <SheetDescription>
                      {selectedContact.company_name && (
                        <span className="flex items-center gap-1">
                          <Building className="w-4 h-4" />
                          {selectedContact.company_name}
                        </span>
                      )}
                    </SheetDescription>
                    <div className="mt-2">
                      {getLifecycleBadge(selectedContact.lifecycle_stage)}
                    </div>
                  </div>
                </div>
              </SheetHeader>

              <Tabs defaultValue="details" className="flex-1 flex flex-col">
                <TabsList className="mx-6 mt-4">
                  <TabsTrigger value="details">Details</TabsTrigger>
                  <TabsTrigger value="deals">Deals ({contactDeals.length})</TabsTrigger>
                  <TabsTrigger value="activity">Activity</TabsTrigger>
                </TabsList>

                <ScrollArea className="flex-1">
                  <TabsContent value="details" className="p-6 space-y-4">
                    {/* Contact Info */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Contact Information</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-xs text-muted-foreground">Email</Label>
                            <p className="font-medium flex items-center gap-2">
                              <Mail className="w-4 h-4 text-muted-foreground" />
                              {selectedContact.email || '-'}
                            </p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Phone</Label>
                            <p className="font-medium flex items-center gap-2">
                              <Phone className="w-4 h-4 text-muted-foreground" />
                              {selectedContact.phone || '-'}
                            </p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Company</Label>
                            <p className="font-medium flex items-center gap-2">
                              <Building className="w-4 h-4 text-muted-foreground" />
                              {selectedContact.company_name || '-'}
                            </p>
                          </div>
                          <div>
                            <Label className="text-xs text-muted-foreground">Created</Label>
                            <p className="font-medium flex items-center gap-2">
                              <Calendar className="w-4 h-4 text-muted-foreground" />
                              {formatDate(selectedContact.created_at)}
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Quick Actions */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Quick Actions</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-4 gap-2">
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <Phone className="w-4 h-4" />
                            <span className="text-xs">Call</span>
                          </Button>
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <Mail className="w-4 h-4" />
                            <span className="text-xs">Email</span>
                          </Button>
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <MessageSquare className="w-4 h-4" />
                            <span className="text-xs">SMS</span>
                          </Button>
                          <Button variant="outline" size="sm" className="h-16 flex-col gap-1">
                            <Target className="w-4 h-4" />
                            <span className="text-xs">Deal</span>
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>

                  <TabsContent value="deals" className="p-6 space-y-4">
                    {contactDeals.length > 0 ? (
                      <div className="space-y-3">
                        {contactDeals.map(deal => (
                          <Card key={deal.id} className="cursor-pointer hover:border-primary/50">
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                                    <Flame className="w-5 h-5 text-orange-500" />
                                  </div>
                                  <div>
                                    <p className="font-medium">{deal.name}</p>
                                    <p className="text-sm text-muted-foreground">{deal.stage_name}</p>
                                  </div>
                                </div>
                                <div className="text-right">
                                  <p className="font-bold text-primary">{formatCurrency(deal.amount)}</p>
                                  <Badge variant="outline" className="text-xs">
                                    {deal.status}
                                  </Badge>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <Target className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        <p>No deals found</p>
                        <Button variant="outline" className="mt-4">
                          <Plus className="w-4 h-4 mr-2" />
                          Create Deal
                        </Button>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="activity" className="p-6 space-y-4">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Recent Activity</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center mt-1">
                              <Mail className="w-4 h-4 text-green-500" />
                            </div>
                            <div>
                              <p className="font-medium text-sm">Email Sent</p>
                              <p className="text-xs text-muted-foreground">Introduction email sent</p>
                              <p className="text-xs text-muted-foreground mt-1">2 days ago</p>
                            </div>
                          </div>
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center mt-1">
                              <Phone className="w-4 h-4 text-blue-500" />
                            </div>
                            <div>
                              <p className="font-medium text-sm">Call Logged</p>
                              <p className="text-xs text-muted-foreground">Outbound call - voicemail</p>
                              <p className="text-xs text-muted-foreground mt-1">3 days ago</p>
                            </div>
                          </div>
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center mt-1">
                              <User className="w-4 h-4 text-purple-500" />
                            </div>
                            <div>
                              <p className="font-medium text-sm">Contact Created</p>
                              <p className="text-xs text-muted-foreground">Added via form submission</p>
                              <p className="text-xs text-muted-foreground mt-1">1 week ago</p>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </TabsContent>
                </ScrollArea>
              </Tabs>

              <div className="p-4 border-t flex gap-2">
                <Button variant="outline" className="flex-1" onClick={closeDetailSheet}>
                  Close
                </Button>
                <Button variant="outline">
                  <Edit className="w-4 h-4 mr-2" />
                  Edit
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Create Contact Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Contact</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>First Name</Label>
                <Input
                  value={newContact.first_name}
                  onChange={(e) => setNewContact({ ...newContact, first_name: e.target.value })}
                  placeholder="John"
                />
              </div>
              <div className="space-y-2">
                <Label>Last Name</Label>
                <Input
                  value={newContact.last_name}
                  onChange={(e) => setNewContact({ ...newContact, last_name: e.target.value })}
                  placeholder="Doe"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Email</Label>
              <Input
                type="email"
                value={newContact.email}
                onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                placeholder="john@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input
                value={newContact.phone}
                onChange={(e) => setNewContact({ ...newContact, phone: e.target.value })}
                placeholder="+1 (555) 123-4567"
              />
            </div>
            <div className="space-y-2">
              <Label>Company</Label>
              <Input
                value={newContact.company_name}
                onChange={(e) => setNewContact({ ...newContact, company_name: e.target.value })}
                placeholder="Acme Inc."
              />
            </div>
            <div className="space-y-2">
              <Label>Lifecycle Stage</Label>
              <Select
                value={newContact.lifecycle_stage}
                onValueChange={(v) => setNewContact({ ...newContact, lifecycle_stage: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="lead">Lead</SelectItem>
                  <SelectItem value="subscriber">Subscriber</SelectItem>
                  <SelectItem value="opportunity">Opportunity</SelectItem>
                  <SelectItem value="customer">Customer</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>Cancel</Button>
            <Button onClick={handleCreateContact} disabled={creating}>
              {creating ? 'Creating...' : 'Create Contact'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ContactsPage;
