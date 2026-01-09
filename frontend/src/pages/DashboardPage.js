import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Progress } from '../components/ui/progress';
import {
  Users, DollarSign, TrendingUp, Target, ArrowUpRight, ArrowDownRight,
  Calendar, Clock, CheckCircle2, AlertCircle, Flame, Phone, Mail,
  Calculator, ArrowRight
} from 'lucide-react';
import { DashboardTasksWidget } from '../components/dashboard';
import { slaNotificationService } from '../services/SLANotificationService';

const DashboardPage = () => {
  const { api, currentWorkspace } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    contacts: 0,
    deals: 0,
    totalValue: 0,
    wonDeals: 0
  });
  const [recentDeals, setRecentDeals] = useState([]);
  const [pipelines, setPipelines] = useState([]);

  useEffect(() => {
    fetchDashboardData();
    
    // Start SLA notifications
    slaNotificationService.start(5); // Check every 5 minutes
    
    return () => {
      slaNotificationService.stop();
    };
  }, [currentWorkspace]);

  const fetchDashboardData = async () => {
    try {
      const [contactsRes, dealsRes, pipelinesRes] = await Promise.all([
        api.get('/contacts?page_size=1'),
        api.get('/deals'),
        api.get('/pipelines')
      ]);

      const deals = dealsRes.data.deals;
      const wonDeals = deals.filter(d => d.status === 'won');
      const totalValue = deals.reduce((sum, d) => sum + (d.amount || 0), 0);

      setStats({
        contacts: contactsRes.data.total,
        deals: dealsRes.data.total,
        totalValue,
        wonDeals: wonDeals.length
      });

      setRecentDeals(deals.slice(0, 5));
      setPipelines(pipelinesRes.data.pipelines || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0
    }).format(value);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-4 w-24 mb-2" />
                <Skeleton className="h-8 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome Header */}
      {currentWorkspace && (
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Flame className="w-6 h-6 text-orange-500" />
              {currentWorkspace.name}
            </h1>
            <p className="text-muted-foreground">Sales Dashboard</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Phone className="w-4 h-4 mr-2" />
              Log Call
            </Button>
            <Button size="sm">
              <Target className="w-4 h-4 mr-2" />
              New Deal
            </Button>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/10 border-blue-500/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Contacts</p>
                <p className="text-3xl font-bold">{stats.contacts}</p>
              </div>
              <div className="p-3 bg-blue-500/20 rounded-full">
                <Users className="w-6 h-6 text-blue-500" />
              </div>
            </div>
            <div className="flex items-center mt-4 text-sm text-green-500">
              <ArrowUpRight className="w-4 h-4 mr-1" />
              <span>12% from last month</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-violet-500/10 to-violet-600/10 border-violet-500/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Deals</p>
                <p className="text-3xl font-bold">{stats.deals}</p>
              </div>
              <div className="p-3 bg-violet-500/20 rounded-full">
                <Target className="w-6 h-6 text-violet-500" />
              </div>
            </div>
            <div className="flex items-center mt-4 text-sm text-green-500">
              <ArrowUpRight className="w-4 h-4 mr-1" />
              <span>8% from last month</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/10 border-emerald-500/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Pipeline Value</p>
                <p className="text-3xl font-bold">{formatCurrency(stats.totalValue)}</p>
              </div>
              <div className="p-3 bg-emerald-500/20 rounded-full">
                <DollarSign className="w-6 h-6 text-emerald-500" />
              </div>
            </div>
            <div className="flex items-center mt-4 text-sm text-green-500">
              <ArrowUpRight className="w-4 h-4 mr-1" />
              <span>24% from last month</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-orange-500/10 to-orange-600/10 border-orange-500/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Deals Won</p>
                <p className="text-3xl font-bold">{stats.wonDeals}</p>
              </div>
              <div className="p-3 bg-orange-500/20 rounded-full">
                <TrendingUp className="w-6 h-6 text-orange-500" />
              </div>
            </div>
            <div className="flex items-center mt-4 text-sm text-green-500">
              <ArrowUpRight className="w-4 h-4 mr-1" />
              <span>18% from last month</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Deals */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Recent Deals
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recentDeals.length > 0 ? (
              <div className="space-y-4">
                {recentDeals.map(deal => (
                  <div key={deal.id} className="flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-orange-500/10 flex items-center justify-center">
                        <Flame className="w-5 h-5 text-orange-500" />
                      </div>
                      <div>
                        <p className="font-medium">{deal.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {deal.contact_name || 'No contact'} • {deal.stage_name}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{formatCurrency(deal.amount)}</p>
                      {deal.blueprint_compliance && (
                        <Badge 
                          variant={deal.blueprint_compliance === 'compliant' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {deal.blueprint_compliance === 'compliant' ? (
                            <><CheckCircle2 className="w-3 h-3 mr-1" /> On Track</>
                          ) : (
                            <><AlertCircle className="w-3 h-3 mr-1" /> Needs Attention</>
                          )}
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Target className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No deals yet</p>
                <p className="text-sm">Create your first deal to get started</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tasks & SLA Widget */}
        <DashboardTasksWidget />
      </div>

      {/* Pipeline Overview Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Sales Workflow */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Flame className="w-5 h-5 text-orange-500" />
              Sales Workflow
            </CardTitle>
            <CardDescription>Your active pipelines</CardDescription>
          </CardHeader>
          <CardContent>
            {pipelines.length > 0 ? (
              <div className="space-y-4">
                {pipelines.map((pipeline) => (
                  <div key={pipeline.id} className="p-4 rounded-lg bg-muted/50">
                    <div className="flex items-center justify-between mb-3">
                      <p className="font-medium">{pipeline.name}</p>
                      <Badge variant="outline" className="text-xs">
                        {pipeline.deal_count || 0} deals
                      </Badge>
                    </div>
                    
                    <div className="space-y-2">
                      {pipeline.stages?.slice(0, 4).map((stage, idx) => (
                        <div key={stage.id} className="flex items-center gap-2">
                          <div 
                            className="w-2 h-2 rounded-full" 
                            style={{ backgroundColor: stage.color || '#6B7280' }}
                          />
                          <span className="text-sm truncate flex-1">{stage.name}</span>
                          <span className="text-xs text-muted-foreground">
                            {stage.probability || 0}%
                          </span>
                        </div>
                      ))}
                      {pipeline.stages?.length > 4 && (
                        <p className="text-xs text-muted-foreground text-center">
                          +{pipeline.stages.length - 4} more stages
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground">
                <p className="text-sm">No pipelines configured</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="cursor-pointer hover:border-primary/50 transition-colors">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Calculator className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <p className="font-medium">ROI Calculator</p>
              <p className="text-sm text-muted-foreground">Calculate oil savings for prospects</p>
            </div>
            <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto" />
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-primary/50 transition-colors">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 bg-green-500/20 rounded-lg">
              <Mail className="w-6 h-6 text-green-500" />
            </div>
            <div>
              <p className="font-medium">Send Campaign</p>
              <p className="text-sm text-muted-foreground">Email or SMS outreach</p>
            </div>
            <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto" />
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:border-primary/50 transition-colors">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 bg-violet-500/20 rounded-lg">
              <Calendar className="w-6 h-6 text-violet-500" />
            </div>
            <div>
              <p className="font-medium">Schedule Demo</p>
              <p className="text-sm text-muted-foreground">Book product demonstrations</p>
            </div>
            <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardPage;
