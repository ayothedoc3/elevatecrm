/**
 * Pipeline Kanban Card Component
 * A draggable deal card for the pipeline kanban board
 */

import React from 'react';
import { Building2, ClipboardList } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';

// Tier colors
const tierColors = {
  A: 'bg-green-500',
  B: 'bg-blue-500',
  C: 'bg-yellow-500',
  D: 'bg-gray-400'
};

const formatCurrency = (value) => {
  if (!value) return '$0';
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
};

const PipelineKanbanCard = ({
  deal,
  columnId,
  isDragged,
  isMoving,
  onDragStart,
  onDragEnd,
  onClick
}) => {
  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-md ${
        isDragged ? 'opacity-50' : ''
      } ${isMoving ? 'animate-pulse' : ''}`}
      draggable
      onDragStart={(e) => onDragStart(e, deal, columnId)}
      onDragEnd={onDragEnd}
      onClick={() => onClick(deal)}
      data-testid={`deal-card-${deal.id}`}
    >
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm truncate">{deal.name}</p>
            <p className="text-xs text-muted-foreground truncate">
              {deal.contact_name || 'No contact'}
            </p>
          </div>
          {deal.tier && (
            <Badge className={`${tierColors[deal.tier]} text-white text-xs`}>
              {deal.tier}
            </Badge>
          )}
        </div>
        
        <div className="flex items-center justify-between mt-2">
          <span className="text-sm font-semibold">
            {formatCurrency(deal.amount)}
          </span>
          {deal.sales_motion_type === 'partner_sales' && (
            <Badge variant="outline" className="text-xs">
              <Building2 className="w-3 h-3 mr-1" />
              Partner
            </Badge>
          )}
        </div>
        
        {/* Lead Score Progress */}
        {deal.lead_score !== undefined && (
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
              <span>Score</span>
              <span>{deal.lead_score}/100</span>
            </div>
            <Progress value={deal.lead_score} className="h-1" />
          </div>
        )}
        
        {/* SPICED indicator */}
        {(deal.spiced_summary || deal.spiced_situation) && (
          <Badge variant="secondary" className="mt-2 text-xs">
            <ClipboardList className="w-3 h-3 mr-1" />
            SPICED
          </Badge>
        )}
      </CardContent>
    </Card>
  );
};

export default PipelineKanbanCard;
