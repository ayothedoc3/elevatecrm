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


def get_blueprint_json(slug: str) -> dict:
    """Get blueprint configuration by slug"""
    blueprints = {
        "frylow-sales": FRYLOW_BLUEPRINT,
        "blank": BLANK_BLUEPRINT
    }
    return blueprints.get(slug, BLANK_BLUEPRINT)


def get_all_blueprints() -> list:
    """Get all available blueprints"""
    return [
        {"slug": "frylow-sales", "name": "Frylow Sales CRM", "is_default": True, "config": FRYLOW_BLUEPRINT},
        {"slug": "blank", "name": "Blank CRM", "is_default": False, "config": BLANK_BLUEPRINT}
    ]
