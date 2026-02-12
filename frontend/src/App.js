import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { Toaster } from './components/ui/sonner';
import { Button } from './components/ui/button';
import { Avatar, AvatarFallback } from './components/ui/avatar';
import { Badge } from './components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './components/ui/tooltip';
import {
  LayoutDashboard, Users, Target, GitBranch, MessageSquare,
  FileText, Settings, LogOut, ChevronLeft, ChevronRight,
  Flame, Bell, Search, Menu, Plus, Sun, Moon, Box, BarChart3, Activity, UserPlus, LayoutTemplate, List, Mail
} from 'lucide-react';

import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ContactsPage from './pages/ContactsPage';
import LeadsPage from './pages/LeadsPage';
import PipelinePage from './pages/PipelinePage';
import BlueprintPage from './pages/BlueprintPage';
import InboxPage from './pages/InboxPage';
import WorkflowsPage from './pages/WorkflowsPage';
import FormsPage from './pages/FormsPage';
import CustomObjectsPage from './pages/CustomObjectsPage';
import ActivityPage from './pages/ActivityPage';
import ReportsPage from './pages/ReportsPage';
import AffiliatesPage from './pages/AffiliatesPage';
import LandingPagesPage from './pages/LandingPagesPage';
import PageBuilderPage from './pages/PageBuilderPage';
import ListsPage from './pages/ListsPage';
import CampaignsPage from './pages/CampaignsPage';
import PublicLandingPage from './pages/PublicLandingPage';
import ComingSoonPage from './pages/ComingSoonPage';
import SettingsPage from './pages/SettingsPage';
import AffiliateLoginPage from './pages/AffiliatePortal/AffiliateLoginPage';
import AffiliateDashboard from './pages/AffiliatePortal/AffiliateDashboard';
import WorkspaceSwitcher from './components/WorkspaceSwitcher';

const APP_PHASE = Number.parseInt(process.env.REACT_APP_APP_PHASE || '1', 10) || 1;
const isFeatureEnabled = (minPhase = 1) => APP_PHASE >= minPhase;

const navItems = [
  // Phase 1 core (go-live for Sales)
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', minPhase: 1 },
  { path: '/contacts', icon: Users, label: 'Contacts', minPhase: 1 },
  { path: '/leads', icon: Target, label: 'Leads', minPhase: 1 },
  { path: '/pipeline', icon: GitBranch, label: 'Pipeline', minPhase: 1 },
  { path: '/activity', icon: Activity, label: 'Activity', minPhase: 1 },
  { path: '/reports', icon: BarChart3, label: 'Reports', minPhase: 1 },

  // Phase 2+ (execution layer / additional modules; enable once backend supports Postgres for these)
  { path: '/affiliates', icon: UserPlus, label: 'Affiliates', minPhase: 2 },
  { path: '/landing-pages', icon: LayoutTemplate, label: 'AI Page Builder', minPhase: 2 },
  { path: '/lists', icon: List, label: 'Lists', minPhase: 2 },
  { path: '/campaigns', icon: Mail, label: 'Campaigns', minPhase: 2 },
  { path: '/inbox', icon: MessageSquare, label: 'Inbox', minPhase: 2 },
  { path: '/workflows', icon: GitBranch, label: 'Workflows', minPhase: 2 },
  { path: '/forms', icon: FileText, label: 'Forms', minPhase: 3 },
  { path: '/custom-objects', icon: Box, label: 'Objects', minPhase: 2 },
  { path: '/blueprints', icon: GitBranch, label: 'Blueprints', minPhase: 2 },
  { path: '/settings', icon: Settings, label: 'Settings', bottom: true, minPhase: 2 },
];

const Sidebar = ({ collapsed, setCollapsed }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { isDark } = useTheme();

  return (
    <div 
      className={`h-screen border-r flex flex-col transition-all duration-300 ${
        collapsed ? 'w-[70px]' : 'w-[240px]'
      } ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-slate-50 border-slate-200'}`}
    >
      {/* Logo */}
      <div className={`p-4 border-b ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-600 rounded-xl flex items-center justify-center flex-shrink-0">
            <Flame className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div>
              <h1 className={`font-bold ${isDark ? 'text-white' : 'text-slate-900'}`}>Elevate CRM</h1>
              <p className="text-xs text-slate-500">Multi-CRM Platform</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <TooltipProvider>
          {navItems.filter(item => !item.bottom && isFeatureEnabled(item.minPhase)).map(item => {
            const isActive = location.pathname === item.path;
            return (
              <Tooltip key={item.path} delayDuration={0}>
                <TooltipTrigger asChild>
                  <Button
                    variant={isActive ? 'secondary' : 'ghost'}
                    className={`w-full justify-start gap-3 ${
                      isActive 
                        ? isDark ? 'bg-slate-800 text-white' : 'bg-slate-200 text-slate-900'
                        : isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800/50' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
                    } ${collapsed ? 'px-3' : ''}`}
                    onClick={() => navigate(item.path)}
                  >
                    <item.icon className="w-5 h-5 flex-shrink-0" />
                    {!collapsed && <span>{item.label}</span>}
                  </Button>
                </TooltipTrigger>
                {collapsed && (
                  <TooltipContent side="right">
                    {item.label}
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}
        </TooltipProvider>
      </nav>

      {/* Settings at bottom */}
      <div className={`p-3 border-t ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        <TooltipProvider>
          {navItems.filter(item => item.bottom && isFeatureEnabled(item.minPhase)).map(item => {
            const isActive = location.pathname === item.path;
            return (
              <Tooltip key={item.path} delayDuration={0}>
                <TooltipTrigger asChild>
                  <Button
                    variant={isActive ? 'secondary' : 'ghost'}
                    className={`w-full justify-start gap-3 ${
                      isActive 
                        ? isDark ? 'bg-slate-800 text-white' : 'bg-slate-200 text-slate-900'
                        : isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800/50' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
                    } ${collapsed ? 'px-3' : ''}`}
                    onClick={() => navigate(item.path)}
                  >
                    <item.icon className="w-5 h-5 flex-shrink-0" />
                    {!collapsed && <span>{item.label}</span>}
                  </Button>
                </TooltipTrigger>
                {collapsed && (
                  <TooltipContent side="right">
                    {item.label}
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}
        </TooltipProvider>
      </div>

      {/* Collapse Button */}
      <div className={`p-3 border-t ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        <Button
          variant="ghost"
          size="sm"
          className={`w-full ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && <span className="ml-2">Collapse</span>}
        </Button>
      </div>

      {/* User */}
      <div className={`p-3 border-t ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className={`w-full justify-start gap-3 ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
              <Avatar className="w-8 h-8">
                <AvatarFallback className="bg-gradient-to-br from-blue-500 to-violet-600 text-white text-xs">
                  {user?.first_name?.[0]}{user?.last_name?.[0]}
                </AvatarFallback>
              </Avatar>
              {!collapsed && (
                <div className="text-left flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user?.first_name} {user?.last_name}</p>
                  <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                </div>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div>
                <p>{user?.first_name} {user?.last_name}</p>
                <p className="text-xs text-muted-foreground font-normal">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Badge variant="outline" className="mr-2">{user?.role}</Badge>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-red-500">
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
};

const TopBar = () => {
  const { user, api } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  const navigate = useNavigate();

  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [recentEvents, setRecentEvents] = useState([]);
  const [overdueTasks, setOverdueTasks] = useState([]);

  const refreshNotifications = async () => {
    setNotificationsLoading(true);
    try {
      const nowIso = new Date().toISOString();
      const [eventsRes, tasksRes] = await Promise.all([
        api.get('/timeline?page=1&page_size=5'),
        api.get(`/tasks?status=open&page=1&page_size=5&due_before=${encodeURIComponent(nowIso)}`)
      ]);
      setRecentEvents(eventsRes.data?.events || []);
      setOverdueTasks(tasksRes.data?.tasks || []);
    } catch (error) {
      console.error('Error loading notifications:', error);
      setRecentEvents([]);
      setOverdueTasks([]);
    } finally {
      setNotificationsLoading(false);
    }
  };

  const formatRelative = (isoString) => {
    if (!isoString) return '';
    const dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) return '';
    const diffMs = Date.now() - dt.getTime();
    const mins = Math.floor(Math.abs(diffMs) / 60000);
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  };
  
  return (
    <div className="h-16 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {/* Workspace Switcher */}
        <WorkspaceSwitcher />
        
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="w-64 h-9 pl-10 pr-4 rounded-lg bg-muted/50 border border-transparent focus:border-primary focus:outline-none text-sm"
          />
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={toggleTheme}
              className="relative"
            >
              {isDark ? (
                <Sun className="w-5 h-5 text-yellow-500" />
              ) : (
                <Moon className="w-5 h-5 text-slate-700" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            Switch to {isDark ? 'light' : 'dark'} mode
          </TooltipContent>
        </Tooltip>
        
        <DropdownMenu
          open={notificationsOpen}
          onOpenChange={(open) => {
            setNotificationsOpen(open);
            if (open) refreshNotifications();
          }}
        >
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
              <Bell className="w-5 h-5" />
              {overdueTasks.length > 0 && (
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Notifications</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.preventDefault();
                  refreshNotifications();
                }}
              >
                Refresh
              </Button>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />

            {notificationsLoading ? (
              <div className="px-2 py-2 text-sm text-muted-foreground">Loading…</div>
            ) : (
              <>
                {overdueTasks.length > 0 && (
                  <>
                    <DropdownMenuLabel className="text-xs text-muted-foreground">Overdue Tasks</DropdownMenuLabel>
                    {overdueTasks.map((t) => (
                      <DropdownMenuItem
                        key={t.id}
                        onSelect={(e) => {
                          e.preventDefault();
                          navigate('/pipeline');
                          setNotificationsOpen(false);
                        }}
                        className="flex flex-col items-start gap-0.5"
                      >
                        <span className="font-medium">{t.title}</span>
                        <span className="text-xs text-muted-foreground">
                          Due {t.due_at ? `${formatRelative(t.due_at)} ago` : '—'}
                        </span>
                      </DropdownMenuItem>
                    ))}
                    <DropdownMenuSeparator />
                  </>
                )}

                <DropdownMenuLabel className="text-xs text-muted-foreground">Recent Activity</DropdownMenuLabel>
                {recentEvents.length === 0 ? (
                  <div className="px-2 py-2 text-sm text-muted-foreground">No recent activity</div>
                ) : (
                  recentEvents.map((e) => (
                    <DropdownMenuItem
                      key={e.id}
                      onSelect={(ev) => {
                        ev.preventDefault();
                        navigate('/activity');
                        setNotificationsOpen(false);
                      }}
                      className="flex flex-col items-start gap-0.5"
                    >
                      <span className="font-medium">{e.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {e.created_at ? `${formatRelative(e.created_at)} ago` : ''}
                      </span>
                    </DropdownMenuItem>
                  ))
                )}
              </>
            )}

            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={(e) => {
                e.preventDefault();
                navigate('/activity');
                setNotificationsOpen(false);
              }}
            >
              View activity
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        
        <div className="text-right ml-2">
          <p className="text-sm font-medium">{user?.first_name} {user?.last_name}</p>
          <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
        </div>
      </div>
    </div>
  );
};

const MainLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  
  return (
    <div className="flex h-screen bg-background">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return <MainLayout>{children}</MainLayout>;
};

const AppRoutes = () => {
  const { user, loading } = useAuth();
  const gate = (minPhase, enabledEl, title, description) => (
    isFeatureEnabled(minPhase)
      ? enabledEl
      : <ComingSoonPage title={title} description={description} />
  );
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }
  
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/contacts" element={<ProtectedRoute><ContactsPage /></ProtectedRoute>} />
      <Route path="/leads" element={<ProtectedRoute><LeadsPage /></ProtectedRoute>} />
      <Route path="/pipeline" element={<ProtectedRoute><PipelinePage /></ProtectedRoute>} />
      <Route path="/activity" element={<ProtectedRoute><ActivityPage /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />

      <Route path="/blueprints" element={<ProtectedRoute>{gate(2, <BlueprintPage />, 'Blueprints')}</ProtectedRoute>} />
      <Route path="/inbox" element={<ProtectedRoute>{gate(2, <InboxPage />, 'Inbox')}</ProtectedRoute>} />
      <Route path="/workflows" element={<ProtectedRoute>{gate(2, <WorkflowsPage />, 'Workflows')}</ProtectedRoute>} />
      <Route path="/forms" element={<ProtectedRoute>{gate(3, <FormsPage />, 'Forms')}</ProtectedRoute>} />
      <Route path="/custom-objects" element={<ProtectedRoute>{gate(2, <CustomObjectsPage />, 'Objects')}</ProtectedRoute>} />
      <Route path="/affiliates" element={<ProtectedRoute>{gate(2, <AffiliatesPage />, 'Affiliates')}</ProtectedRoute>} />
      <Route path="/landing-pages/builder/:pageId" element={<ProtectedRoute>{gate(2, <PageBuilderPage />, 'Landing Pages')}</ProtectedRoute>} />
      <Route path="/landing-pages/builder" element={<ProtectedRoute>{gate(2, <PageBuilderPage />, 'Landing Pages')}</ProtectedRoute>} />
      <Route path="/landing-pages" element={<ProtectedRoute>{gate(2, <LandingPagesPage />, 'Landing Pages')}</ProtectedRoute>} />
      <Route path="/lists" element={<ProtectedRoute>{gate(2, <ListsPage />, 'Lists')}</ProtectedRoute>} />
      <Route path="/campaigns" element={<ProtectedRoute>{gate(2, <CampaignsPage />, 'Campaigns')}</ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute>{gate(2, <SettingsPage />, 'Settings')}</ProtectedRoute>} />
      {/* Affiliate Portal Routes - No Auth Required */}
      <Route path="/affiliate-portal/login" element={gate(2, <AffiliateLoginPage />, 'Affiliate Portal')} />
      <Route path="/affiliate-portal/dashboard" element={gate(2, <AffiliateDashboard />, 'Affiliate Portal')} />
      <Route path="/affiliate-portal" element={<Navigate to="/affiliate-portal/login" replace />} />
      {/* Public Landing Pages - No Auth Required */}
      <Route path="/pages/:slug" element={gate(2, <PublicLandingPage />, 'Public Landing Pages')} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <TooltipProvider>
            <AppRoutes />
            <Toaster />
          </TooltipProvider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
