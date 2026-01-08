/**
 * AI Assistant Panel Component
 * 
 * Slide-in side panel for Elev8 AI Assistant.
 * Provides:
 * - SPICED drafting assistance
 * - Lead score explanations
 * - Outreach message drafting
 * 
 * GOVERNANCE:
 * - All AI outputs are clearly marked as "AI Suggestion" or "Draft"
 * - User must explicitly save any drafts
 * - AI is advisory only - CRM is source of truth
 */

import React, { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from './ui/sheet';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';
import { Skeleton } from './ui/skeleton';
import { ScrollArea } from './ui/scroll-area';
import { 
  Sparkles, 
  Brain, 
  MessageSquare, 
  Copy, 
  Check, 
  AlertTriangle,
  Lightbulb,
  Target,
  FileText,
  Mail,
  RefreshCw,
  Info,
  Loader2,
  ChevronRight
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const AIAssistantPanel = ({ 
  open, 
  onOpenChange, 
  context,  // { type: 'lead' | 'deal', id: string, data: object }
  onApplySpiced  // Callback to apply SPICED draft to deal form
}) => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('intelligence');
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState(null);
  const [copied, setCopied] = useState(false);
  
  // Intelligence state
  const [scoreExplanation, setScoreExplanation] = useState(null);
  const [tierExplanation, setTierExplanation] = useState(null);
  
  // SPICED drafting state
  const [spicedDraft, setSpicedDraft] = useState(null);
  const [spicedContext, setSpicedContext] = useState({ notes: '', call_summary: '' });
  const [draftingSpiced, setDraftingSpiced] = useState(false);
  
  // Outreach state
  const [outreachDraft, setOutreachDraft] = useState(null);
  const [outreachType, setOutreachType] = useState('first_touch');
  const [outreachContext, setOutreachContext] = useState('');
  const [draftingOutreach, setDraftingOutreach] = useState(false);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  };

  // Check AI status on mount
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_URL}/api/elev8/ai-assistant/status`, {
          headers: getAuthHeaders()
        });
        if (response.ok) {
          const data = await response.json();
          setAiStatus(data);
        }
      } catch (error) {
        console.error('Error checking AI status:', error);
      }
    };
    
    if (open) {
      checkStatus();
    }
  }, [open]);

  // Load intelligence when panel opens for a lead
  useEffect(() => {
    if (open && context?.type === 'lead' && context?.id) {
      loadLeadIntelligence();
    }
  }, [open, context?.id]);

  const loadLeadIntelligence = async () => {
    if (!context?.id) return;
    
    setLoading(true);
    try {
      // Load score explanation
      const scoreResponse = await fetch(
        `${API_URL}/api/elev8/ai-assistant/leads/${context.id}/score-explanation`,
        { headers: getAuthHeaders() }
      );
      if (scoreResponse.ok) {
        const scoreData = await scoreResponse.json();
        setScoreExplanation(scoreData);
      }
      
      // Load tier explanation
      const tierResponse = await fetch(
        `${API_URL}/api/elev8/ai-assistant/leads/${context.id}/tier-explanation`,
        { headers: getAuthHeaders() }
      );
      if (tierResponse.ok) {
        const tierData = await tierResponse.json();
        setTierExplanation(tierData);
      }
    } catch (error) {
      console.error('Error loading intelligence:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateSpicedDraft = async () => {
    if (!context?.id || context?.type !== 'deal') return;
    
    setDraftingSpiced(true);
    try {
      const response = await fetch(`${API_URL}/api/elev8/ai-assistant/spiced/draft`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          deal_id: context.id,
          notes: spicedContext.notes || null,
          call_summary: spicedContext.call_summary || null,
          existing_spiced: context.data?.spiced_situation ? {
            situation: context.data.spiced_situation,
            pain: context.data.spiced_pain,
            impact: context.data.spiced_impact,
            critical_event: context.data.spiced_critical_event,
            economic: context.data.spiced_economic,
            decision: context.data.spiced_decision
          } : null
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setSpicedDraft(data);
        toast({
          title: "SPICED Draft Generated",
          description: "Review and edit before saving."
        });
      } else {
        const error = await response.json();
        toast({
          title: "AI Error",
          description: error.detail?.message || "Failed to generate draft",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error generating SPICED:', error);
      toast({
        title: "Error",
        description: "Failed to connect to AI service",
        variant: "destructive"
      });
    } finally {
      setDraftingSpiced(false);
    }
  };

  const generateOutreachDraft = async () => {
    if (!context?.id || context?.type !== 'lead') return;
    
    setDraftingOutreach(true);
    try {
      const params = new URLSearchParams({
        message_type: outreachType,
        ...(outreachContext && { additional_context: outreachContext })
      });
      
      const response = await fetch(
        `${API_URL}/api/elev8/ai-assistant/leads/${context.id}/outreach-draft?${params}`,
        {
          method: 'POST',
          headers: getAuthHeaders()
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setOutreachDraft(data);
        toast({
          title: "Outreach Draft Generated",
          description: "Edit and personalize before sending."
        });
      } else {
        const error = await response.json();
        toast({
          title: "AI Error",
          description: error.detail?.message || "Failed to generate draft",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error('Error generating outreach:', error);
    } finally {
      setDraftingOutreach(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    toast({ title: "Copied to clipboard" });
  };

  const applySpicedToForm = () => {
    if (spicedDraft?.draft && onApplySpiced) {
      onApplySpiced(spicedDraft.draft);
      toast({
        title: "Draft Applied",
        description: "Review and save the deal to commit changes."
      });
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[450px] sm:w-[550px] overflow-hidden flex flex-col">
        <SheetHeader className="flex-shrink-0">
          <SheetTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-500" />
            AI Assistant
            <Badge variant="secondary" className="text-xs">Advisory</Badge>
          </SheetTitle>
          <SheetDescription>
            AI suggestions for {context?.type === 'lead' ? 'lead' : 'deal'} analysis
          </SheetDescription>
        </SheetHeader>

        {/* Governance Banner */}
        <Alert className="mt-4 bg-amber-50 border-amber-200">
          <Info className="w-4 h-4 text-amber-600" />
          <AlertDescription className="text-amber-800 text-xs">
            AI is advisory only. All outputs are drafts - review before saving.
          </AlertDescription>
        </Alert>

        {/* AI Status */}
        {aiStatus && !aiStatus.is_configured && (
          <Alert className="mt-2" variant="destructive">
            <AlertTriangle className="w-4 h-4" />
            <AlertDescription>
              AI not configured. Go to Settings → AI & Intelligence.
            </AlertDescription>
          </Alert>
        )}

        <ScrollArea className="flex-1 mt-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid grid-cols-3 w-full">
              <TabsTrigger value="intelligence" className="text-xs">
                <Brain className="w-3 h-3 mr-1" />
                Intelligence
              </TabsTrigger>
              <TabsTrigger value="spiced" className="text-xs" disabled={context?.type !== 'deal'}>
                <FileText className="w-3 h-3 mr-1" />
                SPICED
              </TabsTrigger>
              <TabsTrigger value="outreach" className="text-xs" disabled={context?.type !== 'lead'}>
                <Mail className="w-3 h-3 mr-1" />
                Outreach
              </TabsTrigger>
            </TabsList>

            {/* Intelligence Tab */}
            <TabsContent value="intelligence" className="mt-4 space-y-4">
              {loading ? (
                <div className="space-y-3">
                  <Skeleton className="h-32 w-full" />
                  <Skeleton className="h-32 w-full" />
                </div>
              ) : context?.type === 'lead' ? (
                <>
                  {/* Score Breakdown */}
                  {scoreExplanation && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <Target className="w-4 h-4 text-blue-500" />
                          Score Breakdown
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="text-sm">
                        {scoreExplanation.data?.categories?.map((cat, idx) => (
                          <div key={idx} className="flex justify-between items-center py-1 border-b last:border-0">
                            <span className="text-muted-foreground">{cat.name}</span>
                            <div className="flex items-center gap-2">
                              <span className="font-medium">{cat.score}</span>
                              <span className="text-xs text-muted-foreground">/ {cat.weight}</span>
                            </div>
                          </div>
                        ))}
                        <div className="flex justify-between items-center pt-2 mt-2 border-t font-medium">
                          <span>Total Score</span>
                          <span className="text-lg">{scoreExplanation.data?.total_score}/100</span>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Tier Explanation */}
                  {tierExplanation && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <Lightbulb className="w-4 h-4 text-yellow-500" />
                          Tier Analysis
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="whitespace-pre-wrap text-sm text-muted-foreground">
                          {tierExplanation.explanation}
                        </div>
                        <p className="text-xs text-muted-foreground mt-3 italic">
                          {tierExplanation.disclaimer}
                        </p>
                      </CardContent>
                    </Card>
                  )}

                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={loadLeadIntelligence}
                    className="w-full"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh Analysis
                  </Button>
                </>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Brain className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Select a lead to view intelligence</p>
                </div>
              )}
            </TabsContent>

            {/* SPICED Tab */}
            <TabsContent value="spiced" className="mt-4 space-y-4">
              {context?.type === 'deal' ? (
                <>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Provide Context</CardTitle>
                      <CardDescription className="text-xs">
                        Add notes or call summaries to generate better drafts
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <Textarea
                        placeholder="Meeting notes, observations, customer quotes..."
                        value={spicedContext.notes}
                        onChange={(e) => setSpicedContext(prev => ({ ...prev, notes: e.target.value }))}
                        rows={3}
                        className="text-sm"
                      />
                      <Textarea
                        placeholder="Call summary (optional)..."
                        value={spicedContext.call_summary}
                        onChange={(e) => setSpicedContext(prev => ({ ...prev, call_summary: e.target.value }))}
                        rows={2}
                        className="text-sm"
                      />
                      <Button 
                        onClick={generateSpicedDraft}
                        disabled={draftingSpiced || !aiStatus?.is_configured}
                        className="w-full"
                      >
                        {draftingSpiced ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4 mr-2" />
                            Generate SPICED Draft
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>

                  {/* SPICED Draft Result */}
                  {spicedDraft && (
                    <Card className="border-purple-200 bg-purple-50/50">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-purple-500" />
                            AI Draft
                          </CardTitle>
                          <Badge variant="outline" className="text-xs">Not Saved</Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm">
                        {spicedDraft.draft && Object.entries(spicedDraft.draft).map(([key, value]) => (
                          <div key={key}>
                            <p className="font-medium text-purple-700 capitalize">{key.replace('_', ' ')}</p>
                            <p className="text-muted-foreground">{value || '-'}</p>
                          </div>
                        ))}

                        {spicedDraft.suggestions?.length > 0 && (
                          <div className="pt-2 border-t">
                            <p className="font-medium text-sm mb-1">Suggested Follow-ups:</p>
                            <ul className="list-disc list-inside text-xs text-muted-foreground">
                              {spicedDraft.suggestions.map((s, i) => (
                                <li key={i}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        <p className="text-xs text-amber-600 italic">
                          {spicedDraft.disclaimer}
                        </p>

                        <div className="flex gap-2 pt-2">
                          <Button onClick={applySpicedToForm} size="sm" className="flex-1">
                            <ChevronRight className="w-4 h-4 mr-1" />
                            Apply to Form
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => copyToClipboard(JSON.stringify(spicedDraft.draft, null, 2))}
                          >
                            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Open a deal to draft SPICED</p>
                </div>
              )}
            </TabsContent>

            {/* Outreach Tab */}
            <TabsContent value="outreach" className="mt-4 space-y-4">
              {context?.type === 'lead' ? (
                <>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">Message Type</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { value: 'first_touch', label: 'First Touch' },
                          { value: 'follow_up', label: 'Follow Up' },
                          { value: 'discovery_prep', label: 'Discovery Prep' },
                          { value: 'demo_agenda', label: 'Demo Agenda' }
                        ].map(type => (
                          <Button
                            key={type.value}
                            variant={outreachType === type.value ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setOutreachType(type.value)}
                            className="text-xs"
                          >
                            {type.label}
                          </Button>
                        ))}
                      </div>
                      
                      <Textarea
                        placeholder="Additional context (optional)..."
                        value={outreachContext}
                        onChange={(e) => setOutreachContext(e.target.value)}
                        rows={2}
                        className="text-sm"
                      />
                      
                      <Button 
                        onClick={generateOutreachDraft}
                        disabled={draftingOutreach || !aiStatus?.is_configured}
                        className="w-full"
                      >
                        {draftingOutreach ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <MessageSquare className="w-4 h-4 mr-2" />
                            Generate Draft
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>

                  {/* Outreach Draft Result */}
                  {outreachDraft && (
                    <Card className="border-blue-200 bg-blue-50/50">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Mail className="w-4 h-4 text-blue-500" />
                            Message Draft
                          </CardTitle>
                          <Badge variant="outline" className="text-xs capitalize">
                            {outreachDraft.tone}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3 text-sm">
                        {outreachDraft.subject && (
                          <div>
                            <p className="font-medium text-blue-700">Subject</p>
                            <p className="text-muted-foreground">{outreachDraft.subject}</p>
                          </div>
                        )}
                        <div>
                          <p className="font-medium text-blue-700">Body</p>
                          <p className="text-muted-foreground whitespace-pre-wrap">
                            {outreachDraft.body}
                          </p>
                        </div>

                        {outreachDraft.personalization_notes?.length > 0 && (
                          <div className="pt-2 border-t">
                            <p className="font-medium text-xs mb-1">Personalized:</p>
                            <div className="flex flex-wrap gap-1">
                              {outreachDraft.personalization_notes.map((note, i) => (
                                <Badge key={i} variant="secondary" className="text-xs">
                                  {note}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        <p className="text-xs text-amber-600 italic">
                          {outreachDraft.disclaimer}
                        </p>

                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => copyToClipboard(
                            `${outreachDraft.subject ? `Subject: ${outreachDraft.subject}\n\n` : ''}${outreachDraft.body}`
                          )}
                          className="w-full"
                        >
                          {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                          Copy to Clipboard
                        </Button>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Mail className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Select a lead for outreach drafts</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
};

export default AIAssistantPanel;
