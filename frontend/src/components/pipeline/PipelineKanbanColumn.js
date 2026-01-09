/**
 * Pipeline Kanban Column Component
 * A droppable column for the pipeline kanban board
 */

import React from 'react';
import { Badge } from '../ui/badge';
import PipelineKanbanCard from './PipelineKanbanCard';

const formatCurrency = (value) => {
  if (!value) return '$0';
  return new Intl.NumberFormat('en-US', { 
    style: 'currency', 
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
};

const PipelineKanbanColumn = ({
  column,
  isDragOver,
  draggedDeal,
  movingDeal,
  onDragOver,
  onDragLeave,
  onDrop,
  onDragStart,
  onDragEnd,
  onDealClick
}) => {
  const totalValue = column.deals?.reduce((sum, d) => sum + (d.amount || 0), 0) || 0;
  
  return (
    <div
      className={`flex-shrink-0 w-[300px] rounded-lg transition-all ${
        isDragOver ? 'ring-2 ring-primary' : ''
      }`}
      onDragOver={(e) => onDragOver(e, column.id)}
      onDragLeave={onDragLeave}
      onDrop={(e) => onDrop(e, column.id)}
      data-testid={`pipeline-column-${column.id}`}
    >
      {/* Column Header */}
      <div 
        className="p-3 rounded-t-lg mb-2"
        style={{ backgroundColor: column.color + '20', borderLeft: `4px solid ${column.color}` }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{column.name}</span>
            <Badge variant="secondary" className="text-xs">
              {column.deals?.length || 0}
            </Badge>
          </div>
          {column.probability !== undefined && (
            <Badge variant="outline" className="text-xs">
              {column.probability}%
            </Badge>
          )}
        </div>
        {column.deals?.length > 0 && (
          <p className="text-xs text-muted-foreground mt-1">
            {formatCurrency(totalValue)}
          </p>
        )}
      </div>

      {/* Column Content */}
      <div className="space-y-2 min-h-[200px] p-1">
        {column.deals?.map(deal => (
          <PipelineKanbanCard
            key={deal.id}
            deal={deal}
            columnId={column.id}
            isDragged={draggedDeal?.id === deal.id}
            isMoving={movingDeal === deal.id}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            onClick={onDealClick}
          />
        ))}
        
        {(!column.deals || column.deals.length === 0) && (
          <div className="flex items-center justify-center h-24 text-xs text-muted-foreground border-2 border-dashed rounded-lg">
            Drop deals here
          </div>
        )}
      </div>
    </div>
  );
};

export default PipelineKanbanColumn;
