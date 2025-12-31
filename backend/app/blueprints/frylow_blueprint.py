"""
Frylow Sales CRM Blueprint Definition

This module contains the complete blueprint configuration for the Frylow Sales CRM.
It defines pipelines, stages, calculations, workflow rules, and forms.
"""

import json

FRYLOW_BLUEPRINT = {
    "name": "Frylow Sales CRM",
    "slug": "frylow-sales",
    "description": "Complete sales CRM for Frylow oil savings solutions with dual pipelines and ROI calculations",
    "version": 1,
    "icon": "flame",
    "color": "#F97316",
    
    # ==================== PIPELINES ====================
    "pipelines": [
        {
            "name": "Qualifying",
            "slug": "qualifying",
            "description": "Lead qualification pipeline - from first contact to qualified hot lead",
            "is_default": True,
            "display_order": 0,
            "stages": [
                {
                    "name": "New / Assigned",
                    "slug": "new-assigned",
                    "description": "Newly assigned leads awaiting first contact",
                    "display_order": 0,
                    "probability": 5,
                    "color": "#6366F1",
                    "rules": {
                        "auto_move_on_assignment": True,
                        "max_time_hours": 24
                    }
                },
                {
                    "name": "Working (Contact Attempts)",
                    "slug": "working",
                    "description": "Active outreach in progress",
                    "display_order": 1,
                    "probability": 15,
                    "color": "#8B5CF6",
                    "rules": {
                        "track_touchpoints": True,
                        "min_touchpoints_for_unresponsive": 6,
                        "max_touchpoints_for_unresponsive": 10
                    }
                },
                {
                    "name": "Info Collected",
                    "slug": "info-collected",
                    "description": "All calculation inputs gathered - ready for qualification",
                    "display_order": 2,
                    "probability": 35,
                    "color": "#A855F7",
                    "rules": {
                        "require_calculation_inputs": True
                    }
                },
                {
                    "name": "Unresponsive",
                    "slug": "unresponsive",
                    "description": "No response after required touchpoints",
                    "display_order": 3,
                    "probability": 5,
                    "color": "#64748B",
                    "rules": {
                        "require_min_touchpoints": 6,
                        "is_nurture_stage": True
                    }
                },
                {
                    "name": "Disqualified",
                    "slug": "disqualified",
                    "description": "Lead does not meet qualification criteria",
                    "display_order": 4,
                    "probability": 0,
                    "color": "#EF4444",
                    "is_lost_stage": True,
                    "rules": {
                        "require_disqualification_reason": True
                    }
                },
                {
                    "name": "Qualified → Push to Hot Lead",
                    "slug": "qualified",
                    "description": "Qualified and ready to move to Hot Lead pipeline",
                    "display_order": 5,
                    "probability": 50,
                    "color": "#10B981",
                    "rules": {
                        "is_transition_stage": True,
                        "transition_to_pipeline": "hot-leads",
                        "transition_to_stage": "calculations-in-progress",
                        "require_all_inputs": True
                    }
                }
            ]
        },
        {
            "name": "Hot Leads",
            "slug": "hot-leads",
            "description": "Qualified leads - from calculation to close",
            "is_default": False,
            "display_order": 1,
            "stages": [
                {
                    "name": "Calculations In Progress",
                    "slug": "calculations-in-progress",
                    "description": "ROI calculations being computed",
                    "display_order": 0,
                    "probability": 55,
                    "color": "#6366F1",
                    "rules": {
                        "auto_calculate": True,
                        "return_here_on_input_change": True
                    }
                },
                {
                    "name": "Demo Scheduled",
                    "slug": "demo-scheduled",
                    "description": "Product demonstration scheduled",
                    "display_order": 1,
                    "probability": 65,
                    "color": "#8B5CF6",
                    "rules": {
                        "require_calculation_complete": True,
                        "require_demo_date": True
                    }
                },
                {
                    "name": "Demo Completed",
                    "slug": "demo-completed",
                    "description": "Demonstration successfully delivered",
                    "display_order": 2,
                    "probability": 75,
                    "color": "#A855F7",
                    "rules": {
                        "require_demo_completed_action": True,
                        "on_no_show": "return_to_working"
                    }
                },
                {
                    "name": "Decision Pending",
                    "slug": "decision-pending",
                    "description": "Awaiting customer decision",
                    "display_order": 3,
                    "probability": 80,
                    "color": "#D946EF",
                    "rules": {
                        "require_demo_completed": True
                    }
                },
                {
                    "name": "Device Trial",
                    "slug": "device-trial",
                    "description": "Customer testing device (if applicable)",
                    "display_order": 4,
                    "probability": 85,
                    "color": "#EC4899",
                    "rules": {
                        "is_optional": True,
                        "trial_period_days": 30
                    }
                },
                {
                    "name": "Verbal Commitment (Invoice/Discount Sent)",
                    "slug": "verbal-commitment",
                    "description": "Customer committed - invoice or discount sent",
                    "display_order": 5,
                    "probability": 90,
                    "color": "#F97316",
                    "rules": {
                        "require_demo_completed": True,
                        "require_commitment_action": True
                    }
                },
                {
                    "name": "Closed Won",
                    "slug": "closed-won",
                    "description": "Deal successfully closed",
                    "display_order": 6,
                    "probability": 100,
                    "color": "#10B981",
                    "is_won_stage": True,
                    "rules": {
                        "require_signed_contract": False  # Can close without
                    }
                },
                {
                    "name": "Closed Lost",
                    "slug": "closed-lost",
                    "description": "Deal lost",
                    "display_order": 7,
                    "probability": 0,
                    "color": "#EF4444",
                    "is_lost_stage": True,
                    "rules": {
                        "require_lost_reason": True
                    }
                }
            ]
        }
    ],
    
    # ==================== CALCULATIONS ====================
    "calculations": [
        {
            "name": "Frylow Oil Savings Calculator",
            "slug": "frylow-savings",
            "description": "Calculate monthly/yearly oil spend and estimated savings with Frylow",
            "version": 1,
            "inputs": [
                {
                    "name": "number_of_fryers",
                    "type": "integer",
                    "label": "Number of Fryers",
                    "required": True,
                    "min": 1,
                    "max": 100,
                    "placeholder": "Enter number of fryers",
                    "help_text": "Total number of fryers at the location"
                },
                {
                    "name": "fryer_capacities",
                    "type": "multi_select",
                    "label": "Fryer Capacity (Liters)",
                    "required": True,
                    "options": [
                        {"value": "16L", "label": "16 Liters"},
                        {"value": "30L", "label": "30 Liters"},
                        {"value": "45L", "label": "45 Liters"}
                    ],
                    "help_text": "Select all fryer sizes used",
                    "allow_multiple": True
                },
                {
                    "name": "oil_units",
                    "type": "select",
                    "label": "Oil Purchase Units",
                    "required": True,
                    "options": [
                        {"value": "boxes", "label": "Boxes"},
                        {"value": "pails", "label": "Pails"}
                    ],
                    "help_text": "How do you purchase cooking oil?"
                },
                {
                    "name": "quantity_per_month",
                    "type": "integer",
                    "label": "Quantity per Month",
                    "required": True,
                    "min": 1,
                    "placeholder": "Enter monthly quantity",
                    "help_text": "How many boxes/pails do you use per month?"
                },
                {
                    "name": "cost_per_unit",
                    "type": "currency",
                    "label": "Cost per Unit ($)",
                    "required": True,
                    "min": 0.01,
                    "placeholder": "Enter cost per box/pail",
                    "currency": "USD",
                    "help_text": "Price per box or pail"
                }
            ],
            "outputs": [
                {
                    "name": "monthly_oil_spend",
                    "type": "currency",
                    "label": "Monthly Oil Spend",
                    "currency": "USD",
                    "formula": "quantity_per_month * cost_per_unit"
                },
                {
                    "name": "yearly_oil_spend",
                    "type": "currency",
                    "label": "Yearly Oil Spend",
                    "currency": "USD",
                    "formula": "monthly_oil_spend * 12"
                },
                {
                    "name": "estimated_savings_low",
                    "type": "currency",
                    "label": "Estimated Annual Savings (Low)",
                    "currency": "USD",
                    "formula": "yearly_oil_spend * 0.30",
                    "description": "30% savings estimate"
                },
                {
                    "name": "estimated_savings_high",
                    "type": "currency",
                    "label": "Estimated Annual Savings (High)",
                    "currency": "USD",
                    "formula": "yearly_oil_spend * 0.50",
                    "description": "50% savings estimate"
                },
                {
                    "name": "recommended_device_quantity",
                    "type": "integer",
                    "label": "Recommended Frylow Devices",
                    "formula": "number_of_fryers",
                    "description": "One device per fryer"
                },
                {
                    "name": "recommended_device_size",
                    "type": "text",
                    "label": "Recommended Device Size",
                    "formula": "calculate_device_size(fryer_capacities)",
                    "description": "Based on largest fryer capacity"
                }
            ],
            "editable_by_roles": ["admin", "manager", "sales_rep"],
            "required_for_stages": ["demo-scheduled"],
            "return_to_stage_on_change": "calculations-in-progress"
        }
    ],
    
    # ==================== STAGE TRANSITION RULES ====================
    "transition_rules": [
        # Qualifying Pipeline Rules
        {
            "pipeline": "qualifying",
            "from_stage": "new-assigned",
            "to_stage": "working",
            "rule_type": "auto_transition",
            "config": {"on_assignment": True},
            "error_message": "Lead must move to Working immediately after assignment"
        },
        {
            "pipeline": "qualifying",
            "from_stage": "working",
            "to_stage": "unresponsive",
            "rule_type": "require_touchpoints",
            "config": {"min_count": 6, "max_count": 10},
            "error_message": "6-10 outreach touchpoints required before marking as Unresponsive"
        },
        {
            "pipeline": "qualifying",
            "from_stage": "working",
            "to_stage": "info-collected",
            "rule_type": "require_calculation_inputs",
            "config": {"calculation": "frylow-savings", "all_inputs": True},
            "error_message": "All calculation inputs must be collected before moving to Info Collected"
        },
        {
            "pipeline": "qualifying",
            "from_stage": "info-collected",
            "to_stage": "qualified",
            "rule_type": "require_calculation_inputs",
            "config": {"calculation": "frylow-savings", "all_inputs": True},
            "error_message": "All required information must be collected to qualify"
        },
        
        # Hot Leads Pipeline Rules
        {
            "pipeline": "hot-leads",
            "from_stage": "calculations-in-progress",
            "to_stage": "demo-scheduled",
            "rule_type": "require_calculation",
            "config": {"calculation": "frylow-savings", "must_be_complete": True},
            "error_message": "Calculations must be complete before scheduling demo"
        },
        {
            "pipeline": "hot-leads",
            "from_stage": "demo-scheduled",
            "to_stage": "demo-completed",
            "rule_type": "require_action",
            "config": {"action_type": "demo_completed"},
            "error_message": "Demo must be marked as completed"
        },
        {
            "pipeline": "hot-leads",
            "from_stage": None,  # Any stage
            "to_stage": "verbal-commitment",
            "rule_type": "require_action",
            "config": {"action_type": "demo_completed"},
            "error_message": "Demo must be completed before verbal commitment"
        },
        {
            "pipeline": "hot-leads",
            "from_stage": None,
            "to_stage": None,  # Any stage movement
            "rule_type": "calculation_change_return",
            "config": {
                "calculation": "frylow-savings",
                "return_to_stage": "calculations-in-progress",
                "trigger_fields": ["number_of_fryers", "fryer_capacities", "quantity_per_month", "cost_per_unit"]
            },
            "error_message": "Calculation inputs changed - returning to Calculations stage"
        }
    ],
    
    # ==================== NO-SHOW RULES ====================
    "no_show_rules": [
        {
            "from_stage": "demo-scheduled",
            "return_to_pipeline": "qualifying",
            "return_to_stage": "working",
            "action": "log_no_show",
            "notification": True
        }
    ],
    
    # ==================== FORMS ====================
    "forms": [
        {
            "name": "Frylow Lead Capture",
            "slug": "frylow-lead-capture",
            "description": "Capture new leads with basic info and fryer details",
            "fields": [
                {"name": "first_name", "type": "text", "label": "First Name", "required": True, "mapping": "contact.first_name"},
                {"name": "last_name", "type": "text", "label": "Last Name", "required": True, "mapping": "contact.last_name"},
                {"name": "email", "type": "email", "label": "Email", "required": True, "mapping": "contact.email"},
                {"name": "phone", "type": "phone", "label": "Phone", "required": True, "mapping": "contact.phone"},
                {"name": "company_name", "type": "text", "label": "Restaurant/Company Name", "required": True, "mapping": "contact.company_name"},
                {"name": "number_of_fryers", "type": "number", "label": "Number of Fryers", "required": False, "mapping": "deal.calculation.number_of_fryers"}
            ],
            "create_contact": True,
            "create_deal": True,
            "assign_pipeline": "qualifying",
            "assign_stage": "new-assigned",
            "success_message": "Thank you! A Frylow specialist will contact you shortly."
        }
    ],
    
    # ==================== WORKFLOW AUTOMATIONS ====================
    "automations": [
        {
            "name": "New Lead Welcome SMS",
            "trigger": {"type": "stage_entered", "stage": "new-assigned"},
            "actions": [
                {"type": "send_sms", "template": "frylow_welcome", "delay_minutes": 0}
            ],
            "is_active": True
        },
        {
            "name": "Demo Reminder",
            "trigger": {"type": "demo_scheduled"},
            "actions": [
                {"type": "send_email", "template": "demo_confirmation", "delay_minutes": 0},
                {"type": "send_sms", "template": "demo_reminder", "delay_hours": -24}  # 24h before
            ],
            "is_active": True
        },
        {
            "name": "No-Show Follow-up",
            "trigger": {"type": "no_show"},
            "actions": [
                {"type": "move_stage", "pipeline": "qualifying", "stage": "working"},
                {"type": "send_sms", "template": "no_show_followup", "delay_minutes": 30},
                {"type": "internal_notification", "message": "Demo no-show - returned to Working"}
            ],
            "is_active": True
        },
        {
            "name": "Calculation Complete Notification",
            "trigger": {"type": "calculation_completed", "calculation": "frylow-savings"},
            "actions": [
                {"type": "internal_notification", "message": "ROI calculation complete - ready for demo scheduling"}
            ],
            "is_active": True
        }
    ],
    
    # ==================== PROPERTIES ====================
    "custom_properties": {
        "contact": [
            {"name": "restaurant_type", "type": "select", "label": "Restaurant Type", 
             "options": ["Fast Food", "Casual Dining", "Fine Dining", "Food Truck", "Catering", "Other"]},
            {"name": "existing_oil_brand", "type": "text", "label": "Current Oil Brand"},
            {"name": "fry_frequency", "type": "select", "label": "Frying Frequency",
             "options": ["Multiple times daily", "Once daily", "Few times weekly", "Occasionally"]}
        ],
        "deal": [
            {"name": "lead_temperature", "type": "select", "label": "Lead Temperature",
             "options": ["Hot", "Warm", "Cold"]},
            {"name": "competitor_interest", "type": "text", "label": "Competitor Interest"},
            {"name": "decision_timeline", "type": "select", "label": "Decision Timeline",
             "options": ["Immediate", "1-2 weeks", "1 month", "3+ months", "Unknown"]}
        ]
    },
    
    # ==================== KPIs ====================
    "kpis": [
        {"name": "Lead Response Time", "type": "time_to_stage", "from": "new-assigned", "to": "working", "target_hours": 24},
        {"name": "Qualification Rate", "type": "conversion", "from": "new-assigned", "to": "qualified", "target_percent": 25},
        {"name": "Demo Show Rate", "type": "conversion", "from": "demo-scheduled", "to": "demo-completed", "target_percent": 80},
        {"name": "Close Rate", "type": "conversion", "from": "qualified", "to": "closed-won", "target_percent": 30},
        {"name": "Average Deal Size", "type": "average", "field": "deal.amount", "target": 5000}
    ]
}


# Blank CRM Blueprint (for custom builds)
BLANK_BLUEPRINT = {
    "name": "Blank CRM",
    "slug": "blank",
    "description": "Start from scratch with an empty CRM workspace",
    "version": 1,
    "icon": "square",
    "color": "#6B7280",
    "pipelines": [
        {
            "name": "Default Pipeline",
            "slug": "default",
            "description": "Basic sales pipeline",
            "is_default": True,
            "display_order": 0,
            "stages": [
                {"name": "New", "slug": "new", "display_order": 0, "probability": 10, "color": "#6366F1"},
                {"name": "Contacted", "slug": "contacted", "display_order": 1, "probability": 25, "color": "#8B5CF6"},
                {"name": "Qualified", "slug": "qualified", "display_order": 2, "probability": 50, "color": "#A855F7"},
                {"name": "Proposal", "slug": "proposal", "display_order": 3, "probability": 75, "color": "#D946EF"},
                {"name": "Won", "slug": "won", "display_order": 4, "probability": 100, "color": "#10B981", "is_won_stage": True},
                {"name": "Lost", "slug": "lost", "display_order": 5, "probability": 0, "color": "#EF4444", "is_lost_stage": True}
            ]
        }
    ],
    "calculations": [],
    "transition_rules": [],
    "forms": [],
    "automations": [],
    "custom_properties": {"contact": [], "deal": []},
    "kpis": []
}


# NLA Accounting CRM Blueprint
NLA_ACCOUNTING_BLUEPRINT = {
    "name": "NLA Accounting CRM",
    "slug": "nla-accounting",
    "description": "Complete CRM for accounting firms with tax filing workflow and client management",
    "version": 1,
    "icon": "calculator",
    "color": "#3B82F6",
    
    # ==================== PIPELINES ====================
    "pipelines": [
        {
            "name": "Tax Filing Pipeline",
            "slug": "tax-filing",
            "description": "15-step tax filing workflow from intake to final review",
            "is_default": True,
            "display_order": 0,
            "stages": [
                {
                    "name": "New Client Intake",
                    "slug": "intake",
                    "description": "Initial client registration and document request",
                    "display_order": 0,
                    "probability": 5,
                    "color": "#6366F1",
                    "rules": {
                        "require_client_info": True,
                        "send_welcome_packet": True
                    }
                },
                {
                    "name": "Documents Requested",
                    "slug": "docs-requested",
                    "description": "Tax documents requested from client",
                    "display_order": 1,
                    "probability": 10,
                    "color": "#818CF8",
                    "rules": {
                        "send_document_checklist": True,
                        "reminder_days": [3, 7, 14]
                    }
                },
                {
                    "name": "Documents Received",
                    "slug": "docs-received",
                    "description": "All required documents collected",
                    "display_order": 2,
                    "probability": 20,
                    "color": "#8B5CF6",
                    "rules": {
                        "require_document_checklist_complete": True
                    }
                },
                {
                    "name": "Initial Review",
                    "slug": "initial-review",
                    "description": "Preliminary review of documents",
                    "display_order": 3,
                    "probability": 25,
                    "color": "#A855F7",
                    "rules": {
                        "assign_reviewer": True
                    }
                },
                {
                    "name": "Data Entry",
                    "slug": "data-entry",
                    "description": "Entering data into tax software",
                    "display_order": 4,
                    "probability": 30,
                    "color": "#C084FC"
                },
                {
                    "name": "Calculation Review",
                    "slug": "calc-review",
                    "description": "Reviewing calculated tax amounts",
                    "display_order": 5,
                    "probability": 40,
                    "color": "#D946EF",
                    "rules": {
                        "require_calculation_verification": True
                    }
                },
                {
                    "name": "Manager Review",
                    "slug": "manager-review",
                    "description": "Senior review of tax return",
                    "display_order": 6,
                    "probability": 50,
                    "color": "#E879F9",
                    "rules": {
                        "require_manager_role": True
                    }
                },
                {
                    "name": "Corrections Needed",
                    "slug": "corrections",
                    "description": "Issues found requiring correction",
                    "display_order": 7,
                    "probability": 35,
                    "color": "#F59E0B",
                    "rules": {
                        "is_return_stage": True
                    }
                },
                {
                    "name": "Ready for Client Review",
                    "slug": "client-review",
                    "description": "Tax return ready for client approval",
                    "display_order": 8,
                    "probability": 60,
                    "color": "#F97316"
                },
                {
                    "name": "Client Reviewing",
                    "slug": "client-reviewing",
                    "description": "Awaiting client feedback",
                    "display_order": 9,
                    "probability": 65,
                    "color": "#FB923C",
                    "rules": {
                        "reminder_days": [2, 5]
                    }
                },
                {
                    "name": "Client Approved",
                    "slug": "client-approved",
                    "description": "Client signed off on return",
                    "display_order": 10,
                    "probability": 75,
                    "color": "#22C55E",
                    "rules": {
                        "require_e_signature": True
                    }
                },
                {
                    "name": "Payment Pending",
                    "slug": "payment-pending",
                    "description": "Awaiting payment for services",
                    "display_order": 11,
                    "probability": 80,
                    "color": "#10B981",
                    "rules": {
                        "send_invoice": True
                    }
                },
                {
                    "name": "Ready to File",
                    "slug": "ready-to-file",
                    "description": "All requirements met, ready for filing",
                    "display_order": 12,
                    "probability": 90,
                    "color": "#14B8A6",
                    "rules": {
                        "require_payment_or_arrangement": True
                    }
                },
                {
                    "name": "Filed",
                    "slug": "filed",
                    "description": "Tax return submitted",
                    "display_order": 13,
                    "probability": 95,
                    "color": "#06B6D4",
                    "rules": {
                        "require_confirmation_number": True
                    }
                },
                {
                    "name": "Completed",
                    "slug": "completed",
                    "description": "All tax filing work completed",
                    "display_order": 14,
                    "probability": 100,
                    "color": "#10B981",
                    "is_won_stage": True,
                    "rules": {
                        "archive_documents": True
                    }
                }
            ]
        },
        {
            "name": "Client Acquisition",
            "slug": "acquisition",
            "description": "New client acquisition pipeline",
            "is_default": False,
            "display_order": 1,
            "stages": [
                {"name": "Lead", "slug": "lead", "display_order": 0, "probability": 10, "color": "#6366F1"},
                {"name": "Contacted", "slug": "contacted", "display_order": 1, "probability": 20, "color": "#8B5CF6"},
                {"name": "Meeting Scheduled", "slug": "meeting", "display_order": 2, "probability": 40, "color": "#A855F7"},
                {"name": "Proposal Sent", "slug": "proposal", "display_order": 3, "probability": 60, "color": "#D946EF"},
                {"name": "Negotiation", "slug": "negotiation", "display_order": 4, "probability": 75, "color": "#EC4899"},
                {"name": "Won - New Client", "slug": "won", "display_order": 5, "probability": 100, "color": "#10B981", "is_won_stage": True},
                {"name": "Lost", "slug": "lost", "display_order": 6, "probability": 0, "color": "#EF4444", "is_lost_stage": True}
            ]
        }
    ],
    
    # ==================== CALCULATIONS ====================
    "calculations": [
        {
            "name": "Tax Preparation Quote Calculator",
            "slug": "tax-quote",
            "description": "Calculate estimated fees based on tax complexity",
            "version": 1,
            "inputs": [
                {
                    "name": "filing_type",
                    "type": "select",
                    "label": "Filing Type",
                    "required": True,
                    "options": [
                        {"value": "individual", "label": "Individual (1040)"},
                        {"value": "business_sole", "label": "Sole Proprietor (Schedule C)"},
                        {"value": "business_llc", "label": "LLC/Partnership"},
                        {"value": "business_scorp", "label": "S-Corporation"},
                        {"value": "business_ccorp", "label": "C-Corporation"}
                    ]
                },
                {
                    "name": "has_rental_income",
                    "type": "checkbox",
                    "label": "Has Rental Income Properties"
                },
                {
                    "name": "rental_properties",
                    "type": "integer",
                    "label": "Number of Rental Properties",
                    "required": False,
                    "min": 0
                },
                {
                    "name": "has_investments",
                    "type": "checkbox",
                    "label": "Has Investment Income"
                },
                {
                    "name": "state_returns",
                    "type": "integer",
                    "label": "Number of State Returns",
                    "required": True,
                    "min": 0,
                    "max": 10
                }
            ],
            "outputs": [
                {
                    "name": "base_fee",
                    "type": "currency",
                    "label": "Base Preparation Fee",
                    "currency": "USD"
                },
                {
                    "name": "rental_fee",
                    "type": "currency",
                    "label": "Rental Property Fee",
                    "currency": "USD"
                },
                {
                    "name": "state_fee",
                    "type": "currency",
                    "label": "State Return Fees",
                    "currency": "USD"
                },
                {
                    "name": "total_estimate",
                    "type": "currency",
                    "label": "Total Estimated Fee",
                    "currency": "USD"
                }
            ],
            "editable_by_roles": ["admin", "manager", "accountant"]
        }
    ],
    
    # ==================== STAGE TRANSITION RULES ====================
    "transition_rules": [
        {
            "pipeline": "tax-filing",
            "from_stage": "intake",
            "to_stage": "docs-requested",
            "rule_type": "require_contact_info",
            "config": {"fields": ["email", "phone"]},
            "error_message": "Client contact information required before requesting documents"
        },
        {
            "pipeline": "tax-filing",
            "from_stage": "docs-requested",
            "to_stage": "docs-received",
            "rule_type": "require_documents",
            "config": {"min_documents": 1},
            "error_message": "At least one document must be uploaded"
        },
        {
            "pipeline": "tax-filing",
            "from_stage": "client-review",
            "to_stage": "client-approved",
            "rule_type": "require_action",
            "config": {"action_type": "e_signature"},
            "error_message": "Client signature required for approval"
        },
        {
            "pipeline": "tax-filing",
            "from_stage": "client-approved",
            "to_stage": "ready-to-file",
            "rule_type": "require_action",
            "config": {"action_type": "payment_received"},
            "error_message": "Payment must be received or payment arrangement made"
        },
        {
            "pipeline": "tax-filing",
            "from_stage": "ready-to-file",
            "to_stage": "filed",
            "rule_type": "require_field",
            "config": {"field": "confirmation_number"},
            "error_message": "Filing confirmation number required"
        }
    ],
    
    # ==================== FORMS ====================
    "forms": [
        {
            "name": "New Client Registration",
            "slug": "client-registration",
            "description": "Register new tax preparation clients",
            "fields": [
                {"name": "first_name", "type": "text", "label": "First Name", "required": True},
                {"name": "last_name", "type": "text", "label": "Last Name", "required": True},
                {"name": "email", "type": "email", "label": "Email", "required": True},
                {"name": "phone", "type": "phone", "label": "Phone", "required": True},
                {"name": "filing_type", "type": "select", "label": "Filing Type", "required": True,
                 "options": ["Individual", "Business", "Both"]},
                {"name": "referred_by", "type": "text", "label": "Referred By", "required": False}
            ],
            "create_contact": True,
            "create_deal": True,
            "assign_pipeline": "tax-filing",
            "assign_stage": "intake",
            "success_message": "Thank you! We'll be in touch shortly to begin your tax preparation."
        }
    ],
    
    # ==================== WORKFLOW AUTOMATIONS ====================
    "automations": [
        {
            "name": "Welcome Email",
            "trigger": {"type": "stage_entered", "stage": "intake"},
            "actions": [
                {"type": "send_email", "template": "nla_welcome", "delay_minutes": 0}
            ],
            "is_active": True
        },
        {
            "name": "Document Request",
            "trigger": {"type": "stage_entered", "stage": "docs-requested"},
            "actions": [
                {"type": "send_email", "template": "document_checklist", "delay_minutes": 0}
            ],
            "is_active": True
        },
        {
            "name": "Document Reminder",
            "trigger": {"type": "time_in_stage", "stage": "docs-requested", "days": 7},
            "actions": [
                {"type": "send_email", "template": "document_reminder"}
            ],
            "is_active": True
        },
        {
            "name": "Review Ready Notification",
            "trigger": {"type": "stage_entered", "stage": "client-review"},
            "actions": [
                {"type": "send_email", "template": "review_ready"},
                {"type": "send_sms", "template": "review_notification"}
            ],
            "is_active": True
        }
    ],
    
    # ==================== CUSTOM PROPERTIES ====================
    "custom_properties": {
        "contact": [
            {"name": "ssn_last_four", "type": "text", "label": "SSN (Last 4)", "encrypted": True},
            {"name": "filing_status", "type": "select", "label": "Filing Status",
             "options": ["Single", "Married Filing Jointly", "Married Filing Separately", "Head of Household"]},
            {"name": "occupation", "type": "text", "label": "Occupation"},
            {"name": "employer", "type": "text", "label": "Employer"},
            {"name": "prior_year_client", "type": "checkbox", "label": "Returning Client"}
        ],
        "deal": [
            {"name": "tax_year", "type": "select", "label": "Tax Year",
             "options": ["2024", "2023", "2022", "2021"]},
            {"name": "complexity_level", "type": "select", "label": "Complexity",
             "options": ["Simple", "Moderate", "Complex", "Very Complex"]},
            {"name": "estimated_refund", "type": "currency", "label": "Estimated Refund"},
            {"name": "balance_due", "type": "currency", "label": "Balance Due"},
            {"name": "assigned_preparer", "type": "user", "label": "Assigned Preparer"},
            {"name": "assigned_reviewer", "type": "user", "label": "Assigned Reviewer"}
        ]
    },
    
    # ==================== KPIs ====================
    "kpis": [
        {"name": "Document Turnaround", "type": "time_to_stage", "from": "docs-requested", "to": "docs-received", "target_days": 7},
        {"name": "Preparation Time", "type": "time_to_stage", "from": "docs-received", "to": "client-review", "target_days": 5},
        {"name": "Client Approval Rate", "type": "conversion", "from": "client-review", "to": "client-approved", "target_percent": 95},
        {"name": "Filing Completion Rate", "type": "conversion", "from": "intake", "to": "completed", "target_percent": 90},
        {"name": "Average Revenue per Client", "type": "average", "field": "deal.amount", "target": 500}
    ]
}


def get_blueprint_json(slug: str) -> dict:
    """Get blueprint configuration by slug"""
    blueprints = {
        "frylow-sales": FRYLOW_BLUEPRINT,
        "nla-accounting": NLA_ACCOUNTING_BLUEPRINT,
        "blank": BLANK_BLUEPRINT
    }
    return blueprints.get(slug, BLANK_BLUEPRINT)


def get_all_blueprints() -> list:
    """Get all available blueprints"""
    return [
        {"slug": "frylow-sales", "name": "Frylow Sales CRM", "is_default": True, "config": FRYLOW_BLUEPRINT},
        {"slug": "nla-accounting", "name": "NLA Accounting CRM", "is_default": False, "config": NLA_ACCOUNTING_BLUEPRINT},
        {"slug": "blank", "name": "Blank CRM", "is_default": False, "config": BLANK_BLUEPRINT}
    ]
