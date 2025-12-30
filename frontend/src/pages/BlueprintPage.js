import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../components/ui/accordion';
import {
  CheckCircle2, Circle, AlertTriangle, FileText, Send, User, 
  Calculator, Target, Flame, Building, DollarSign, Star,
  ArrowRight, ChevronRight, Settings, Plus
} from 'lucide-react';

const BlueprintPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [crmBlueprints, setCrmBlueprints] = useState([]);
  const [workflowBlueprints, setWorkflowBlueprints] = useState([]);
  const [selectedCrmBlueprint, setSelectedCrmBlueprint] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [crmRes, workflowRes] = await Promise.all([
        api.get('/workspaces/blueprints'),
        api.get('/blueprints').catch(() => ({ data: { blueprints: [] } }))
      ]);
      
      setCrmBlueprints(crmRes.data.blueprints || []);
      setWorkflowBlueprints(workflowRes.data.blueprints || []);
      
      // Auto-select first CRM blueprint
      if (crmRes.data.blueprints?.length > 0) {
        const defaultBp = crmRes.data.blueprints.find(bp => bp.is_default) || crmRes.data.blueprints[0];
        await fetchBlueprintDetails(defaultBp.slug);
      }
    } catch (error) {
      console.error('Error fetching blueprints:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBlueprintDetails = async (slug) => {
    try {
      const response = await api.get(`/workspaces/blueprints/${slug}`);
      setSelectedCrmBlueprint(response.data);
    } catch (error) {
      console.error('Error fetching blueprint details:', error);
    }
  };

  const getBlueprintIcon = (icon) => {
    switch (icon) {
      case 'flame': return <Flame className="w-6 h-6" />;
      case 'building': return <Building className="w-6 h-6" />;
      case 'calculator': return <Calculator className="w-6 h-6" />;
      case 'target': return <Target className="w-6 h-6" />;
      default: return <Star className="w-6 h-6" />;
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
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
          <h1 className="text-2xl font-bold">CRM Blueprints</h1>
          <p className="text-muted-foreground">Templates for creating new CRM workspaces</p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Create Blueprint
        </Button>
      </div>

      {/* CRM Blueprints Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {crmBlueprints.map(blueprint => (
          <Card 
            key={blueprint.id}
            className={`cursor-pointer transition-all hover:shadow-md ${
              selectedCrmBlueprint?.slug === blueprint.slug ? 'ring-2 ring-primary' : ''
            }`}
            onClick={() => fetchBlueprintDetails(blueprint.slug)}
          >
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div 
                  className="p-3 rounded-lg"
                  style={{ backgroundColor: `${blueprint.color}20` }}
                >
                  <div style={{ color: blueprint.color }}>
                    {getBlueprintIcon(blueprint.icon)}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold">{blueprint.name}</h3>
                    {blueprint.is_default && (
                      <Badge variant="secondary" className="text-xs">Default</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {blueprint.description}
                  </p>
                  {blueprint.is_system && (
                    <Badge variant="outline" className="mt-2 text-xs">System</Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Selected Blueprint Details */}
      {selectedCrmBlueprint && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div 
                  className="p-3 rounded-lg"
                  style={{ backgroundColor: `${selectedCrmBlueprint.color}20` }}
                >
                  <div style={{ color: selectedCrmBlueprint.color }}>
                    {getBlueprintIcon(selectedCrmBlueprint.icon)}
                  </div>
                </div>
                <div>
                  <CardTitle>{selectedCrmBlueprint.name}</CardTitle>
                  <CardDescription>{selectedCrmBlueprint.description}</CardDescription>
                </div>
              </div>
              <Button variant="outline">
                <Settings className="w-4 h-4 mr-2" />
                Edit Blueprint
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="pipelines">
              <TabsList>
                <TabsTrigger value="pipelines">Pipelines</TabsTrigger>
                <TabsTrigger value="calculations">Calculations</TabsTrigger>
                <TabsTrigger value="rules">Transition Rules</TabsTrigger>
                <TabsTrigger value="automations">Automations</TabsTrigger>
              </TabsList>

              <TabsContent value="pipelines" className="mt-4">
                <div className="space-y-4">
                  {selectedCrmBlueprint.config?.pipelines?.map((pipeline, pIdx) => (
                    <Card key={pIdx} className="bg-muted/30">
                      <CardHeader className="py-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Target className="w-5 h-5 text-primary" />
                            <CardTitle className="text-base">{pipeline.name}</CardTitle>
                            {pipeline.is_default && (
                              <Badge variant="secondary" className="text-xs">Default</Badge>
                            )}
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {pipeline.stages?.length || 0} stages
                          </span>
                        </div>
                        <CardDescription>{pipeline.description}</CardDescription>
                      </CardHeader>
                      <CardContent className="py-0 pb-4">
                        <div className="flex flex-wrap gap-2">
                          {pipeline.stages?.map((stage, sIdx) => (
                            <div 
                              key={sIdx}
                              className="flex items-center gap-1 px-3 py-1.5 rounded-full text-sm"
                              style={{ 
                                backgroundColor: `${stage.color}20`,
                                color: stage.color 
                              }}
                            >
                              <div 
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: stage.color }}
                              />
                              {stage.name}
                              <span className="text-xs opacity-70">({stage.probability}%)</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="calculations" className="mt-4">
                <div className="space-y-4">
                  {selectedCrmBlueprint.config?.calculations?.length > 0 ? (
                    selectedCrmBlueprint.config.calculations.map((calc, cIdx) => (
                      <Card key={cIdx} className="bg-muted/30">
                        <CardHeader className="py-4">
                          <div className="flex items-center gap-2">
                            <Calculator className="w-5 h-5 text-blue-500" />
                            <CardTitle className="text-base">{calc.name}</CardTitle>
                          </div>
                          <CardDescription>{calc.description}</CardDescription>
                        </CardHeader>
                        <CardContent className="py-0 pb-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-sm font-medium mb-2">Inputs</p>
                              <div className="space-y-1">
                                {calc.inputs?.map((inp, iIdx) => (
                                  <div key={iIdx} className="flex items-center gap-2 text-sm">
                                    <ChevronRight className="w-3 h-3 text-muted-foreground" />
                                    <span>{inp.label}</span>
                                    {inp.required && <span className="text-red-500">*</span>}
                                  </div>
                                ))}
                              </div>
                            </div>
                            <div>
                              <p className="text-sm font-medium mb-2">Outputs</p>
                              <div className="space-y-1">
                                {calc.outputs?.map((out, oIdx) => (
                                  <div key={oIdx} className="flex items-center gap-2 text-sm">
                                    <ArrowRight className="w-3 h-3 text-green-500" />
                                    <span>{out.label}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Calculator className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>No calculations defined</p>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="rules" className="mt-4">
                <div className="space-y-4">
                  {selectedCrmBlueprint.config?.transition_rules?.length > 0 ? (
                    selectedCrmBlueprint.config.transition_rules.map((rule, rIdx) => (
                      <Card key={rIdx} className="bg-muted/30">
                        <CardContent className="py-4">
                          <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-amber-500/20">
                              <AlertTriangle className="w-4 h-4 text-amber-500" />
                            </div>
                            <div>
                              <p className="font-medium text-sm">
                                {rule.from_stage || 'Any'} → {rule.to_stage || 'Any'}
                              </p>
                              <p className="text-sm text-muted-foreground">{rule.error_message}</p>
                              <Badge variant="outline" className="mt-2 text-xs">
                                {rule.rule_type}
                              </Badge>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <AlertTriangle className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>No transition rules defined</p>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="automations" className="mt-4">
                <div className="space-y-4">
                  {selectedCrmBlueprint.config?.automations?.length > 0 ? (
                    selectedCrmBlueprint.config.automations.map((auto, aIdx) => (
                      <Card key={aIdx} className="bg-muted/30">
                        <CardContent className="py-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-start gap-3">
                              <div className="p-2 rounded-lg bg-violet-500/20">
                                <Send className="w-4 h-4 text-violet-500" />
                              </div>
                              <div>
                                <p className="font-medium text-sm">{auto.name}</p>
                                <p className="text-sm text-muted-foreground">
                                  Trigger: {auto.trigger?.type}
                                </p>
                                <div className="flex gap-2 mt-2">
                                  {auto.actions?.map((action, actIdx) => (
                                    <Badge key={actIdx} variant="secondary" className="text-xs">
                                      {action.type}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            </div>
                            <Badge variant={auto.is_active ? 'default' : 'secondary'}>
                              {auto.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <Send className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p>No automations defined</p>
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}

      {/* Legacy Workflow Blueprints */}
      {workflowBlueprints.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold mb-4">Workflow Blueprints</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workflowBlueprints.map(bp => (
              <Card key={bp.id}>
                <CardHeader>
                  <CardTitle className="text-base">{bp.name}</CardTitle>
                  <CardDescription>{bp.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {bp.stages?.slice(0, 5).map((stage, idx) => (
                      <div key={stage.id} className="flex items-center gap-2 text-sm">
                        <div 
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: stage.color || '#6B7280' }}
                        />
                        <span>{stage.name}</span>
                        {stage.is_milestone && (
                          <Badge variant="outline" className="text-xs">Milestone</Badge>
                        )}
                      </div>
                    ))}
                    {bp.stages?.length > 5 && (
                      <p className="text-xs text-muted-foreground">
                        +{bp.stages.length - 5} more stages
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BlueprintPage;
