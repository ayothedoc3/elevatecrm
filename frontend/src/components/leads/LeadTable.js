/**
 * LeadTable Component
 * Extracted from LeadsPage for better maintainability
 */

import React from 'react';
import { Loader2, MoreHorizontal, Edit, Trash2, ArrowRight, Sparkles } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../ui/dropdown-menu';

// Tier badge colors
const tierColors = {
  A: 'bg-green-500 text-white',
  B: 'bg-blue-500 text-white',
  C: 'bg-yellow-500 text-black',
  D: 'bg-gray-400 text-white'
};

const statusColors = {
  new: 'bg-blue-100 text-blue-800',
  assigned: 'bg-purple-100 text-purple-800',
  working: 'bg-yellow-100 text-yellow-800',
  info_collected: 'bg-indigo-100 text-indigo-800',
  unresponsive: 'bg-gray-100 text-gray-800',
  disqualified: 'bg-red-100 text-red-800',
  qualified: 'bg-green-100 text-green-800'
};

const LeadTable = ({
  leads,
  loading,
  onRowClick,
  onEdit,
  onDelete,
  onQualify,
  onAIAssist
}) => {
  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Lead</TableHead>
              <TableHead>Company</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Sales Motion</TableHead>
              <TableHead>Source</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto" />
                </TableCell>
              </TableRow>
            ) : leads.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  No leads found. Create your first lead to get started.
                </TableCell>
              </TableRow>
            ) : (
              leads.map(lead => (
                <TableRow 
                  key={lead.id} 
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => onRowClick(lead.id)}
                  data-testid={`lead-row-${lead.id}`}
                >
                  <TableCell>
                    <div>
                      <p className="font-medium">{lead.full_name || `${lead.first_name} ${lead.last_name}`}</p>
                      <p className="text-sm text-muted-foreground">{lead.email}</p>
                    </div>
                  </TableCell>
                  <TableCell>{lead.company_name || '-'}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={lead.lead_score} className="w-16 h-2" />
                      <span className="text-sm font-medium">{lead.lead_score}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={tierColors[lead.tier] || tierColors.D}>
                      {lead.tier || 'D'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className={statusColors[lead.status] || ''}>
                      {lead.status?.replace('_', ' ') || 'new'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs">
                      {lead.sales_motion_type === 'partner_sales' ? 'Partner' : 'Partnership'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {lead.source?.replace('_', ' ') || '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(lead); }}>
                          <Edit className="w-4 h-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onAIAssist(lead); }}>
                          <Sparkles className="w-4 h-4 mr-2" />
                          AI Assist
                        </DropdownMenuItem>
                        {lead.status !== 'qualified' && lead.status !== 'disqualified' && (
                          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onQualify(lead.id); }}>
                            <ArrowRight className="w-4 h-4 mr-2" />
                            Qualify Lead
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          onClick={(e) => { e.stopPropagation(); onDelete(lead.id); }}
                          className="text-red-600"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default LeadTable;
