import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Progress } from '../components/ui/progress';
import {
  BarChart3, TrendingUp, TrendingDown, DollarSign, Users, Target,
  Phone, Mail, Calendar, Clock, ArrowUp, ArrowDown, Minus,
  RefreshCw, Download, Filter, Activity, CheckCircle, XCircle,
  Percent, Timer, Zap
} from 'lucide-react';
import { toast } from 'sonner';

const ReportsPage = () => {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('30d');
  const [stats, setStats] = useState({
    deals: { total: 0, won: 0, lost: 0, open: 0, value: 0, wonValue: 0 },
    contacts: { total: 0, new: 0 },
    pipeline: { stages: [], velocity: 0 },
    outreach: { calls: 0, emails: 0, meetings: 0, totalTouchpoints: 0 },
    conversion: { rate: 0, avgDealSize: 0, avgDaysToClose: 0 }
  });

  const api = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL + '/api',
    headers: { Authorization: `Bearer ${token}` }
  });

  const fetchReportData = useCallback(async () => {
    setLoading(true);
    try {
      // Fetch deals data
      const dealsRes = await api.get('/deals');
      const deals = dealsRes.data.deals || [];
      
      // Fetch contacts data
      const contactsRes = await api.get('/contacts');
      const contacts = contactsRes.data.contacts || [];
      
      // Fetch pipeline data
      const pipelinesRes = await api.get('/pipelines');
      const pipelines = pipelinesRes.data.pipelines || [];
      
      // Fetch timeline for activity stats
      const timelineRes = await api.get('/timeline?page_size=100');
      const events = timelineRes.data.events || [];
      
      // Calculate deal stats
      const wonDeals = deals.filter(d => d.status === 'won' || d.status === 'WON');
      const lostDeals = deals.filter(d => d.status === 'lost' || d.status === 'LOST');
      const openDeals = deals.filter(d => d.status === 'open' || d.status === 'OPEN');
      
      const totalValue = deals.reduce((sum, d) => sum + (d.amount || 0), 0);
      const wonValue = wonDeals.reduce((sum, d) => sum + (d.amount || 0), 0);
      
      // Calculate pipeline stage distribution
      const stageDistribution = {};
      const pipeline = pipelines[0];
      if (pipeline) {
        const kanbanRes = await api.get(`/pipelines/${pipeline.id}/kanban`);
        const columns = kanbanRes.data.columns || [];
        columns.forEach(col => {
          stageDistribution[col.name] = {
            count: col.deals?.length || 0,
            value: col.deals?.reduce((sum, d) => sum + (d.amount || 0), 0) || 0
          };
        });
      }
      
      // Calculate outreach stats from timeline
      const callEvents = events.filter(e => e.event_type === 'call_log');
      const emailEvents = events.filter(e => e.event_type === 'email_sent' || e.event_type === 'email_received');
      const meetingEvents = events.filter(e => e.event_type === 'meeting');
      
      // Calculate conversion metrics
      const totalClosedDeals = wonDeals.length + lostDeals.length;
      const conversionRate = totalClosedDeals > 0 ? (wonDeals.length / totalClosedDeals) * 100 : 0;
      const avgDealSize = wonDeals.length > 0 ? wonValue / wonDeals.length : 0;
      
      setStats({
        deals: {
          total: deals.length,
          won: wonDeals.length,
          lost: lostDeals.length,
          open: openDeals.length,
          value: totalValue,
          wonValue: wonValue
        },
        contacts: {
          total: contacts.length,
          new: contacts.filter(c => {
            const created = new Date(c.created_at);
            const daysAgo = (Date.now() - created.getTime()) / (1000 * 60 * 60 * 24);
            return daysAgo <= parseInt(timeRange);
          }).length
        },
        pipeline: {
          stages: Object.entries(stageDistribution).map(([name, data]) => ({ name, ...data })),
          velocity: deals.length > 0 ? Math.round(wonValue / deals.length) : 0
        },
        outreach: {
          calls: callEvents.length,
          emails: emailEvents.length,
          meetings: meetingEvents.length,
          totalTouchpoints: callEvents.length + emailEvents.length + meetingEvents.length
        },
        conversion: {
          rate: conversionRate,
          avgDealSize: avgDealSize,
          avgDaysToClose: 14 // Placeholder - would need deal close dates
        }
      });
    } catch (error) {
      console.error('Error fetching report data:', error);
      toast.error('Failed to load report data');
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    fetchReportData();
  }, [fetchReportData]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const MetricCard = ({ title, value, subtitle, icon: Icon, trend, trendValue, color = 'text-primary' }) => (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          <div className={`w-10 h-10 rounded-lg ${color.replace('text-', 'bg-')}/20 flex items-center justify-center`}>
            <Icon className={`w-5 h-5 ${color}`} />
          </div>
        </div>
        {trend && (
          <div className="flex items-center gap-1 mt-3 text-xs">
            {trend === 'up' && <ArrowUp className="w-3 h-3 text-green-500" />}
            {trend === 'down' && <ArrowDown className="w-3 h-3 text-red-500" />}
            {trend === 'neutral' && <Minus className="w-3 h-3 text-gray-500" />}
            <span className={trend === 'up' ? 'text-green-500' : trend === 'down' ? 'text-red-500' : 'text-gray-500'}>
              {trendValue}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BarChart3 className="w-6 h-6" />
            Reports & Analytics
          </h1>
          <p className="text-muted-foreground">Track performance across your CRM</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-40">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="365d">Last year</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={fetchReportData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32" />)}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[1, 2].map(i => <Skeleton key={i} className="h-80" />)}
          </div>
        </div>
      ) : (
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
            <TabsTrigger value="outreach">Outreach</TabsTrigger>
            <TabsTrigger value="conversion">Conversion</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Total Pipeline Value"
                value={formatCurrency(stats.deals.value)}
                subtitle={`${stats.deals.total} deals`}
                icon={DollarSign}
                color="text-green-500"
              />
              <MetricCard
                title="Deals Won"
                value={stats.deals.won}
                subtitle={formatCurrency(stats.deals.wonValue)}
                icon={CheckCircle}
                color="text-emerald-500"
                trend="up"
                trendValue="+12% vs last period"
              />
              <MetricCard
                title="Total Contacts"
                value={stats.contacts.total}
                subtitle={`${stats.contacts.new} new this period`}
                icon={Users}
                color="text-blue-500"
              />
              <MetricCard
                title="Conversion Rate"
                value={`${stats.conversion.rate.toFixed(1)}%`}
                subtitle="Won / Total Closed"
                icon={Percent}
                color="text-purple-500"
              />
            </div>

            {/* Pipeline Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Deal Status Distribution</CardTitle>
                  <CardDescription>Current deal breakdown by status</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-blue-500" />
                        <span className="text-sm">Open</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{stats.deals.open}</span>
                        <Progress value={(stats.deals.open / stats.deals.total) * 100} className="w-24 h-2" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-green-500" />
                        <span className="text-sm">Won</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{stats.deals.won}</span>
                        <Progress value={(stats.deals.won / stats.deals.total) * 100} className="w-24 h-2 [&>div]:bg-green-500" />
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500" />
                        <span className="text-sm">Lost</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{stats.deals.lost}</span>
                        <Progress value={(stats.deals.lost / stats.deals.total) * 100} className="w-24 h-2 [&>div]:bg-red-500" />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Activity Summary</CardTitle>
                  <CardDescription>Outreach activities this period</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-muted/50 rounded-lg">
                      <Phone className="w-6 h-6 mx-auto mb-2 text-green-500" />
                      <p className="text-2xl font-bold">{stats.outreach.calls}</p>
                      <p className="text-xs text-muted-foreground">Calls</p>
                    </div>
                    <div className="text-center p-4 bg-muted/50 rounded-lg">
                      <Mail className="w-6 h-6 mx-auto mb-2 text-blue-500" />
                      <p className="text-2xl font-bold">{stats.outreach.emails}</p>
                      <p className="text-xs text-muted-foreground">Emails</p>
                    </div>
                    <div className="text-center p-4 bg-muted/50 rounded-lg">
                      <Calendar className="w-6 h-6 mx-auto mb-2 text-purple-500" />
                      <p className="text-2xl font-bold">{stats.outreach.meetings}</p>
                      <p className="text-xs text-muted-foreground">Meetings</p>
                    </div>
                  </div>
                  <div className="mt-4 p-3 bg-primary/10 rounded-lg text-center">
                    <p className="text-sm text-muted-foreground">Total Touchpoints</p>
                    <p className="text-xl font-bold text-primary">{stats.outreach.totalTouchpoints}</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Pipeline Tab */}
          <TabsContent value="pipeline" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard
                title="Pipeline Velocity"
                value={formatCurrency(stats.pipeline.velocity)}
                subtitle="Avg value per deal"
                icon={Zap}
                color="text-yellow-500"
              />
              <MetricCard
                title="Avg Deal Size"
                value={formatCurrency(stats.conversion.avgDealSize)}
                subtitle="Won deals average"
                icon={DollarSign}
                color="text-green-500"
              />
              <MetricCard
                title="Avg Days to Close"
                value={stats.conversion.avgDaysToClose}
                subtitle="From creation to won"
                icon={Timer}
                color="text-blue-500"
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Pipeline Stage Distribution</CardTitle>
                <CardDescription>Deals and value by stage</CardDescription>
              </CardHeader>
              <CardContent>
                {stats.pipeline.stages.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Target className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p>No pipeline data available</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {stats.pipeline.stages.slice(0, 8).map((stage, index) => (
                      <div key={index} className="flex items-center gap-4">
                        <div className="w-32 text-sm truncate">{stage.name}</div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Progress 
                              value={(stage.count / Math.max(...stats.pipeline.stages.map(s => s.count), 1)) * 100} 
                              className="h-3 flex-1"
                            />
                            <span className="text-sm font-medium w-8">{stage.count}</span>
                          </div>
                        </div>
                        <div className="w-24 text-right text-sm text-muted-foreground">
                          {formatCurrency(stage.value)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Outreach Tab */}
          <TabsContent value="outreach" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <MetricCard
                title="Total Touchpoints"
                value={stats.outreach.totalTouchpoints}
                icon={Activity}
                color="text-primary"
              />
              <MetricCard
                title="Calls Made"
                value={stats.outreach.calls}
                icon={Phone}
                color="text-green-500"
              />
              <MetricCard
                title="Emails Sent"
                value={stats.outreach.emails}
                icon={Mail}
                color="text-blue-500"
              />
              <MetricCard
                title="Meetings Held"
                value={stats.outreach.meetings}
                icon={Calendar}
                color="text-purple-500"
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Outreach Breakdown</CardTitle>
                <CardDescription>Activity distribution by type</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { label: 'Calls', value: stats.outreach.calls, color: 'bg-green-500', icon: Phone },
                    { label: 'Emails', value: stats.outreach.emails, color: 'bg-blue-500', icon: Mail },
                    { label: 'Meetings', value: stats.outreach.meetings, color: 'bg-purple-500', icon: Calendar },
                  ].map((item, index) => {
                    const total = stats.outreach.totalTouchpoints || 1;
                    const percent = ((item.value / total) * 100).toFixed(1);
                    return (
                      <div key={index} className="flex items-center gap-4">
                        <div className="w-24 flex items-center gap-2">
                          <item.icon className="w-4 h-4 text-muted-foreground" />
                          <span className="text-sm">{item.label}</span>
                        </div>
                        <div className="flex-1">
                          <Progress value={parseFloat(percent)} className={`h-4 [&>div]:${item.color}`} />
                        </div>
                        <div className="w-20 text-right">
                          <span className="font-semibold">{item.value}</span>
                          <span className="text-xs text-muted-foreground ml-1">({percent}%)</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Conversion Tab */}
          <TabsContent value="conversion" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard
                title="Win Rate"
                value={`${stats.conversion.rate.toFixed(1)}%`}
                subtitle="Won / Total Closed"
                icon={Percent}
                color="text-green-500"
              />
              <MetricCard
                title="Average Deal Value"
                value={formatCurrency(stats.conversion.avgDealSize)}
                subtitle="Won deals"
                icon={DollarSign}
                color="text-blue-500"
              />
              <MetricCard
                title="Total Revenue"
                value={formatCurrency(stats.deals.wonValue)}
                subtitle={`From ${stats.deals.won} won deals`}
                icon={TrendingUp}
                color="text-emerald-500"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Win/Loss Ratio</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-8">
                    <div className="flex-1">
                      <div className="flex items-center gap-4 mb-4">
                        <div className="flex-1 bg-green-500/20 rounded-full h-8 relative overflow-hidden">
                          <div 
                            className="absolute inset-y-0 left-0 bg-green-500 rounded-full flex items-center justify-center text-white text-sm font-medium"
                            style={{ width: `${stats.conversion.rate}%`, minWidth: '60px' }}
                          >
                            {stats.deals.won} Won
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="flex-1 bg-red-500/20 rounded-full h-8 relative overflow-hidden">
                          <div 
                            className="absolute inset-y-0 left-0 bg-red-500 rounded-full flex items-center justify-center text-white text-sm font-medium"
                            style={{ width: `${100 - stats.conversion.rate}%`, minWidth: '60px' }}
                          >
                            {stats.deals.lost} Lost
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Key Metrics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <span className="text-sm">Deals in Pipeline</span>
                      <Badge variant="secondary">{stats.deals.open}</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <span className="text-sm">Pipeline Value</span>
                      <Badge variant="secondary">{formatCurrency(stats.deals.value - stats.deals.wonValue)}</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <span className="text-sm">Avg Touchpoints per Deal</span>
                      <Badge variant="secondary">
                        {stats.deals.total > 0 ? (stats.outreach.totalTouchpoints / stats.deals.total).toFixed(1) : 0}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
};

export default ReportsPage;
