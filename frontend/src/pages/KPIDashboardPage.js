/**
 * KPI & Forecasting Dashboard
 * 
 * Displays sales KPIs, forecasting metrics, and pipeline health.
 * Per Elev8 PRD Sections 6.4 (Forecasting) and 10 (KPIs & Reporting).
 */

import React, { useState, useEffect } from 'react';
import {
  TrendingUp, DollarSign, Target, Users, BarChart3, 
  PieChart, Activity, AlertTriangle, CheckCircle2, 
  ArrowUp, ArrowDown, RefreshCw, Loader2, Filter,
  Calendar, Briefcase, Award, AlertCircle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { useToast } from '../hooks/use-toast';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Tier colors
const tierColors = {
  A: 'bg-green-500',
  B: 'bg-blue-500',
  C: 'bg-yellow-500',
  D: 'bg-gray-400'
};

const riskColors = {
  low: 'text-green-600 bg-green-50',
  medium: 'text-yellow-600 bg-yellow-50',
  high: 'text-orange-600 bg-orange-50',
  critical: 'text-red-600 bg-red-50'
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
};

const KPIDashboardPage = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('month');
  
  // Data state
  const [forecast, setForecast] = useState(null);
  const [kpis, setKpis] = useState(null);
  const [pipelineHealth, setPipelineHealth] = useState(null);
  const [salesMotionKpis, setSalesMotionKpis] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [forecastRes, kpisRes, healthRes, motionRes, leaderRes] = await Promise.all([
        fetch(`${API_URL}/api/elev8/forecasting/summary?period=${period}`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/kpis/overview?period=${period}`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/ai-assistant/pipeline/health-summary?pipeline_type=sales`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/kpis/sales-motion?period=${period}`, { headers: getAuthHeaders() }),
        fetch(`${API_URL}/api/elev8/kpis/leaderboard?period=${period}`, { headers: getAuthHeaders() })
      ]);
      
      if (forecastRes.ok) setForecast(await forecastRes.json());
      if (kpisRes.ok) setKpis(await kpisRes.json());
      if (healthRes.ok) setPipelineHealth(await healthRes.json());
      if (motionRes.ok) setSalesMotionKpis(await motionRes.json());
      if (leaderRes.ok) setLeaderboard(await leaderRes.json());
      
    } catch (error) {
      console.error('Error loading dashboard:', error);
      toast({ title: "Error", description: "Failed to load dashboard data", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [period]);

  const getProgressColor = (value, target) => {
    const pct = (value / target) * 100;
    if (pct >= 100) return 'bg-green-500';
    if (pct >= 75) return 'bg-blue-500';
    if (pct >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">KPIs & Forecasting</h1>
          <p className="text-muted-foreground">Pipeline metrics and sales performance</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[150px]">
              <Calendar className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
              <SelectItem value="quarter">This Quarter</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={loadDashboardData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Forecast Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pipeline Value</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(forecast?.pipeline_summary?.total_pipeline_value || 0)}
                </p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <DollarSign className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {forecast?.pipeline_summary?.total_deals || 0} open deals
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Weighted Forecast</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(forecast?.pipeline_summary?.weighted_forecast || 0)}
                </p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Based on tier probabilities
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Closed Won</p>
                <p className="text-2xl font-bold">
                  {formatCurrency(forecast?.closed_this_period?.won?.value || 0)}
                </p>
              </div>
              <div className="p-3 bg-emerald-100 rounded-full">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {forecast?.closed_this_period?.won?.count || 0} deals this {period}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Win Rate</p>
                <p className="text-2xl font-bold">
                  {forecast?.closed_this_period?.win_rate || 0}%
                </p>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <Target className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Target: 25%
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="forecast" className="w-full">
        <TabsList>
          <TabsTrigger value="forecast">
            <BarChart3 className="w-4 h-4 mr-2" />
            Forecast
          </TabsTrigger>
          <TabsTrigger value="activity">
            <Activity className="w-4 h-4 mr-2" />
            Activity KPIs
          </TabsTrigger>
          <TabsTrigger value="health">
            <PieChart className="w-4 h-4 mr-2" />
            Pipeline Health
          </TabsTrigger>
          <TabsTrigger value="leaderboard">
            <Award className="w-4 h-4 mr-2" />
            Leaderboard
          </TabsTrigger>
        </TabsList>

        {/* Forecast Tab */}
        <TabsContent value="forecast" className="mt-4 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Forecast by Tier */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Forecast by Tier</CardTitle>
                <CardDescription>Weighted pipeline by lead tier</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {['A', 'B', 'C', 'D'].map(tier => {
                  const tierData = forecast?.forecast_by_tier?.[tier] || {};
                  return (
                    <div key={tier} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge className={`${tierColors[tier]} text-white w-6 h-6 flex items-center justify-center`}>
                            {tier}
                          </Badge>
                          <span className="text-sm">
                            {tierData.count || 0} deals • {Math.round((tierData.probability || 0) * 100)}% prob
                          </span>
                        </div>
                        <span className="font-semibold">{formatCurrency(tierData.weighted_value || 0)}</span>
                      </div>
                      <div className="flex gap-2 text-xs text-muted-foreground">
                        <span>Total: {formatCurrency(tierData.total_value || 0)}</span>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            {/* Forecast Confidence */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Forecast Confidence</CardTitle>
                <CardDescription>Breakdown by confidence level</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-green-600 font-medium">High Confidence (Tier A)</span>
                      <span className="font-semibold">{formatCurrency(forecast?.forecast_confidence?.high || 0)}</span>
                    </div>
                    <Progress value={70} className="h-2 bg-green-100" />
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-blue-600 font-medium">Medium Confidence (Tier B)</span>
                      <span className="font-semibold">{formatCurrency(forecast?.forecast_confidence?.medium || 0)}</span>
                    </div>
                    <Progress value={50} className="h-2 bg-blue-100" />
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-yellow-600 font-medium">Low Confidence (Tier C)</span>
                      <span className="font-semibold">{formatCurrency(forecast?.forecast_confidence?.low || 0)}</span>
                    </div>
                    <Progress value={30} className="h-2 bg-yellow-100" />
                  </div>
                  <div>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-gray-500 font-medium">Excluded (Tier D)</span>
                      <span className="font-semibold text-muted-foreground">{formatCurrency(forecast?.forecast_confidence?.excluded || 0)}</span>
                    </div>
                    <Progress value={10} className="h-2 bg-gray-200" />
                  </div>
                </div>

                <div className="pt-4 border-t space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm">Best Case</span>
                    <span className="font-medium">{formatCurrency(forecast?.pipeline_summary?.best_case || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Commit Forecast</span>
                    <span className="font-medium text-green-600">{formatCurrency(forecast?.pipeline_summary?.commit_forecast || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm">Worst Case</span>
                    <span className="font-medium text-muted-foreground">{formatCurrency(forecast?.pipeline_summary?.worst_case || 0)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Sales Motion Comparison */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">Sales Motion Performance</CardTitle>
                <CardDescription>Partnership Sales vs Partner Sales</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <Briefcase className="w-5 h-5 text-blue-600" />
                      <span className="font-medium">Partnership Sales</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Leads</p>
                        <p className="text-lg font-semibold">{salesMotionKpis?.partnership_sales?.leads_created || 0}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Deals</p>
                        <p className="text-lg font-semibold">{salesMotionKpis?.partnership_sales?.deals_count || 0}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Pipeline</p>
                        <p className="text-lg font-semibold">{formatCurrency(salesMotionKpis?.partnership_sales?.pipeline_value || 0)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Weighted</p>
                        <p className="text-lg font-semibold">{formatCurrency(salesMotionKpis?.partnership_sales?.weighted_forecast || 0)}</p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 bg-purple-50 rounded-lg">
                    <div className="flex items-center gap-2 mb-3">
                      <Users className="w-5 h-5 text-purple-600" />
                      <span className="font-medium">Partner Sales</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Leads</p>
                        <p className="text-lg font-semibold">{salesMotionKpis?.partner_sales?.leads_created || 0}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Deals</p>
                        <p className="text-lg font-semibold">{salesMotionKpis?.partner_sales?.deals_count || 0}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Pipeline</p>
                        <p className="text-lg font-semibold">{formatCurrency(salesMotionKpis?.partner_sales?.pipeline_value || 0)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Weighted</p>
                        <p className="text-lg font-semibold">{formatCurrency(salesMotionKpis?.partner_sales?.weighted_forecast || 0)}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Activity KPIs Tab */}
        <TabsContent value="activity" className="mt-4 space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {/* Lead Generation */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Users className="w-5 h-5" />
                  Lead Generation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">Leads Created</span>
                    <span className="font-semibold">{kpis?.activity_kpis?.leads_created || 0}</span>
                  </div>
                  <Progress 
                    value={((kpis?.activity_kpis?.leads_created || 0) / (kpis?.targets?.leads_target || 50)) * 100} 
                    className="h-2" 
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Target: {kpis?.targets?.leads_target || 50}
                  </p>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">Leads Qualified</span>
                    <span className="font-semibold">{kpis?.activity_kpis?.leads_qualified || 0}</span>
                  </div>
                  <Progress 
                    value={((kpis?.activity_kpis?.leads_qualified || 0) / (kpis?.targets?.qualification_target || 30)) * 100} 
                    className="h-2" 
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Target: {kpis?.targets?.qualification_target || 30}
                  </p>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex justify-between">
                    <span className="text-sm">Qualification Rate</span>
                    <Badge variant={kpis?.activity_kpis?.qualification_rate > 20 ? "success" : "secondary"}>
                      {kpis?.activity_kpis?.qualification_rate || 0}%
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Deal Performance */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Deal Performance
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <p className="text-2xl font-bold text-green-600">{kpis?.pipeline_kpis?.deals_won || 0}</p>
                    <p className="text-xs text-muted-foreground">Won</p>
                  </div>
                  <div className="text-center p-3 bg-red-50 rounded-lg">
                    <p className="text-2xl font-bold text-red-600">{kpis?.pipeline_kpis?.deals_lost || 0}</p>
                    <p className="text-xs text-muted-foreground">Lost</p>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">Win Rate</span>
                    <span className="font-semibold">{kpis?.pipeline_kpis?.win_rate || 0}%</span>
                  </div>
                  <Progress 
                    value={(kpis?.pipeline_kpis?.win_rate || 0) / (kpis?.targets?.win_rate_target || 25) * 100} 
                    className="h-2" 
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Target: {kpis?.targets?.win_rate_target || 25}%
                  </p>
                </div>
                <div className="pt-2 border-t">
                  <div className="flex justify-between">
                    <span className="text-sm">Avg Deal Size</span>
                    <span className="font-semibold">{formatCurrency(kpis?.pipeline_kpis?.avg_deal_size || 0)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quality Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Quality Metrics
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">SPICED Completion</span>
                    <span className="font-semibold">{kpis?.quality_kpis?.spiced_completion_rate || 0}%</span>
                  </div>
                  <Progress 
                    value={(kpis?.quality_kpis?.spiced_completion_rate || 0)} 
                    className="h-2" 
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Target: {kpis?.targets?.spiced_target || 80}%
                  </p>
                </div>
                <div className="pt-2 border-t">
                  <p className="text-sm font-medium mb-2">Tier Distribution</p>
                  <div className="grid grid-cols-4 gap-2">
                    {['A', 'B', 'C', 'D'].map(tier => (
                      <div key={tier} className="text-center">
                        <Badge className={`${tierColors[tier]} text-white mb-1`}>{tier}</Badge>
                        <p className="text-sm font-semibold">{kpis?.quality_kpis?.tier_distribution?.[tier]?.count || 0}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Pipeline Health Tab */}
        <TabsContent value="health" className="mt-4 space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {/* Health Metrics */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Health Metrics</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm">SPICED Completion</span>
                    <div className="flex items-center gap-2">
                      <Progress value={pipelineHealth?.health_metrics?.spiced_completion_rate || 0} className="w-24 h-2" />
                      <span className="text-sm font-medium">{pipelineHealth?.health_metrics?.spiced_completion_rate || 0}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">Tier A Deals</span>
                    <div className="flex items-center gap-2">
                      <Progress value={pipelineHealth?.health_metrics?.tier_a_percentage || 0} className="w-24 h-2" />
                      <span className="text-sm font-medium">{pipelineHealth?.health_metrics?.tier_a_percentage || 0}%</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm">At Risk</span>
                    <div className="flex items-center gap-2">
                      <Progress value={pipelineHealth?.health_metrics?.at_risk_percentage || 0} className="w-24 h-2 bg-red-100" />
                      <span className="text-sm font-medium text-red-600">{pipelineHealth?.health_metrics?.at_risk_percentage || 0}%</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Risk Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Risk Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {['low', 'medium', 'high', 'critical'].map(level => (
                    <div key={level} className="flex justify-between items-center">
                      <Badge className={riskColors[level]} variant="outline">
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </Badge>
                      <span className="font-semibold">{pipelineHealth?.risk_distribution?.[level] || 0}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Stage Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Stage Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(pipelineHealth?.stage_distribution || {}).map(([stage, count]) => (
                    <div key={stage} className="flex justify-between items-center">
                      <span className="text-sm truncate max-w-[180px]">{stage}</span>
                      <Badge variant="secondary">{count}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* At Risk Deals */}
            <Card className="md:col-span-3">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  At-Risk Deals
                </CardTitle>
                <CardDescription>Deals requiring immediate attention</CardDescription>
              </CardHeader>
              <CardContent>
                {(pipelineHealth?.at_risk_deals?.length || 0) > 0 ? (
                  <div className="divide-y">
                    {pipelineHealth.at_risk_deals.map(deal => (
                      <div key={deal.id} className="flex items-center justify-between py-3">
                        <div>
                          <p className="font-medium">{deal.name}</p>
                          <p className="text-sm text-muted-foreground">Risk Score: {deal.risk_score}</p>
                        </div>
                        <Badge className={riskColors[deal.risk_score >= 70 ? 'critical' : 'high']}>
                          {deal.risk_score >= 70 ? 'Critical' : 'High'} Risk
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-green-500" />
                    <p>No high-risk deals identified</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Leaderboard Tab */}
        <TabsContent value="leaderboard" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-500" />
                Sales Leaderboard
              </CardTitle>
              <CardDescription>Performance by team member</CardDescription>
            </CardHeader>
            <CardContent>
              {(leaderboard?.leaderboard?.length || 0) > 0 ? (
                <div className="divide-y">
                  {leaderboard.leaderboard.map((user, idx) => (
                    <div key={user.user_id} className="flex items-center justify-between py-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${idx === 0 ? 'bg-amber-100 text-amber-700' : idx === 1 ? 'bg-gray-200 text-gray-700' : idx === 2 ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-500'}`}>
                          {idx + 1}
                        </div>
                        <div>
                          <p className="font-medium">{user.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {user.open_deals} open • {user.won_deals} won
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-green-600">{formatCurrency(user.won_value)}</p>
                        <p className="text-sm text-muted-foreground">Pipeline: {formatCurrency(user.pipeline_value)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Users className="w-8 h-8 mx-auto mb-2" />
                  <p>No data available</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default KPIDashboardPage;
