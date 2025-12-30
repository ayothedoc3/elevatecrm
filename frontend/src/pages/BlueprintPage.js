import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../components/ui/accordion';
import {
  CheckCircle2, Circle, AlertTriangle, Lock, Unlock,
  FileText, Send, User, ClipboardCheck, Folder, ShieldCheck,
  Calculator, ThumbsUp, FileSignature, Building, DollarSign, Star
} from 'lucide-react';

const iconMap = {
  'file-text': FileText,
  'send': Send,
  'check-circle': CheckCircle2,
  'user': User,
  'clipboard': ClipboardCheck,
  'clipboard-check': ClipboardCheck,
  'folder': Folder,
  'shield-check': ShieldCheck,
  'calculator': Calculator,
  'thumbs-up': ThumbsUp,
  'file-signature': FileSignature,
  'building-bank': Building,
  'file-check': FileText,
  'star': Star,
  'dollar-sign': DollarSign,
  'circle': Circle
};

const BlueprintPage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [blueprints, setBlueprints] = useState([]);
  const [selectedBlueprint, setSelectedBlueprint] = useState(null);

  useEffect(() => {
    fetchBlueprints();
  }, []);

  const fetchBlueprints = async () => {
    try {
      const response = await api.get('/blueprints');
      setBlueprints(response.data.blueprints);
      if (response.data.blueprints.length > 0) {
        setSelectedBlueprint(response.data.blueprints[0]);
      }
    } catch (error) {
      console.error('Error fetching blueprints:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Workflow Blueprints</h1>
        <p className="text-muted-foreground">Manage your workflow processes and requirements</p>
      </div>

      {/* Blueprint Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Blueprint List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Blueprints</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {blueprints.map(bp => (
              <Button
                key={bp.id}
                variant={selectedBlueprint?.id === bp.id ? 'default' : 'ghost'}
                className="w-full justify-start"
                onClick={() => setSelectedBlueprint(bp)}
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                {bp.name}
              </Button>
            ))}
          </CardContent>
        </Card>

        {/* Blueprint Details */}
        {selectedBlueprint && (
          <Card className="lg:col-span-3">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>{selectedBlueprint.name}</CardTitle>
                  <CardDescription>
                    {selectedBlueprint.description || 'No description'}
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  {selectedBlueprint.is_default && (
                    <Badge>Default</Badge>
                  )}
                  <Badge variant="outline">v{selectedBlueprint.version}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="stages">
                <TabsList className="mb-4">
                  <TabsTrigger value="stages">Stages ({selectedBlueprint.stages.length})</TabsTrigger>
                  <TabsTrigger value="settings">Settings</TabsTrigger>
                </TabsList>
                
                <TabsContent value="stages">
                  <div className="space-y-4">
                    {/* Progress Bar */}
                    <div className="flex items-center gap-2 p-4 rounded-lg bg-muted/50">
                      {selectedBlueprint.stages.map((stage, idx) => (
                        <React.Fragment key={stage.id}>
                          <div 
                            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium text-white"
                            style={{ backgroundColor: stage.color }}
                          >
                            {idx + 1}
                          </div>
                          {idx < selectedBlueprint.stages.length - 1 && (
                            <div className="flex-1 h-1 bg-muted rounded" style={{ backgroundColor: `${stage.color}40` }} />
                          )}
                        </React.Fragment>
                      ))}
                    </div>

                    {/* Stage List */}
                    <Accordion type="single" collapsible className="space-y-2">
                      {selectedBlueprint.stages.map((stage, idx) => {
                        const IconComponent = iconMap[stage.icon] || Circle;
                        return (
                          <AccordionItem key={stage.id} value={stage.id} className="border rounded-lg px-4">
                            <AccordionTrigger className="hover:no-underline">
                              <div className="flex items-center gap-4">
                                <div 
                                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                                  style={{ backgroundColor: `${stage.color}20` }}
                                >
                                  <IconComponent className="w-5 h-5" style={{ color: stage.color }} />
                                </div>
                                <div className="text-left">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">Stage {stage.stage_order}: {stage.name}</span>
                                    {stage.is_milestone && (
                                      <Badge variant="outline" className="text-xs">Milestone</Badge>
                                    )}
                                    {stage.is_start_stage && (
                                      <Badge className="bg-green-500/20 text-green-400 text-xs">Start</Badge>
                                    )}
                                    {stage.is_end_stage && (
                                      <Badge className="bg-blue-500/20 text-blue-400 text-xs">End</Badge>
                                    )}
                                  </div>
                                  <p className="text-sm text-muted-foreground">{stage.description || 'No description'}</p>
                                </div>
                              </div>
                            </AccordionTrigger>
                            <AccordionContent>
                              <div className="grid grid-cols-2 gap-4 pt-4">
                                {/* Required Properties */}
                                <div className="space-y-2">
                                  <h4 className="text-sm font-medium flex items-center gap-2">
                                    <Lock className="w-4 h-4" />
                                    Required Properties
                                  </h4>
                                  {stage.required_properties.length > 0 ? (
                                    <div className="flex flex-wrap gap-2">
                                      {stage.required_properties.map(prop => (
                                        <Badge key={prop} variant="secondary">{prop}</Badge>
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="text-sm text-muted-foreground">None required</p>
                                  )}
                                </div>

                                {/* Required Actions */}
                                <div className="space-y-2">
                                  <h4 className="text-sm font-medium flex items-center gap-2">
                                    <CheckCircle2 className="w-4 h-4" />
                                    Required Actions
                                  </h4>
                                  {stage.required_actions.length > 0 ? (
                                    <div className="flex flex-wrap gap-2">
                                      {stage.required_actions.map(action => (
                                        <Badge key={action} variant="outline">{action}</Badge>
                                      ))}
                                    </div>
                                  ) : (
                                    <p className="text-sm text-muted-foreground">None required</p>
                                  )}
                                </div>

                                {/* Entry Automations */}
                                {stage.entry_automations.length > 0 && (
                                  <div className="col-span-2 space-y-2">
                                    <h4 className="text-sm font-medium flex items-center gap-2">
                                      <Send className="w-4 h-4" />
                                      Entry Automations
                                    </h4>
                                    <div className="space-y-1">
                                      {stage.entry_automations.map((auto, i) => (
                                        <div key={i} className="text-sm p-2 rounded bg-muted/50">
                                          <span className="font-medium">{auto.type}</span>
                                          {auto.template && <span className="text-muted-foreground"> - Template: {auto.template}</span>}
                                          {auto.doc_type && <span className="text-muted-foreground"> - Document: {auto.doc_type}</span>}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        );
                      })}
                    </Accordion>
                  </div>
                </TabsContent>

                <TabsContent value="settings">
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <Card>
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {selectedBlueprint.allow_skip_stages ? (
                                <Unlock className="w-5 h-5 text-amber-500" />
                              ) : (
                                <Lock className="w-5 h-5 text-green-500" />
                              )}
                              <span>Skip Stages</span>
                            </div>
                            <Badge variant={selectedBlueprint.allow_skip_stages ? 'destructive' : 'default'}>
                              {selectedBlueprint.allow_skip_stages ? 'Allowed' : 'Blocked'}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <ShieldCheck className="w-5 h-5 text-blue-500" />
                              <span>Admin Override</span>
                            </div>
                            <Badge variant={selectedBlueprint.allow_admin_override ? 'default' : 'secondary'}>
                              {selectedBlueprint.allow_admin_override ? 'Enabled' : 'Disabled'}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <FileText className="w-5 h-5 text-violet-500" />
                              <span>Override Reason</span>
                            </div>
                            <Badge variant={selectedBlueprint.require_override_reason ? 'default' : 'secondary'}>
                              {selectedBlueprint.require_override_reason ? 'Required' : 'Optional'}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                              <span>Status</span>
                            </div>
                            <Badge variant={selectedBlueprint.is_active ? 'default' : 'secondary'}>
                              {selectedBlueprint.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default BlueprintPage;
