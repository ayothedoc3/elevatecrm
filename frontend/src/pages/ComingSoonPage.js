import React from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '../components/ui/button';

export default function ComingSoonPage({ title = 'Coming Soon', description }) {
  const navigate = useNavigate();

  return (
    <div className="max-w-2xl mx-auto py-16">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      <p className="mt-3 text-muted-foreground">
        {description || 'This module is not enabled in Phase 1 core. It will be turned on as the PostgreSQL migration continues.'}
      </p>
      <div className="mt-8">
        <Button onClick={() => navigate('/dashboard')}>Back to Dashboard</Button>
      </div>
    </div>
  );
}

