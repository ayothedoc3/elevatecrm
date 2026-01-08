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
  Flame, Bell, Search, Menu, Plus, Sun, Moon, Box, BarChart3, Activity, UserPlus, LayoutTemplate, Building2, TrendingUp
} from 'lucide-react';

import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ContactsPage from './pages/ContactsPage';
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
import PublicLandingPage from './pages/PublicLandingPage';
import SettingsPage from './pages/SettingsPage';
import LeadsPage from './pages/LeadsPage';
import PartnersPage from './pages/PartnersPage';
import KPIDashboardPage from './pages/KPIDashboardPage';
import TasksPage from './pages/TasksPage';
import HandoffPage from './pages/HandoffPage';
import PartnerConfigPage from './pages/PartnerConfigPage';
import AffiliateLoginPage from './pages/AffiliatePortal/AffiliateLoginPage';
import AffiliateDashboard from './pages/AffiliatePortal/AffiliateDashboard';
import WorkspaceSwitcher from './components/WorkspaceSwitcher';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/leads', icon: UserPlus, label: 'Leads' },
  { path: '/contacts', icon: Users, label: 'Contacts' },
  { path: '/pipeline', icon: Target, label: 'Pipeline' },
  { path: '/partners', icon: Building2, label: 'Partners' },
  { path: '/kpis', icon: TrendingUp, label: 'KPIs & Forecast' },
  { path: '/activity', icon: Activity, label: 'Activity' },
  { path: '/reports', icon: BarChart3, label: 'Reports' },
  { path: '/affiliates', icon: UserPlus, label: 'Affiliates' },
  { path: '/landing-pages', icon: LayoutTemplate, label: 'AI Page Builder' },
  { path: '/inbox', icon: MessageSquare, label: 'Inbox' },
  { path: '/workflows', icon: GitBranch, label: 'Workflows' },
  { path: '/forms', icon: FileText, label: 'Forms' },
  { path: '/custom-objects', icon: Box, label: 'Objects' },
  { path: '/blueprints', icon: GitBranch, label: 'Blueprints' },
  { path: '/settings', icon: Settings, label: 'Settings', bottom: true },
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
          {navItems.filter(item => !item.bottom).map(item => {
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
          {navItems.filter(item => item.bottom).map(item => {
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
  const { user } = useAuth();
  const { theme, toggleTheme, isDark } = useTheme();
  
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
        
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </Button>
        
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
      <Route path="/pipeline" element={<ProtectedRoute><PipelinePage /></ProtectedRoute>} />
      <Route path="/blueprints" element={<ProtectedRoute><BlueprintPage /></ProtectedRoute>} />
      <Route path="/inbox" element={<ProtectedRoute><InboxPage /></ProtectedRoute>} />
      <Route path="/workflows" element={<ProtectedRoute><WorkflowsPage /></ProtectedRoute>} />
      <Route path="/forms" element={<ProtectedRoute><FormsPage /></ProtectedRoute>} />
      <Route path="/custom-objects" element={<ProtectedRoute><CustomObjectsPage /></ProtectedRoute>} />
      <Route path="/activity" element={<ProtectedRoute><ActivityPage /></ProtectedRoute>} />
      <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
      <Route path="/affiliates" element={<ProtectedRoute><AffiliatesPage /></ProtectedRoute>} />
      <Route path="/landing-pages" element={<ProtectedRoute><LandingPagesPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="/leads" element={<ProtectedRoute><LeadsPage /></ProtectedRoute>} />
      <Route path="/partners" element={<ProtectedRoute><PartnersPage /></ProtectedRoute>} />
      <Route path="/kpis" element={<ProtectedRoute><KPIDashboardPage /></ProtectedRoute>} />
      {/* Affiliate Portal Routes - No Auth Required */}
      <Route path="/affiliate-portal/login" element={<AffiliateLoginPage />} />
      <Route path="/affiliate-portal/dashboard" element={<AffiliateDashboard />} />
      <Route path="/affiliate-portal" element={<Navigate to="/affiliate-portal/login" replace />} />
      {/* Public Landing Pages - No Auth Required */}
      <Route path="/pages/:slug" element={<PublicLandingPage />} />
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
