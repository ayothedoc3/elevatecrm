import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Progress } from '../components/ui/progress';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  BarChart3, TrendingUp, TrendingDown, DollarSign, Users, Target,
  Phone, Mail, Calendar, Clock, ArrowUp, ArrowDown, Minus,
  RefreshCw, Download, Filter, Activity, CheckCircle, XCircle,
  Percent, Timer, Zap
} from 'lucide-react';
import { toast } from 'sonner';

const ReportsPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('30d');
  const [stats, setStats] = useState({
    deals: { total: 0, won: 0, lost: 0, open: 0, value: 0, wonValue: 0 },
    contacts: { total: 0, new: 0 },
    pipeline: { stages: [], velocity: 0 },
    outreach: { calls: 0, emails: 0, meetings: 0, totalTouchpoints: 0 },
    conversion: { rate: 0, avgDealSize: 0, avgDaysToClose: 0 }
  });
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecast, setForecast] = useState(null);
  const [forecastMotion, setForecastMotion] = useState('all');
  const [forecastPartnerId, setForecastPartnerId] = useState('all');
  const [forecastProductId, setForecastProductId] = useState('all');
  const [forecastTier, setForecastTier] = useState('all');
  const [forecastOwnerId, setForecastOwnerId] = useState('all');
  const [forecastIncludeClosed, setForecastIncludeClosed] = useState(false);
  const [forecastStaleDays, setForecastStaleDays] = useState(3);

  const [partners, setPartners] = useState([]);
  const [products, setProducts] = useState([]);
  const [users, setUsers] = useState([]);

  const fetchReportData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/kpis/summary?time_range=${encodeURIComponent(timeRange)}`);
      const data = res.data || {};
      setStats({
        deals: data.deals || { total: 0, won: 0, lost: 0, open: 0, value: 0, wonValue: 0 },
        contacts: data.contacts || { total: 0, new: 0 },
        pipeline: data.pipeline || { stages: [], velocity: 0 },
        outreach: data.outreach || { calls: 0, emails: 0, meetings: 0, totalTouchpoints: 0 },
        conversion: data.conversion || { rate: 0, avgDealSize: 0, avgDaysToClose: 0 },
      });
    } catch (error) {
      console.error('Error fetching report data:', error);
      toast.error('Failed to load report data');
    } finally {
      setLoading(false);
    }
  }, [api, timeRange]);

  const fetchForecastRefs = useCallback(async () => {
    try {
      const [partnersRes, usersRes] = await Promise.all([
        api.get('/partners'),
        api.get('/users')
      ]);
      setPartners(partnersRes.data.partners || []);
      setUsers(usersRes.data.users || []);
    } catch (error) {
      console.error('Error loading forecast reference data:', error);
    }
  }, [api]);

  const fetchProductsForPartner = useCallback(async (partnerId) => {
    if (!partnerId || partnerId === 'all') {
      setProducts([]);
      return;
    }
    try {
      const res = await api.get(`/products?partner_id=${partnerId}`);
      setProducts(res.data.products || []);
    } catch (error) {
      console.error('Error loading products:', error);
      setProducts([]);
    }
  }, [api]);

  const fetchForecast = useCallback(async () => {
    setForecastLoading(true);
    try {
      const params = new URLSearchParams();
      if (forecastMotion !== 'all') params.append('sales_motion_type', forecastMotion);
      if (forecastPartnerId !== 'all') params.append('partner_id', forecastPartnerId);
      if (forecastProductId !== 'all') params.append('product_id', forecastProductId);
      if (forecastTier !== 'all') params.append('lead_tier', forecastTier);
      if (forecastOwnerId !== 'all') params.append('owner_id', forecastOwnerId);
      if (forecastIncludeClosed) params.append('include_closed', 'true');
      params.append('stale_days', String(forecastStaleDays || 3));

      const res = await api.get(`/forecast/summary?${params.toString()}`);
      setForecast(res.data);
    } catch (error) {
      console.error('Error fetching forecast:', error);
      toast.error('Failed to load forecast');
      setForecast(null);
    } finally {
      setForecastLoading(false);
    }
  }, [api, forecastMotion, forecastPartnerId, forecastProductId, forecastTier, forecastOwnerId, forecastIncludeClosed, forecastStaleDays]);

  useEffect(() => {
    fetchReportData();
  }, [fetchReportData]);

  useEffect(() => {
    fetchForecastRefs();
  }, [fetchForecastRefs]);

  useEffect(() => {
    if (forecastMotion !== 'partner_sales') {
      setForecastPartnerId('all');
      setForecastProductId('all');
      setProducts([]);
      return;
    }
  }, [forecastMotion]);

  useEffect(() => {
    if (forecastPartnerId === 'all') {
      setProducts([]);
      setForecastProductId('all');
      return;
    }
    fetchProductsForPartner(forecastPartnerId);
    setForecastProductId('all');
  }, [forecastPartnerId, fetchProductsForPartner]);

  useEffect(() => {
    fetchForecast();
  }, [fetchForecast]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getTierBadge = (tier) => {
    const t = (tier || '').toString().trim().toUpperCase();
    const styles = {
      A: 'bg-green-500/20 text-green-400 border-green-500/30',
      B: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      C: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      D: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
    };
    if (!styles[t]) return <Badge variant="outline">-</Badge>;
    return <Badge className={styles[t]}>{t}</Badge>;
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
            <TabsTrigger value="forecast">Forecast</TabsTrigger>
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

          {/* Forecast Tab */}
          <TabsContent value="forecast" className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      <TrendingUp className="w-4 h-4" />
                      Weighted Forecast
                    </CardTitle>
                    <CardDescription>Tier-weighted pipeline and SLA risk indicators.</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={fetchForecast} disabled={forecastLoading}>
                    <RefreshCw className={`w-4 h-4 mr-2 ${forecastLoading ? 'animate-spin' : ''}`} />
                    Refresh
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label>Sales Motion</Label>
                    <Select value={forecastMotion} onValueChange={setForecastMotion}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="partnership_sales">Partnership Sales</SelectItem>
                        <SelectItem value="partner_sales">Partner Sales</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Partner</Label>
                    <Select
                      value={forecastPartnerId}
                      onValueChange={setForecastPartnerId}
                      disabled={forecastMotion !== 'partner_sales'}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        {partners.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Product</Label>
                    <Select
                      value={forecastProductId}
                      onValueChange={setForecastProductId}
                      disabled={forecastMotion !== 'partner_sales' || forecastPartnerId === 'all'}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        {products.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Lead Tier</Label>
                    <Select value={forecastTier} onValueChange={setForecastTier}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="A">A</SelectItem>
                        <SelectItem value="B">B</SelectItem>
                        <SelectItem value="C">C</SelectItem>
                        <SelectItem value="D">D</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Owner</Label>
                    <Select value={forecastOwnerId} onValueChange={setForecastOwnerId}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        {users.map(u => (
                          <SelectItem key={u.id} value={u.id}>{u.full_name || u.email}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Include Closed</Label>
                    <Select
                      value={forecastIncludeClosed ? 'true' : 'false'}
                      onValueChange={(v) => setForecastIncludeClosed(v === 'true')}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="false">Open Only</SelectItem>
                        <SelectItem value="true">Include Closed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Stale Days</Label>
                    <Input
                      type="number"
                      min={1}
                      max={90}
                      value={forecastStaleDays}
                      onChange={(e) => {
                        const n = Math.max(1, Math.min(90, Number(e.target.value) || 1));
                        setForecastStaleDays(n);
                      }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {forecastLoading && !forecast ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3, 4, 5, 6].map(i => <Skeleton key={i} className="h-32" />)}
              </div>
            ) : forecast ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <MetricCard
                    title="Pipeline Value"
                    value={formatCurrency(forecast.totals?.pipeline_value || 0)}
                    subtitle={`${forecast.totals?.deal_count || 0} deals`}
                    icon={DollarSign}
                    color="text-green-500"
                  />
                  <MetricCard
                    title="Weighted Forecast"
                    value={formatCurrency(forecast.totals?.weighted_value || 0)}
                    subtitle="Tier probability applied"
                    icon={TrendingUp}
                    color="text-primary"
                  />
                  <MetricCard
                    title="Overdue Next Steps"
                    value={forecast.totals?.overdue_next_steps || 0}
                    subtitle="Next step due in past"
                    icon={Clock}
                    color="text-red-500"
                  />
                  <MetricCard
                    title="Missing Next Steps"
                    value={forecast.totals?.missing_next_steps || 0}
                    subtitle="No next step scheduled"
                    icon={XCircle}
                    color="text-amber-500"
                  />
                  <MetricCard
                    title="Stale Deals"
                    value={forecast.totals?.stale_no_activity || 0}
                    subtitle={`No activity ≥ ${forecast.filters?.stale_days || forecastStaleDays} days`}
                    icon={Activity}
                    color="text-purple-500"
                  />
                  <MetricCard
                    title="Deals Count"
                    value={forecast.totals?.deal_count || 0}
                    subtitle="In current filter"
                    icon={Target}
                    color="text-blue-500"
                  />
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Tier Breakdown</CardTitle>
                    <CardDescription>Pipeline and weighted value by tier.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-5 gap-2 text-xs text-muted-foreground mb-2">
                      <div>Tier</div>
                      <div>Probability</div>
                      <div className="text-right">Deals</div>
                      <div className="text-right">Pipeline</div>
                      <div className="text-right">Weighted</div>
                    </div>
                    <div className="space-y-2">
                      {Object.entries(forecast.by_tier || {}).map(([tier, row]) => (
                        <div key={tier} className="grid grid-cols-5 gap-2 items-center p-3 rounded-lg border">
                          <div className="flex items-center gap-2">
                            {getTierBadge(tier)}
                          </div>
                          <div className="text-sm">{Math.round((row.probability || 0) * 100)}%</div>
                          <div className="text-sm text-right">{row.deal_count || 0}</div>
                          <div className="text-sm text-right">{formatCurrency(row.pipeline_value || 0)}</div>
                          <div className="text-sm font-medium text-right">{formatCurrency(row.weighted_value || 0)}</div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardContent className="py-10 text-center text-muted-foreground">
                  <TrendingUp className="w-10 h-10 mx-auto mb-2 opacity-50" />
                  <p>No forecast data yet</p>
                </CardContent>
              </Card>
            )}
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
