import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
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
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '../components/ui/sheet';
import { 
  Calculator, Check, AlertCircle, RefreshCw, DollarSign, 
  TrendingUp, Package, Loader2 
} from 'lucide-react';

const CalculationForm = ({ dealId, open, onClose, onCalculationComplete }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [definition, setDefinition] = useState(null);
  const [inputs, setInputs] = useState({});
  const [outputs, setOutputs] = useState({});
  const [isComplete, setIsComplete] = useState(false);
  const [validationErrors, setValidationErrors] = useState([]);
  const [stageReturned, setStageReturned] = useState(false);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || '';

  useEffect(() => {
    if (open && dealId) {
      fetchCalculation();
    }
  }, [open, dealId]);

  const fetchCalculation = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${backendUrl}/api/calculations/deal/${dealId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDefinition(data.definition);
        if (data.result) {
          setInputs(data.result.inputs || {});
          setOutputs(data.result.outputs || {});
          setIsComplete(data.result.is_complete);
          setValidationErrors(data.result.validation_errors || []);
        }
      }
    } catch (err) {
      console.error('Failed to fetch calculation:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (name, value) => {
    setInputs(prev => ({ ...prev, [name]: value }));
  };

  const handleMultiSelectChange = (name, value) => {
    const current = inputs[name] || [];
    if (current.includes(value)) {
      setInputs(prev => ({ ...prev, [name]: current.filter(v => v !== value) }));
    } else {
      setInputs(prev => ({ ...prev, [name]: [...current, value] }));
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setStageReturned(false);
    
    try {
      const response = await fetch(`${backendUrl}/api/calculations/deal/${dealId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ inputs })
      });
      
      if (response.ok) {
        const data = await response.json();
        setOutputs(data.outputs);
        setIsComplete(data.is_complete);
        setValidationErrors(data.validation_errors);
        setStageReturned(data.stage_returned);
        
        if (data.is_complete) {
          onCalculationComplete?.();
        }
      }
    } catch (err) {
      console.error('Failed to save calculation:', err);
    } finally {
      setSaving(false);
    }
  };

  const formatCurrency = (value) => {
    if (value === undefined || value === null) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const renderInput = (field) => {
    const value = inputs[field.name];
    
    switch (field.type) {
      case 'integer':
      case 'number':
        return (
          <Input
            type="number"
            value={value || ''}
            onChange={(e) => handleInputChange(field.name, parseInt(e.target.value) || '')}
            placeholder={field.placeholder}
            min={field.min}
            max={field.max}
          />
        );
      
      case 'currency':
        return (
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="number"
              value={value || ''}
              onChange={(e) => handleInputChange(field.name, parseFloat(e.target.value) || '')}
              placeholder={field.placeholder}
              className="pl-9"
              step="0.01"
              min={field.min}
            />
          </div>
        );
      
      case 'select':
        return (
          <Select value={value || ''} onValueChange={(v) => handleInputChange(field.name, v)}>
            <SelectTrigger>
              <SelectValue placeholder={field.placeholder || 'Select...'} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      
      case 'multi_select':
        const selectedValues = value || [];
        return (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {field.options?.map(opt => (
                <Button
                  key={opt.value}
                  type="button"
                  variant={selectedValues.includes(opt.value) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => handleMultiSelectChange(field.name, opt.value)}
                >
                  {opt.label}
                  {selectedValues.includes(opt.value) && (
                    <Check className="w-3 h-3 ml-1" />
                  )}
                </Button>
              ))}
            </div>
          </div>
        );
      
      default:
        return (
          <Input
            type="text"
            value={value || ''}
            onChange={(e) => handleInputChange(field.name, e.target.value)}
            placeholder={field.placeholder}
          />
        );
    }
  };

  if (!open) return null;

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col">
        <SheetHeader className="p-6 border-b">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/20">
              <Calculator className="w-5 h-5 text-primary" />
            </div>
            <div>
              <SheetTitle>{definition?.name || 'ROI Calculator'}</SheetTitle>
              <SheetDescription>
                {definition?.description || 'Calculate savings and recommendations'}
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <ScrollArea className="flex-1 p-6">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-6">
              {/* Stage Return Warning */}
              {stageReturned && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                  <div className="flex items-center gap-2 text-amber-500">
                    <AlertCircle className="w-4 h-4" />
                    <span className="font-medium">Deal stage updated</span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Calculation inputs changed. Deal returned to Calculations stage.
                  </p>
                </div>
              )}

              {/* Validation Errors */}
              {validationErrors.length > 0 && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <div className="flex items-center gap-2 text-red-500 mb-2">
                    <AlertCircle className="w-4 h-4" />
                    <span className="font-medium">Validation Errors</span>
                  </div>
                  <ul className="text-sm space-y-1">
                    {validationErrors.map((err, i) => (
                      <li key={i} className="text-red-400">• {err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Input Fields */}
              <div>
                <h3 className="text-sm font-semibold text-muted-foreground mb-4">
                  INPUT VALUES
                </h3>
                <div className="space-y-4">
                  {definition?.inputs?.map(field => (
                    <div key={field.name} className="space-y-2">
                      <Label className="flex items-center gap-1">
                        {field.label}
                        {field.required && <span className="text-red-500">*</span>}
                      </Label>
                      {renderInput(field)}
                      {field.help_text && (
                        <p className="text-xs text-muted-foreground">{field.help_text}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Output Values */}
              {Object.keys(outputs).length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-semibold text-muted-foreground">
                      CALCULATED RESULTS
                    </h3>
                    {isComplete && (
                      <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                        <Check className="w-3 h-3 mr-1" />
                        Complete
                      </Badge>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    {/* Monthly Spend */}
                    <Card className="bg-muted/50">
                      <CardContent className="p-4">
                        <p className="text-xs text-muted-foreground">Monthly Oil Spend</p>
                        <p className="text-2xl font-bold">
                          {formatCurrency(outputs.monthly_oil_spend)}
                        </p>
                      </CardContent>
                    </Card>

                    {/* Yearly Spend */}
                    <Card className="bg-muted/50">
                      <CardContent className="p-4">
                        <p className="text-xs text-muted-foreground">Yearly Oil Spend</p>
                        <p className="text-2xl font-bold">
                          {formatCurrency(outputs.yearly_oil_spend)}
                        </p>
                      </CardContent>
                    </Card>

                    {/* Estimated Savings */}
                    <Card className="col-span-2 bg-green-500/10 border-green-500/30">
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <TrendingUp className="w-4 h-4 text-green-500" />
                          <p className="text-sm font-medium text-green-400">Estimated Annual Savings</p>
                        </div>
                        <p className="text-3xl font-bold text-green-500">
                          {formatCurrency(outputs.estimated_savings_low)} - {formatCurrency(outputs.estimated_savings_high)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">30-50% reduction in oil costs</p>
                      </CardContent>
                    </Card>

                    {/* Recommendations */}
                    <Card className="bg-primary/10 border-primary/30">
                      <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <Package className="w-4 h-4 text-primary" />
                          <p className="text-xs text-muted-foreground">Devices Needed</p>
                        </div>
                        <p className="text-2xl font-bold">
                          {outputs.recommended_device_quantity}
                        </p>
                      </CardContent>
                    </Card>

                    <Card className="bg-primary/10 border-primary/30">
                      <CardContent className="p-4">
                        <p className="text-xs text-muted-foreground">Recommended Size</p>
                        <p className="text-2xl font-bold">
                          {outputs.recommended_device_size || '-'}
                        </p>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              )}
            </div>
          )}
        </ScrollArea>

        <div className="p-4 border-t flex gap-2">
          <Button variant="outline" className="flex-1" onClick={onClose}>
            Close
          </Button>
          <Button 
            className="flex-1" 
            onClick={handleSave}
            disabled={saving || loading}
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Calculating...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Calculate & Save
              </>
            )}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default CalculationForm;
