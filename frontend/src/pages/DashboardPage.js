import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { Progress } from '../components/ui/progress';
import {
  Users, DollarSign, TrendingUp, Target, ArrowUpRight, ArrowDownRight,
  Calendar, Clock, CheckCircle2, AlertCircle
} from 'lucide-react';

const DashboardPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    contacts: 0,
    deals: 0,
    totalValue: 0,
    wonDeals: 0
  });
  const [recentDeals, setRecentDeals] = useState([]);
  const [blueprintStats, setBlueprintStats] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [contactsRes, dealsRes, blueprintsRes] = await Promise.all([
        api.get('/contacts?page_size=1'),
        api.get('/deals'),
        api.get('/blueprints')
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
      
      if (blueprintsRes.data.blueprints.length > 0) {
        setBlueprintStats(blueprintsRes.data.blueprints[0]);
      }
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

        <Card className="bg-gradient-to-br from-amber-500/10 to-amber-600/10 border-amber-500/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Conversion Rate</p>
                <p className="text-3xl font-bold">68%</p>
              </div>
              <div className="p-3 bg-amber-500/20 rounded-full">
                <TrendingUp className="w-6 h-6 text-amber-500" />
              </div>
            </div>
            <div className="flex items-center mt-4 text-sm text-red-500">
              <ArrowDownRight className="w-4 h-4 mr-1" />
              <span>3% from last month</span>
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
            <div className="space-y-4">
              {recentDeals.map(deal => (
                <div key={deal.id} className="flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <DollarSign className="w-5 h-5 text-primary" />
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
                    <Badge 
                      variant={deal.blueprint_compliance === 'compliant' ? 'default' : 'secondary'}
                      className="text-xs"
                    >
                      {deal.blueprint_compliance === 'compliant' ? (
                        <><CheckCircle2 className="w-3 h-3 mr-1" /> Compliant</>
                      ) : (
                        <><AlertCircle className="w-3 h-3 mr-1" /> {deal.blueprint_compliance}</>
                      )}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* NLA Workflow Blueprint */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5" />
              NLA Workflow
            </CardTitle>
          </CardHeader>
          <CardContent>
            {blueprintStats && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium mb-2">{blueprintStats.name}</p>
                  <p className="text-xs text-muted-foreground">{blueprintStats.stages.length} stages</p>
                </div>
                
                <div className="space-y-2">
                  {blueprintStats.stages.slice(0, 8).map((stage, idx) => (
                    <div key={stage.id} className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: stage.color }}
                      />
                      <span className="text-sm truncate flex-1">{stage.name}</span>
                      {stage.is_milestone && (
                        <Badge variant="outline" className="text-xs">Milestone</Badge>
                      )}
                    </div>
                  ))}
                  {blueprintStats.stages.length > 8 && (
                    <p className="text-xs text-muted-foreground text-center">
                      +{blueprintStats.stages.length - 8} more stages
                    </p>
                  )}
                </div>

                <div className="pt-4 border-t">
                  <div className="flex justify-between text-sm mb-2">
                    <span>Overall Compliance</span>
                    <span className="font-medium">85%</span>
                  </div>
                  <Progress value={85} className="h-2" />
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DashboardPage;
