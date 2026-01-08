/**
 * LeadFilters Component
 * Extracted from LeadsPage for better maintainability
 */

import React from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

const LeadFilters = ({
  search,
  setSearch,
  filterTier,
  setFilterTier,
  filterStatus,
  setFilterStatus,
  filterMotion,
  setFilterMotion,
  onRefresh
}) => {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex-1 min-w-[250px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search leads..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
                data-testid="lead-search-input"
              />
            </div>
          </div>
          <Select value={filterTier} onValueChange={setFilterTier}>
            <SelectTrigger className="w-[140px]" data-testid="tier-filter">
              <SelectValue placeholder="Tier" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Tiers</SelectItem>
              <SelectItem value="A">Tier A</SelectItem>
              <SelectItem value="B">Tier B</SelectItem>
              <SelectItem value="C">Tier C</SelectItem>
              <SelectItem value="D">Tier D</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-[160px]" data-testid="status-filter">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="new">New</SelectItem>
              <SelectItem value="working">Working</SelectItem>
              <SelectItem value="info_collected">Info Collected</SelectItem>
              <SelectItem value="qualified">Qualified</SelectItem>
              <SelectItem value="unresponsive">Unresponsive</SelectItem>
              <SelectItem value="disqualified">Disqualified</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filterMotion} onValueChange={setFilterMotion}>
            <SelectTrigger className="w-[180px]" data-testid="motion-filter">
              <SelectValue placeholder="Sales Motion" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Motions</SelectItem>
              <SelectItem value="partnership_sales">Partnership Sales</SelectItem>
              <SelectItem value="partner_sales">Partner Sales</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={onRefresh} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default LeadFilters;
