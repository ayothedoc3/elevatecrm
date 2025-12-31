import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { 
  Plus, Flame, Square, Check, Loader2, 
  ChevronRight, Building2, Briefcase, Calculator 
} from 'lucide-react';

const AddCRMModal = ({ open, onClose, onSuccess }) => {
  const [step, setStep] = useState(1); // 1: select blueprint, 2: configure, 3: provisioning
  const [blueprints, setBlueprints] = useState([]);
  const [selectedBlueprint, setSelectedBlueprint] = useState(null);
  const [workspaceName, setWorkspaceName] = useState('');
  const [includeDemoData, setIncludeDemoData] = useState(true);
  const [loading, setLoading] = useState(false);
  const [provisioningStatus, setProvisioningStatus] = useState(null);
  const [error, setError] = useState(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    if (open) {
      fetchBlueprints();
      resetState();
    }
  }, [open]);

  const resetState = () => {
    setStep(1);
    setSelectedBlueprint(null);
    setWorkspaceName('');
    setIncludeDemoData(true);
    setProvisioningStatus(null);
    setError(null);
  };

  const fetchBlueprints = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/workspaces/blueprints`);
      if (response.ok) {
        const data = await response.json();
        setBlueprints(data.blueprints);
        // Select default blueprint
        const defaultBp = data.blueprints.find(bp => bp.is_default);
        if (defaultBp) {
          setSelectedBlueprint(defaultBp);
        }
      }
    } catch (err) {
      console.error('Failed to fetch blueprints:', err);
    }
  };

  const handleCreate = async () => {
    if (!selectedBlueprint || !workspaceName.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${backendUrl}/api/workspaces`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          name: workspaceName.trim(),
          blueprint_slug: selectedBlueprint.slug,
          include_demo_data: includeDemoData
        })
      });

      if (response.ok) {
        const data = await response.json();
        setStep(3);
        pollProvisioningStatus(data.workspace_id);
      } else {
        const errData = await response.json();
        setError(errData.detail || 'Failed to create workspace');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const pollProvisioningStatus = async (workspaceId) => {
    const poll = async () => {
      try {
        const response = await fetch(`${backendUrl}/api/workspaces/${workspaceId}/provisioning`);
        if (response.ok) {
          const status = await response.json();
          setProvisioningStatus(status);

          if (status.status === 'completed') {
            setTimeout(() => {
              onSuccess?.(workspaceId);
            }, 1000);
          } else if (status.status === 'failed') {
            setError(status.error_message || 'Provisioning failed');
          } else {
            // Continue polling
            setTimeout(poll, 1000);
          }
        }
      } catch (err) {
        console.error('Failed to get status:', err);
      }
    };
    poll();
  };

  const getBlueprintIcon = (icon) => {
    switch (icon) {
      case 'flame':
        return <Flame className="w-8 h-8" />;
      case 'square':
        return <Square className="w-8 h-8" />;
      case 'briefcase':
        return <Briefcase className="w-8 h-8" />;
      case 'calculator':
        return <Calculator className="w-8 h-8" />;
      default:
        return <Building2 className="w-8 h-8" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !loading && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            {step === 1 && 'Add New CRM'}
            {step === 2 && 'Configure Your CRM'}
            {step === 3 && 'Creating Your CRM'}
          </DialogTitle>
          <DialogDescription>
            {step === 1 && 'Choose a blueprint to start with'}
            {step === 2 && 'Set up your new CRM workspace'}
            {step === 3 && 'Please wait while we set up your workspace...'}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Select Blueprint */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {blueprints.map(blueprint => (
                <Card 
                  key={blueprint.id}
                  className={`cursor-pointer transition-all hover:shadow-md ${
                    selectedBlueprint?.id === blueprint.id 
                      ? 'ring-2 ring-primary border-primary' 
                      : 'hover:border-primary/50'
                  }`}
                  onClick={() => setSelectedBlueprint(blueprint)}
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
                      </div>
                      {selectedBlueprint?.id === blueprint.id && (
                        <Check className="w-5 h-5 text-primary" />
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button 
                onClick={() => setStep(2)}
                disabled={!selectedBlueprint}
              >
                Continue
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step 2: Configure */}
        {step === 2 && (
          <div className="space-y-6">
            {/* Selected Blueprint Summary */}
            <Card className="bg-muted/50">
              <CardContent className="p-4 flex items-center gap-4">
                <div 
                  className="p-2 rounded-lg"
                  style={{ backgroundColor: `${selectedBlueprint.color}20` }}
                >
                  <div style={{ color: selectedBlueprint.color }}>
                    {getBlueprintIcon(selectedBlueprint.icon)}
                  </div>
                </div>
                <div>
                  <p className="font-medium">{selectedBlueprint.name}</p>
                  <p className="text-sm text-muted-foreground">Blueprint selected</p>
                </div>
                <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setStep(1)}>
                  Change
                </Button>
              </CardContent>
            </Card>

            {/* Workspace Name */}
            <div className="space-y-2">
              <Label htmlFor="workspace-name">Workspace Name</Label>
              <Input
                id="workspace-name"
                placeholder="e.g., West Coast Sales, NYC Team"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                autoFocus
              />
              <p className="text-sm text-muted-foreground">
                This will be the name of your CRM workspace
              </p>
            </div>

            {/* Demo Data Toggle */}
            <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
              <div>
                <Label>Include Demo Data</Label>
                <p className="text-sm text-muted-foreground">
                  Add sample contacts and deals to get started
                </p>
              </div>
              <Switch
                checked={includeDemoData}
                onCheckedChange={setIncludeDemoData}
              />
            </div>

            {error && (
              <div className="p-3 bg-red-500/10 text-red-500 rounded-lg text-sm">
                {error}
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
              <Button 
                onClick={handleCreate}
                disabled={!workspaceName.trim() || loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    Create CRM
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step 3: Provisioning */}
        {step === 3 && provisioningStatus && (
          <div className="space-y-6 py-4">
            <div className="text-center">
              {provisioningStatus.status === 'completed' ? (
                <div className="w-16 h-16 mx-auto rounded-full bg-green-500/20 flex items-center justify-center mb-4">
                  <Check className="w-8 h-8 text-green-500" />
                </div>
              ) : provisioningStatus.status === 'failed' ? (
                <div className="w-16 h-16 mx-auto rounded-full bg-red-500/20 flex items-center justify-center mb-4">
                  <span className="text-red-500 text-2xl">✗</span>
                </div>
              ) : (
                <div className="w-16 h-16 mx-auto rounded-full bg-primary/20 flex items-center justify-center mb-4">
                  <Loader2 className="w-8 h-8 text-primary animate-spin" />
                </div>
              )}

              <h3 className="text-xl font-semibold mb-2">
                {provisioningStatus.status === 'completed' 
                  ? 'CRM Created Successfully!' 
                  : provisioningStatus.status === 'failed'
                  ? 'Creation Failed'
                  : 'Setting Up Your CRM'}
              </h3>
              <p className="text-muted-foreground">
                {provisioningStatus.current_step || 'Initializing...'}
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>{provisioningStatus.progress}%</span>
              </div>
              <Progress value={provisioningStatus.progress} />
            </div>

            {provisioningStatus.completed_steps?.length > 0 && (
              <div className="max-h-40 overflow-y-auto space-y-1 text-sm">
                {provisioningStatus.completed_steps.slice(-5).map((step, i) => (
                  <div key={i} className="flex items-center gap-2 text-muted-foreground">
                    <Check className="w-3 h-3 text-green-500" />
                    {step}
                  </div>
                ))}
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-500/10 text-red-500 rounded-lg text-sm">
                {error}
              </div>
            )}

            {provisioningStatus.status === 'completed' && (
              <DialogFooter>
                <Button onClick={() => window.location.reload()}>
                  Open CRM
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </DialogFooter>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default AddCRMModal;
