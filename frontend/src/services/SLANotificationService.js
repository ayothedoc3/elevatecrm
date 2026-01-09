/**
 * SLA Notification Service
 * Provides real-time notifications for SLA breaches and overdue tasks
 */

import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

class SLANotificationService {
  constructor() {
    this.checkInterval = null;
    this.lastChecked = null;
    this.notifiedBreaches = new Set();
    this.notifiedOverdue = new Set();
  }

  getAuthHeaders() {
    const token = localStorage.getItem('crm_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  async checkSLABreaches() {
    try {
      const response = await fetch(`${API_URL}/api/elev8/sla/status?entity_type=deals`, {
        headers: this.getAuthHeaders()
      });

      if (!response.ok) return;

      const data = await response.json();

      // Notify for newly breached items
      if (data.breached_items) {
        data.breached_items.forEach(item => {
          const key = `breach-${item.id || item.name}`;
          if (!this.notifiedBreaches.has(key)) {
            this.notifiedBreaches.add(key);
            toast.error(`SLA Breached: ${item.name}`, {
              description: `${item.hours_since_activity}h since last activity (+${item.breach_hours}h over SLA)`,
              duration: 10000,
              action: {
                label: 'View',
                onClick: () => window.location.href = '/tasks'
              }
            });
          }
        });
      }

      // Notify for items at risk (approaching breach)
      if (data.at_risk_items) {
        data.at_risk_items.forEach(item => {
          const key = `risk-${item.id || item.name}`;
          if (!this.notifiedBreaches.has(key) && item.hours_to_breach <= 4) {
            this.notifiedBreaches.add(key);
            toast.warning(`SLA Warning: ${item.name}`, {
              description: `Only ${item.hours_to_breach}h remaining before SLA breach`,
              duration: 8000,
              action: {
                label: 'View',
                onClick: () => window.location.href = '/tasks'
              }
            });
          }
        });
      }
    } catch (error) {
      console.error('Error checking SLA breaches:', error);
    }
  }

  async checkOverdueTasks() {
    try {
      const response = await fetch(`${API_URL}/api/elev8/tasks/my-tasks`, {
        headers: this.getAuthHeaders()
      });

      if (!response.ok) return;

      const data = await response.json();

      // Notify for newly overdue tasks
      if (data.overdue) {
        data.overdue.forEach(task => {
          const key = `overdue-${task.id}`;
          if (!this.notifiedOverdue.has(key)) {
            this.notifiedOverdue.add(key);
            toast.error(`Task Overdue: ${task.title}`, {
              description: task.deal_name || task.lead_name || 'Action required',
              duration: 8000,
              action: {
                label: 'View',
                onClick: () => window.location.href = '/tasks'
              }
            });
          }
        });
      }

      // Notify for tasks due today that are high priority
      if (data.due_today) {
        data.due_today.forEach(task => {
          if (task.priority === 'urgent' || task.priority === 'high') {
            const key = `today-${task.id}`;
            if (!this.notifiedOverdue.has(key)) {
              this.notifiedOverdue.add(key);
              toast.info(`${task.priority === 'urgent' ? '🚨' : '⚠️'} Due Today: ${task.title}`, {
                description: task.deal_name || task.lead_name || 'Due today',
                duration: 6000,
                action: {
                  label: 'View',
                  onClick: () => window.location.href = '/tasks'
                }
              });
            }
          }
        });
      }
    } catch (error) {
      console.error('Error checking overdue tasks:', error);
    }
  }

  start(intervalMinutes = 5) {
    // Initial check after 5 seconds
    setTimeout(() => {
      this.checkSLABreaches();
      this.checkOverdueTasks();
    }, 5000);

    // Regular checks
    this.checkInterval = setInterval(() => {
      this.checkSLABreaches();
      this.checkOverdueTasks();
    }, intervalMinutes * 60 * 1000);
  }

  stop() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  // Clear notification cache (useful when user takes action)
  clearCache() {
    this.notifiedBreaches.clear();
    this.notifiedOverdue.clear();
  }
}

// Export singleton instance
export const slaNotificationService = new SLANotificationService();

// Hook for React components
export const useSLANotifications = () => {
  return {
    start: () => slaNotificationService.start(),
    stop: () => slaNotificationService.stop(),
    clearCache: () => slaNotificationService.clearCache(),
    checkNow: async () => {
      await slaNotificationService.checkSLABreaches();
      await slaNotificationService.checkOverdueTasks();
    }
  };
};

export default SLANotificationService;
