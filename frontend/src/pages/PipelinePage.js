import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { ScrollArea } from '../components/ui/scroll-area';
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
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Progress } from '../components/ui/progress';
import {
  DollarSign, User, Clock, CheckCircle2, AlertTriangle,
  ChevronRight, GripVertical, MoreHorizontal, Plus, RefreshCw
} from 'lucide-react';

const PipelinePage = () => {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [pipelines, setPipelines] = useState([]);
  const [selectedPipeline, setSelectedPipeline] = useState(null);
  const [kanbanData, setKanbanData] = useState(null);
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [dealProgress, setDealProgress] = useState(null);
  const [showDealModal, setShowDealModal] = useState(false);
  const [movingDeal, setMovingDeal] = useState(null);

  useEffect(() => {
    fetchPipelines();
  }, []);

  useEffect(() => {
    if (selectedPipeline) {
      fetchKanbanData(selectedPipeline);
    }
  }, [selectedPipeline]);

  const fetchPipelines = async () => {
    try {
      const response = await api.get('/pipelines');
      setPipelines(response.data.pipelines);
      if (response.data.pipelines.length > 0) {
        setSelectedPipeline(response.data.pipelines[0].id);
      }
    } catch (error) {
      console.error('Error fetching pipelines:', error);
    }
  };

  const fetchKanbanData = async (pipelineId) => {
    setLoading(true);
    try {
      const response = await api.get(`/pipelines/${pipelineId}/kanban`);
      setKanbanData(response.data);
    } catch (error) {
      console.error('Error fetching kanban data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDealProgress = async (dealId) => {
    try {
      const response = await api.get(`/deals/${dealId}/blueprint-progress`);
      setDealProgress(response.data);
    } catch (error) {
      console.error('Error fetching deal progress:', error);
    }
  };

  const handleDealClick = async (deal) => {
    setSelectedDeal(deal);
    setShowDealModal(true);
    await fetchDealProgress(deal.id);
  };

  const handleMoveStage = async (dealId, targetStageId) => {
    setMovingDeal(dealId);
    try {
      await api.post(`/deals/${dealId}/move-stage`, {
        stage_id: targetStageId
      });
      // Refresh kanban
      await fetchKanbanData(selectedPipeline);
    } catch (error) {
      console.error('Error moving deal:', error);
    } finally {
      setMovingDeal(null);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0
    }).format(value);
  };

  const getComplianceBadge = (status) => {
    switch (status) {
      case 'compliant':
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/30"><CheckCircle2 className="w-3 h-3 mr-1" />Compliant</Badge>;
      case 'overridden':
        return <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30"><AlertTriangle className="w-3 h-3 mr-1" />Override</Badge>;
      case 'missing_requirements':
        return <Badge className="bg-red-500/20 text-red-400 border-red-500/30"><AlertTriangle className="w-3 h-3 mr-1" />Missing</Badge>;
      default:
        return <Badge variant="outline">N/A</Badge>;
    }
  };

  if (loading && !kanbanData) {
    return (
      <div className="space-y-4">
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex-1 min-w-[280px]">
              <Skeleton className="h-8 w-32 mb-4" />
              <Skeleton className="h-32 w-full mb-2" />
              <Skeleton className="h-32 w-full" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Select value={selectedPipeline} onValueChange={setSelectedPipeline}>
            <SelectTrigger className="w-[280px]">
              <SelectValue placeholder="Select pipeline" />
            </SelectTrigger>
            <SelectContent>
              {pipelines.map(p => (
                <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Button variant="outline" size="sm" onClick={() => fetchKanbanData(selectedPipeline)}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        {kanbanData && (
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{kanbanData.total_deals} deals</span>
            <span className="font-semibold text-foreground">
              {formatCurrency(kanbanData.total_value)} total value
            </span>
          </div>
        )}
      </div>

      {/* Kanban Board */}
      <ScrollArea className="h-[calc(100vh-220px)]">
        <div className="flex gap-4 pb-4" style={{ minWidth: 'max-content' }}>
          {kanbanData?.columns.map((column, colIndex) => (
            <div 
              key={column.id} 
              className="flex-shrink-0 w-[320px]"
            >
              {/* Column Header */}
              <div 
                className="p-3 rounded-t-lg border border-b-0" 
                style={{ 
                  backgroundColor: `${column.color}15`,
                  borderColor: `${column.color}40`
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: column.color }}
                    />
                    <span className="font-medium text-sm">{column.name}</span>
                    <Badge variant="secondary" className="text-xs">
                      {column.deal_count}
                    </Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {column.probability}%
                  </span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {formatCurrency(column.total_value)}
                </div>
              </div>

              {/* Column Content */}
              <div 
                className="p-2 space-y-2 min-h-[400px] rounded-b-lg border border-t-0 bg-muted/30"
                style={{ borderColor: `${column.color}40` }}
              >
                {column.deals.map(deal => (
                  <Card 
                    key={deal.id}
                    className={`cursor-pointer hover:shadow-md transition-all border-l-4 ${
                      movingDeal === deal.id ? 'opacity-50' : ''
                    }`}
                    style={{ borderLeftColor: column.color }}
                    onClick={() => handleDealClick(deal)}
                  >
                    <CardContent className="p-3 space-y-2">
                      <div className="flex items-start justify-between">
                        <p className="font-medium text-sm leading-tight">{deal.name}</p>
                        <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-lg font-bold text-primary">
                          {formatCurrency(deal.amount)}
                        </span>
                        {getComplianceBadge(deal.blueprint_compliance)}
                      </div>
                      
                      {deal.contact_name && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <User className="w-3 h-3" />
                          <span>{deal.contact_name}</span>
                        </div>
                      )}
                      
                      {/* Quick Move Buttons */}
                      <div className="flex gap-1 pt-2 border-t">
                        {colIndex > 0 && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="flex-1 h-7 text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMoveStage(deal.id, kanbanData.columns[colIndex - 1].id);
                            }}
                            disabled={movingDeal === deal.id}
                          >
                            ← Back
                          </Button>
                        )}
                        {colIndex < kanbanData.columns.length - 1 && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="flex-1 h-7 text-xs"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleMoveStage(deal.id, kanbanData.columns[colIndex + 1].id);
                            }}
                            disabled={movingDeal === deal.id}
                          >
                            Next →
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
                
                {column.deals.length === 0 && (
                  <div className="h-32 flex items-center justify-center text-sm text-muted-foreground">
                    No deals in this stage
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Deal Detail Modal */}
      <Dialog open={showDealModal} onOpenChange={setShowDealModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedDeal?.name}</DialogTitle>
            <DialogDescription>
              {selectedDeal?.contact_name || 'No contact assigned'}
            </DialogDescription>
          </DialogHeader>
          
          {selectedDeal && (
            <div className="space-y-6">
              {/* Deal Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Deal Value</p>
                  <p className="text-2xl font-bold">{formatCurrency(selectedDeal.amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div className="flex items-center gap-2 mt-1">
                    {getComplianceBadge(selectedDeal.blueprint_compliance)}
                  </div>
                </div>
              </div>

              {/* Blueprint Progress */}
              {dealProgress?.has_blueprint && dealProgress.progress && (
                <div className="space-y-4 p-4 rounded-lg bg-muted/50">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{dealProgress.blueprint_name}</p>
                      <p className="text-sm text-muted-foreground">
                        Stage {dealProgress.progress.current_stage} of {dealProgress.progress.total_stages}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold">{dealProgress.progress.progress_percentage}%</p>
                      <p className="text-xs text-muted-foreground">Complete</p>
                    </div>
                  </div>
                  
                  <Progress value={dealProgress.progress.progress_percentage} className="h-2" />
                  
                  {/* Stage List */}
                  <div className="grid grid-cols-3 gap-2 mt-4">
                    {dealProgress.progress.stages.map((stage, idx) => (
                      <div 
                        key={stage.id}
                        className={`p-2 rounded text-xs flex items-center gap-2 ${
                          stage.is_current 
                            ? 'bg-primary/20 border border-primary' 
                            : stage.is_completed 
                              ? 'bg-green-500/20' 
                              : 'bg-muted'
                        }`}
                      >
                        <div 
                          className="w-2 h-2 rounded-full flex-shrink-0" 
                          style={{ backgroundColor: stage.color }}
                        />
                        <span className="truncate">{stage.name}</span>
                        {stage.is_completed && <CheckCircle2 className="w-3 h-3 text-green-500 flex-shrink-0" />}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PipelinePage;
