/**
 * LeadFormDialog Component
 * A reusable dialog for creating and editing leads
 */

import React from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

const LeadFormDialog = ({
  open,
  onOpenChange,
  lead,
  setLead,
  partners,
  products,
  onLoadProducts,
  onSubmit,
  saving,
  isEdit = false
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Lead' : 'Create New Lead'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Update lead information.' : 'Enter lead information. Score will be calculated automatically.'}
          </DialogDescription>
        </DialogHeader>
        
        <Tabs defaultValue="basic" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="basic">Basic Info</TabsTrigger>
            <TabsTrigger value="scoring">Scoring Fields</TabsTrigger>
            <TabsTrigger value="sales">Sales Motion</TabsTrigger>
          </TabsList>
          
          {/* Basic Info Tab */}
          <TabsContent value="basic" className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>First Name *</Label>
                <Input
                  value={lead.first_name}
                  onChange={(e) => setLead({...lead, first_name: e.target.value})}
                  placeholder="John"
                />
              </div>
              <div className="space-y-2">
                <Label>Last Name *</Label>
                <Input
                  value={lead.last_name}
                  onChange={(e) => setLead({...lead, last_name: e.target.value})}
                  placeholder="Smith"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  type="email"
                  value={lead.email}
                  onChange={(e) => setLead({...lead, email: e.target.value})}
                  placeholder="john@company.com"
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  value={lead.phone}
                  onChange={(e) => setLead({...lead, phone: e.target.value})}
                  placeholder="555-123-4567"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Company Name</Label>
                <Input
                  value={lead.company_name}
                  onChange={(e) => setLead({...lead, company_name: e.target.value})}
                  placeholder="Acme Corp"
                />
              </div>
              <div className="space-y-2">
                <Label>Title</Label>
                <Input
                  value={lead.title}
                  onChange={(e) => setLead({...lead, title: e.target.value})}
                  placeholder="VP of Operations"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Lead Source</Label>
              <Select 
                value={lead.source} 
                onValueChange={(v) => setLead({...lead, source: v})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="referral">Referral</SelectItem>
                  <SelectItem value="partner_referral">Partner Referral</SelectItem>
                  <SelectItem value="inbound_demo">Inbound Demo Request</SelectItem>
                  <SelectItem value="website_demo">Website Demo</SelectItem>
                  <SelectItem value="trade_show">Trade Show</SelectItem>
                  <SelectItem value="webinar">Webinar</SelectItem>
                  <SelectItem value="content_download">Content Download</SelectItem>
                  <SelectItem value="cold_outreach">Cold Outreach</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </TabsContent>
          
          {/* Scoring Fields Tab */}
          <TabsContent value="scoring" className="space-y-4 mt-4">
            <div className="p-3 bg-muted rounded-lg text-sm">
              <p className="font-medium">Scoring Categories:</p>
              <p className="text-muted-foreground">
                Size (30%) • Urgency (20%) • Source (15%) • Motivation (20%) • Decision (15%)
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Economic Units (locations, sites, etc.)</Label>
                <Input
                  type="number"
                  value={lead.economic_units}
                  onChange={(e) => setLead({...lead, economic_units: e.target.value})}
                  placeholder="e.g., 25"
                />
              </div>
              <div className="space-y-2">
                <Label>Usage Volume</Label>
                <Input
                  type="number"
                  value={lead.usage_volume}
                  onChange={(e) => setLead({...lead, usage_volume: e.target.value})}
                  placeholder="e.g., 50"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Urgency (1-5)</Label>
                <Select 
                  value={lead.urgency} 
                  onValueChange={(v) => setLead({...lead, urgency: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 - Not Urgent</SelectItem>
                    <SelectItem value="2">2 - Low</SelectItem>
                    <SelectItem value="3">3 - Medium</SelectItem>
                    <SelectItem value="4">4 - High</SelectItem>
                    <SelectItem value="5">5 - Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Decision Process Clarity (1-5)</Label>
                <Select 
                  value={lead.decision_process_clarity} 
                  onValueChange={(v) => setLead({...lead, decision_process_clarity: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 - Unclear</SelectItem>
                    <SelectItem value="2">2 - Somewhat Clear</SelectItem>
                    <SelectItem value="3">3 - Moderately Clear</SelectItem>
                    <SelectItem value="4">4 - Clear</SelectItem>
                    <SelectItem value="5">5 - Very Clear</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Trigger Event</Label>
              <Input
                value={lead.trigger_event}
                onChange={(e) => setLead({...lead, trigger_event: e.target.value})}
                placeholder="e.g., Rising costs in Q4"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Primary Motivation</Label>
                <Select 
                  value={lead.primary_motivation} 
                  onValueChange={(v) => setLead({...lead, primary_motivation: v})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select motivation" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cost_reduction">Cost Reduction</SelectItem>
                    <SelectItem value="revenue_growth">Revenue Growth</SelectItem>
                    <SelectItem value="efficiency">Efficiency</SelectItem>
                    <SelectItem value="compliance">Compliance</SelectItem>
                    <SelectItem value="competitive_pressure">Competitive Pressure</SelectItem>
                    <SelectItem value="modernization">Modernization</SelectItem>
                    <SelectItem value="expansion">Expansion</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Decision Role</Label>
                <Select 
                  value={lead.decision_role} 
                  onValueChange={(v) => setLead({...lead, decision_role: v})}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="decision_maker">Decision Maker</SelectItem>
                    <SelectItem value="economic_buyer">Economic Buyer</SelectItem>
                    <SelectItem value="champion">Champion</SelectItem>
                    <SelectItem value="influencer">Influencer</SelectItem>
                    <SelectItem value="user">End User</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </TabsContent>
          
          {/* Sales Motion Tab */}
          <TabsContent value="sales" className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Sales Motion Type *</Label>
              <Select 
                value={lead.sales_motion_type} 
                onValueChange={(v) => {
                  setLead({...lead, sales_motion_type: v, partner_id: '', product_id: ''});
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="partnership_sales">Partnership Sales (Elev8 Services)</SelectItem>
                  <SelectItem value="partner_sales">Partner Sales (Partner Products)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {lead.sales_motion_type === 'partner_sales' && (
              <>
                <div className="space-y-2">
                  <Label>Partner *</Label>
                  <Select 
                    value={lead.partner_id} 
                    onValueChange={(v) => {
                      setLead({...lead, partner_id: v, product_id: ''});
                      onLoadProducts && onLoadProducts(v);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select partner" />
                    </SelectTrigger>
                    <SelectContent>
                      {partners.map(p => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {lead.partner_id && products.length > 0 && (
                  <div className="space-y-2">
                    <Label>Product *</Label>
                    <Select 
                      value={lead.product_id} 
                      onValueChange={(v) => setLead({...lead, product_id: v})}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select product" />
                      </SelectTrigger>
                      <SelectContent>
                        {products.map(p => (
                          <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </>
            )}
          </TabsContent>
        </Tabs>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={saving}>
            {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {isEdit ? 'Save Changes' : 'Create Lead'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default LeadFormDialog;
