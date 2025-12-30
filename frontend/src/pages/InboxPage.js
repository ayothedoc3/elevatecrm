import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { ScrollArea } from '../components/ui/scroll-area';
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
import { Label } from '../components/ui/label';
import {
  Mail, MessageSquare, Phone, User, Search, Send, RefreshCw,
  CheckCircle2, Clock, AlertCircle, MoreHorizontal, Plus
} from 'lucide-react';

const InboxPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [conversations, setConversations] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [showComposeModal, setShowComposeModal] = useState(false);
  const [sending, setSending] = useState(false);
  const [newMessage, setNewMessage] = useState({
    contact_id: '',
    channel: 'email',
    to_address: '',
    subject: '',
    body: ''
  });
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchData();
  }, [filter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [convRes, statsRes, contactsRes] = await Promise.all([
        api.get(`/inbox${filter !== 'all' ? `?channel=${filter}` : ''}`),
        api.get('/inbox/stats'),
        api.get('/contacts?page_size=100')
      ]);
      setConversations(convRes.data.conversations);
      setStats(statsRes.data);
      setContacts(contactsRes.data.contacts);
    } catch (error) {
      console.error('Error fetching inbox data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchConversation = async (id) => {
    try {
      const response = await api.get(`/inbox/${id}`);
      setSelectedConversation(response.data);
    } catch (error) {
      console.error('Error fetching conversation:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.contact_id || !newMessage.to_address || !newMessage.body) return;
    
    setSending(true);
    try {
      await api.post('/inbox/send', newMessage);
      setShowComposeModal(false);
      setNewMessage({ contact_id: '', channel: 'email', to_address: '', subject: '', body: '' });
      fetchData();
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setSending(false);
    }
  };

  const handleContactSelect = (contactId) => {
    const contact = contacts.find(c => c.id === contactId);
    if (contact) {
      setNewMessage({
        ...newMessage,
        contact_id: contactId,
        to_address: newMessage.channel === 'email' ? contact.email : contact.phone
      });
    }
  };

  const getChannelIcon = (channel) => {
    return channel === 'email' ? <Mail className="w-4 h-4" /> : <MessageSquare className="w-4 h-4" />;
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'sent': return <CheckCircle2 className="w-3 h-3 text-green-500" />;
      case 'delivered': return <CheckCircle2 className="w-3 h-3 text-blue-500" />;
      case 'pending': return <Clock className="w-3 h-3 text-amber-500" />;
      case 'failed': return <AlertCircle className="w-3 h-3 text-red-500" />;
      default: return null;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Inbox</h1>
          <p className="text-muted-foreground">
            {stats ? `${stats.total_conversations} conversations, ${stats.unread_conversations} unread` : 'Loading...'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowComposeModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Compose
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-4">
          <Card className="cursor-pointer hover:border-primary" onClick={() => setFilter('all')}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">All</p>
                  <p className="text-2xl font-bold">{stats.total_conversations}</p>
                </div>
                <MessageSquare className="w-6 h-6 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:border-primary" onClick={() => setFilter('email')}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Email</p>
                  <p className="text-2xl font-bold">{stats.email_count}</p>
                </div>
                <Mail className="w-6 h-6 text-blue-500" />
              </div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:border-primary" onClick={() => setFilter('sms')}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">SMS</p>
                  <p className="text-2xl font-bold">{stats.sms_count}</p>
                </div>
                <Phone className="w-6 h-6 text-green-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Unread</p>
                  <p className="text-2xl font-bold">{stats.unread_conversations}</p>
                </div>
                <Badge variant="destructive">{stats.unread_conversations}</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Conversation List */}
        <Card className="w-1/3">
          <CardHeader className="py-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input placeholder="Search conversations..." className="pl-10" />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[calc(100vh-420px)]">
              {loading ? (
                [...Array(5)].map((_, i) => (
                  <div key={i} className="p-4 border-b">
                    <Skeleton className="h-4 w-32 mb-2" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                ))
              ) : conversations.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No conversations yet</p>
                  <p className="text-sm">Start by sending a message</p>
                </div>
              ) : (
                conversations.map(conv => (
                  <div
                    key={conv.id}
                    className={`p-4 border-b cursor-pointer hover:bg-muted/50 transition-colors ${
                      selectedConversation?.id === conv.id ? 'bg-muted' : ''
                    } ${!conv.is_read ? 'bg-primary/5' : ''}`}
                    onClick={() => fetchConversation(conv.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`p-2 rounded-full ${
                          conv.channel === 'email' ? 'bg-blue-500/10' : 'bg-green-500/10'
                        }`}>
                          {getChannelIcon(conv.channel)}
                        </div>
                        <div>
                          <p className={`font-medium ${!conv.is_read ? 'font-bold' : ''}`}>
                            {conv.contact_name || 'Unknown'}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {conv.channel === 'email' ? conv.contact_email : conv.contact_phone}
                          </p>
                        </div>
                      </div>
                      {conv.unread_count > 0 && (
                        <Badge variant="default" className="ml-2">{conv.unread_count}</Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-2 truncate">
                      {conv.last_message_preview || 'No messages'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {conv.last_message_at ? new Date(conv.last_message_at).toLocaleString() : ''}
                    </p>
                  </div>
                ))
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Conversation Detail */}
        <Card className="flex-1 flex flex-col">
          {selectedConversation ? (
            <>
              <CardHeader className="border-b py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <User className="w-5 h-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{selectedConversation.contact_name}</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        {selectedConversation.channel === 'email' 
                          ? selectedConversation.contact_email 
                          : selectedConversation.contact_phone}
                      </p>
                    </div>
                  </div>
                  <Badge variant="outline">
                    {getChannelIcon(selectedConversation.channel)}
                    <span className="ml-1 capitalize">{selectedConversation.channel}</span>
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="flex-1 p-4 overflow-hidden">
                <ScrollArea className="h-full">
                  <div className="space-y-4">
                    {selectedConversation.messages?.map(msg => (
                      <div
                        key={msg.id}
                        className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-[70%] p-3 rounded-lg ${
                          msg.direction === 'outbound'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted'
                        }`}>
                          {msg.subject && (
                            <p className="font-medium mb-1">{msg.subject}</p>
                          )}
                          <p className="whitespace-pre-wrap">{msg.body}</p>
                          <div className="flex items-center justify-end gap-2 mt-2 text-xs opacity-70">
                            {getStatusIcon(msg.status)}
                            <span>{new Date(msg.created_at).toLocaleTimeString()}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
              <div className="p-4 border-t">
                <div className="flex gap-2">
                  <Textarea 
                    placeholder="Type your message..."
                    className="flex-1 resize-none"
                    rows={2}
                  />
                  <Button>
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          ) : (
            <CardContent className="flex-1 flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <Mail className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg">Select a conversation</p>
                <p className="text-sm">Or compose a new message</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>

      {/* Compose Modal */}
      <Dialog open={showComposeModal} onOpenChange={setShowComposeModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Compose Message</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Channel</Label>
              <Select
                value={newMessage.channel}
                onValueChange={(value) => setNewMessage({ ...newMessage, channel: value, to_address: '' })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="email"><Mail className="w-4 h-4 inline mr-2" />Email</SelectItem>
                  <SelectItem value="sms"><MessageSquare className="w-4 h-4 inline mr-2" />SMS</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Contact</Label>
              <Select
                value={newMessage.contact_id}
                onValueChange={handleContactSelect}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select contact..." />
                </SelectTrigger>
                <SelectContent>
                  {contacts.map(c => (
                    <SelectItem key={c.id} value={c.id}>
                      {c.full_name} ({newMessage.channel === 'email' ? c.email : c.phone})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>{newMessage.channel === 'email' ? 'Email Address' : 'Phone Number'}</Label>
              <Input
                value={newMessage.to_address}
                onChange={(e) => setNewMessage({ ...newMessage, to_address: e.target.value })}
                placeholder={newMessage.channel === 'email' ? 'email@example.com' : '+1-555-0100'}
              />
            </div>
            
            {newMessage.channel === 'email' && (
              <div className="space-y-2">
                <Label>Subject</Label>
                <Input
                  value={newMessage.subject}
                  onChange={(e) => setNewMessage({ ...newMessage, subject: e.target.value })}
                  placeholder="Message subject..."
                />
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Message</Label>
              <Textarea
                value={newMessage.body}
                onChange={(e) => setNewMessage({ ...newMessage, body: e.target.value })}
                placeholder="Type your message..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowComposeModal(false)}>Cancel</Button>
            <Button onClick={handleSendMessage} disabled={sending}>
              {sending ? 'Sending...' : 'Send Message'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default InboxPage;
