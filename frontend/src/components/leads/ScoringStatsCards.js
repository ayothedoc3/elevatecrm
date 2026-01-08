/**
 * ScoringStatsCards Component
 * Displays tier distribution statistics for leads
 */

import React from 'react';
import { Target, TrendingUp, AlertCircle, Star } from 'lucide-react';
import { Card, CardContent } from '../ui/card';

const tierDescriptions = {
  A: 'Priority Account (80-100)',
  B: 'Strategic (60-79)',
  C: 'Standard (40-59)',
  D: 'Nurture Only (0-39)'
};

const ScoringStatsCards = ({ scoringStats }) => {
  if (!scoringStats) return null;

  return (
    <div className="grid grid-cols-4 gap-4">
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Tier A</p>
              <p className="text-2xl font-bold text-green-600">
                {scoringStats.tier_distribution?.A || 0}
              </p>
              <p className="text-xs text-muted-foreground">{tierDescriptions.A}</p>
            </div>
            <div className="p-3 bg-green-100 rounded-full">
              <Star className="w-5 h-5 text-green-600" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Tier B</p>
              <p className="text-2xl font-bold text-blue-600">
                {scoringStats.tier_distribution?.B || 0}
              </p>
              <p className="text-xs text-muted-foreground">{tierDescriptions.B}</p>
            </div>
            <div className="p-3 bg-blue-100 rounded-full">
              <TrendingUp className="w-5 h-5 text-blue-600" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Tier C</p>
              <p className="text-2xl font-bold text-yellow-600">
                {scoringStats.tier_distribution?.C || 0}
              </p>
              <p className="text-xs text-muted-foreground">{tierDescriptions.C}</p>
            </div>
            <div className="p-3 bg-yellow-100 rounded-full">
              <Target className="w-5 h-5 text-yellow-600" />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Tier D</p>
              <p className="text-2xl font-bold text-gray-500">
                {scoringStats.tier_distribution?.D || 0}
              </p>
              <p className="text-xs text-muted-foreground">{tierDescriptions.D}</p>
            </div>
            <div className="p-3 bg-gray-100 rounded-full">
              <AlertCircle className="w-5 h-5 text-gray-500" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ScoringStatsCards;
