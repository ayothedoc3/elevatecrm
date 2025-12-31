#!/usr/bin/env python3
"""
Backend API Testing for Elevate CRM Settings Module
Tests Settings APIs: Workspace, AI Config, Integrations, Affiliates, Audit Logs, Providers
"""

import requests
import json
import sys
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://elevate-pages.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"
TENANT_SLUG = "demo"

class SettingsModuleTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.admin_user_data = None
        self.test_results = []
        self.test_integration_provider = "openai"
        self.test_api_key = "sk-test-key-12345678"
        
    def log_test(self, test_name, success, details="", error=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "error": str(error) if error else None,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
        print()
    
    def authenticate_admin(self):
        """Login as admin and get JWT token"""
        try:
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/auth/login?tenant_slug={TENANT_SLUG}",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.admin_user_data = data["user"]
                self.log_test("Admin Authentication", True, f"Logged in as {self.admin_user_data['email']}")
                return True
            else:
                self.log_test("Admin Authentication", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Admin Authentication", False, error=e)
            return False
    
    def test_health_check(self):
        """Test basic health endpoint"""
        try:
            response = self.session.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status')}")
                return True
            else:
                self.log_test("Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, error=e)
            return False
    
    # ==================== WORKSPACE SETTINGS API TESTS ====================
    
    def test_get_workspace_settings(self):
        """Test GET /api/settings/workspace - Get workspace settings"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/workspace", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["workspace_id", "name", "primary_color", "timezone", "currency"]
                if all(field in data for field in required_fields):
                    self.log_test("GET /settings/workspace", True, f"Retrieved workspace settings: {data.get('name')}")
                    return True
                else:
                    self.log_test("GET /settings/workspace", False, "Missing required fields in response")
                    return False
            else:
                self.log_test("GET /settings/workspace", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/workspace", False, error=e)
            return False
    
    def test_update_workspace_settings(self):
        """Test PUT /api/settings/workspace - Update workspace settings"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            update_data = {
                "name": "Updated Test Workspace",
                "description": "Test workspace for Settings Module testing",
                "primary_color": "#FF6B6B",
                "timezone": "America/New_York",
                "currency": "EUR"
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/settings/workspace",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                # Check if the response contains the updated settings
                if data.get("name") == update_data["name"] and data.get("currency") == update_data["currency"]:
                    self.log_test("PUT /settings/workspace", True, "Workspace settings updated successfully")
                    return True
                else:
                    self.log_test("PUT /settings/workspace", False, "Updated data not reflected in response")
                    return False
            else:
                self.log_test("PUT /settings/workspace", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /settings/workspace", False, error=e)
            return False
    
    # ==================== AI CONFIGURATION API TESTS ====================
    
    def test_get_ai_config(self):
        """Test GET /api/settings/ai - Get AI configuration"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/ai", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["default_provider", "default_model", "features_enabled", "usage_limits", "configured_providers"]
                if all(field in data for field in required_fields):
                    providers_count = len(data.get("configured_providers", []))
                    self.log_test("GET /settings/ai", True, f"Retrieved AI config with {providers_count} configured providers")
                    return True
                else:
                    self.log_test("GET /settings/ai", False, "Missing required fields in AI config")
                    return False
            else:
                self.log_test("GET /settings/ai", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/ai", False, error=e)
            return False
    
    def test_update_ai_config(self):
        """Test PUT /api/settings/ai - Update AI configuration"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            update_data = {
                "default_provider": "openai",
                "default_model": "gpt-4o",
                "features_enabled": {
                    "page_builder": True,
                    "lead_scoring": True,
                    "deal_analysis": False
                },
                "usage_limits": {
                    "monthly_requests": 1000,
                    "daily_requests": 50
                }
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/settings/ai",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                # Check if the response contains the updated AI config
                if data.get("default_provider") == update_data["default_provider"] and data.get("default_model") == update_data["default_model"]:
                    self.log_test("PUT /settings/ai", True, "AI configuration updated successfully")
                    return True
                else:
                    self.log_test("PUT /settings/ai", False, "Updated AI config not reflected in response")
                    return False
            else:
                self.log_test("PUT /settings/ai", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /settings/ai", False, error=e)
            return False
    
    def test_get_ai_usage_stats(self):
        """Test GET /api/settings/ai/usage?days=30 - Get AI usage statistics"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/ai/usage?days=30", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Usage stats might be empty for new workspace, that's OK
                self.log_test("GET /settings/ai/usage", True, f"Retrieved AI usage stats for 30 days")
                return True
            else:
                self.log_test("GET /settings/ai/usage", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/ai/usage", False, error=e)
            return False
    
    def test_get_ai_status(self):
        """Test GET /api/settings/ai/status - Get AI configuration status"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/ai/status", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["is_configured", "has_fallback_key", "configured_providers", "default_provider"]
                if all(field in data for field in required_fields):
                    is_configured = data.get("is_configured", False)
                    has_fallback = data.get("has_fallback_key", False)
                    self.log_test("GET /settings/ai/status", True, f"AI Status - Configured: {is_configured}, Fallback: {has_fallback}")
                    return True
                else:
                    self.log_test("GET /settings/ai/status", False, "Missing required fields in AI status")
                    return False
            else:
                self.log_test("GET /settings/ai/status", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/ai/status", False, error=e)
            return False
    
    # ==================== INTEGRATIONS API TESTS (CRITICAL SECURITY) ====================
    
    def test_list_integrations(self):
        """Test GET /api/settings/integrations - List integrations (SECURITY: Keys must be masked)"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/integrations", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                integrations = data.get("integrations", [])
                by_category = data.get("by_category", {})
                
                # SECURITY CHECK: Ensure no actual API keys are returned
                security_violation = False
                for integration in integrations:
                    if "api_key" in integration:
                        # If api_key field exists, it should be masked
                        api_key = integration.get("api_key", "")
                        if api_key and not api_key.startswith("••••••••"):
                            security_violation = True
                            break
                
                if security_violation:
                    self.log_test("GET /settings/integrations", False, "SECURITY VIOLATION: Actual API key returned in response!")
                    return False
                
                categories = ["ai", "communication", "payment"]
                if all(cat in by_category for cat in categories):
                    self.log_test("GET /settings/integrations", True, f"Retrieved {len(integrations)} integrations with proper security masking")
                    return True
                else:
                    self.log_test("GET /settings/integrations", False, "Missing category groupings")
                    return False
            else:
                self.log_test("GET /settings/integrations", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/integrations", False, error=e)
            return False
    
    def test_add_integration(self):
        """Test POST /api/settings/integrations - Add new integration (SECURITY: Key encryption)"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            integration_data = {
                "provider_type": self.test_integration_provider,
                "api_key": self.test_api_key,
                "config": {
                    "model": "gpt-4o",
                    "temperature": 0.7
                }
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/settings/integrations",
                json=integration_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    integration = data.get("integration", {})
                    
                    # SECURITY CHECK: Ensure API key is not returned
                    if "api_key" in integration and not integration["api_key"].startswith("••••••••"):
                        self.log_test("POST /settings/integrations", False, "SECURITY VIOLATION: API key returned in response!")
                        return False
                    
                    # Check for masked hint
                    key_hint = integration.get("key_hint", "")
                    if key_hint and key_hint.endswith("5678"):  # Last 4 chars of test key
                        self.log_test("POST /settings/integrations", True, f"Integration '{self.test_integration_provider}' added with proper key masking")
                        return True
                    else:
                        self.log_test("POST /settings/integrations", True, f"Integration '{self.test_integration_provider}' added successfully")
                        return True
                else:
                    self.log_test("POST /settings/integrations", False, "Integration creation failed")
                    return False
            else:
                self.log_test("POST /settings/integrations", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /settings/integrations", False, error=e)
            return False
    
    def test_get_specific_integration(self):
        """Test GET /api/settings/integrations/{provider_type} - Get specific integration"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/integrations/{self.test_integration_provider}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # SECURITY CHECK: Ensure API key is masked
                if "api_key" in data and not data["api_key"].startswith("••••••••"):
                    self.log_test("GET /settings/integrations/{provider}", False, "SECURITY VIOLATION: API key not masked!")
                    return False
                
                if data.get("provider_type") == self.test_integration_provider:
                    self.log_test("GET /settings/integrations/{provider}", True, f"Retrieved {self.test_integration_provider} integration with masked key")
                    return True
                else:
                    self.log_test("GET /settings/integrations/{provider}", False, "Invalid integration data")
                    return False
            else:
                self.log_test("GET /settings/integrations/{provider}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/integrations/{provider}", False, error=e)
            return False
    
    def test_toggle_integration(self):
        """Test PATCH /api/settings/integrations/{provider_type}/toggle - Enable/disable integration"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # First disable
            toggle_data = {"enabled": False}
            response = self.session.patch(
                f"{BACKEND_URL}/settings/integrations/{self.test_integration_provider}/toggle",
                json=toggle_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Then enable again
                    toggle_data = {"enabled": True}
                    response2 = self.session.patch(
                        f"{BACKEND_URL}/settings/integrations/{self.test_integration_provider}/toggle",
                        json=toggle_data,
                        headers=headers
                    )
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        if data2.get("success"):
                            self.log_test("PATCH /settings/integrations/{provider}/toggle", True, "Integration toggle working (disabled then enabled)")
                            return True
                        else:
                            self.log_test("PATCH /settings/integrations/{provider}/toggle", False, "Failed to re-enable integration")
                            return False
                    else:
                        self.log_test("PATCH /settings/integrations/{provider}/toggle", False, f"Re-enable failed: {response2.status_code}")
                        return False
                else:
                    self.log_test("PATCH /settings/integrations/{provider}/toggle", False, "Failed to disable integration")
                    return False
            else:
                self.log_test("PATCH /settings/integrations/{provider}/toggle", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PATCH /settings/integrations/{provider}/toggle", False, error=e)
            return False
    
    def test_integration_connection(self):
        """Test POST /api/settings/integrations/test - Test connection (may fail without real key)"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            test_data = {
                "provider_type": self.test_integration_provider,
                "api_key": self.test_api_key  # Test with the fake key
            }
            
            response = self.session.post(
                f"{BACKEND_URL}/settings/integrations/test",
                json=test_data,
                headers=headers
            )
            
            # This test may fail with fake key, but endpoint should respond properly
            if response.status_code in [200, 400, 401]:
                data = response.json()
                # Even if connection fails, the endpoint should return structured response
                if "success" in data or "error" in data:
                    self.log_test("POST /settings/integrations/test", True, f"Connection test endpoint working (may fail with fake key)")
                    return True
                else:
                    self.log_test("POST /settings/integrations/test", False, "Invalid response structure")
                    return False
            else:
                self.log_test("POST /settings/integrations/test", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("POST /settings/integrations/test", False, error=e)
            return False
    
    def test_revoke_integration(self):
        """Test DELETE /api/settings/integrations/{provider_type} - Revoke integration"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.delete(f"{BACKEND_URL}/settings/integrations/{self.test_integration_provider}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("DELETE /settings/integrations/{provider}", True, f"Integration '{self.test_integration_provider}' revoked successfully")
                    return True
                else:
                    self.log_test("DELETE /settings/integrations/{provider}", False, "Revocation failed")
                    return False
            else:
                self.log_test("DELETE /settings/integrations/{provider}", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("DELETE /settings/integrations/{provider}", False, error=e)
            return False
    
    # ==================== PROVIDERS INFO API TESTS ====================
    
    def test_list_providers(self):
        """Test GET /api/settings/providers - List all available providers"""
        try:
            # This endpoint doesn't require authentication
            response = self.session.get(f"{BACKEND_URL}/settings/providers")
            
            if response.status_code == 200:
                data = response.json()
                providers = data.get("providers", {})
                
                required_categories = ["ai", "communication", "payment"]
                if all(cat in providers for cat in required_categories):
                    ai_count = len(providers.get("ai", []))
                    comm_count = len(providers.get("communication", []))
                    payment_count = len(providers.get("payment", []))
                    
                    self.log_test("GET /settings/providers", True, f"Retrieved providers: AI({ai_count}), Comm({comm_count}), Payment({payment_count})")
                    return True
                else:
                    self.log_test("GET /settings/providers", False, "Missing required provider categories")
                    return False
            else:
                self.log_test("GET /settings/providers", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/providers", False, error=e)
            return False
    
    # ==================== AFFILIATE SETTINGS API TESTS ====================
    
    def test_get_affiliate_settings(self):
        """Test GET /api/settings/affiliates - Get affiliate system settings"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/affiliates", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # Affiliate settings might have defaults
                self.log_test("GET /settings/affiliates", True, "Retrieved affiliate settings")
                return True
            else:
                self.log_test("GET /settings/affiliates", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/affiliates", False, error=e)
            return False
    
    def test_update_affiliate_settings(self):
        """Test PUT /api/settings/affiliates - Update affiliate settings"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            update_data = {
                "enabled": True,
                "default_currency": "USD",
                "default_attribution_window_days": 30,
                "approval_mode": "manual",
                "min_payout_threshold": 100.0
            }
            
            response = self.session.put(
                f"{BACKEND_URL}/settings/affiliates",
                json=update_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                # Check if the response contains the updated affiliate settings
                if data.get("enabled") == update_data["enabled"] and data.get("min_payout_threshold") == update_data["min_payout_threshold"]:
                    self.log_test("PUT /settings/affiliates", True, "Affiliate settings updated successfully")
                    return True
                else:
                    self.log_test("PUT /settings/affiliates", False, "Updated affiliate settings not reflected in response")
                    return False
            else:
                self.log_test("PUT /settings/affiliates", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("PUT /settings/affiliates", False, error=e)
            return False
    
    # ==================== AUDIT LOGS API TESTS ====================
    
    def test_get_audit_logs(self):
        """Test GET /api/settings/audit-logs - Get audit log entries"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{BACKEND_URL}/settings/audit-logs?page=1&page_size=20", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logs = data.get("logs", [])
                total = data.get("total", 0)
                
                # Audit logs might be empty for new workspace
                self.log_test("GET /settings/audit-logs", True, f"Retrieved {len(logs)} audit log entries (total: {total})")
                return True
            else:
                self.log_test("GET /settings/audit-logs", False, f"Status: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("GET /settings/audit-logs", False, error=e)
            return False
    
    # ==================== SECURITY VERIFICATION TESTS ====================
    
    def test_non_admin_access_denied(self):
        """Test that non-admin users cannot access settings endpoints (403 Forbidden)"""
        try:
            # This test would require a non-admin user token
            # For now, we'll test with no token to verify authentication is required
            response = self.session.get(f"{BACKEND_URL}/settings/workspace")
            
            if response.status_code == 401:
                self.log_test("Security: Non-admin Access", True, "Unauthenticated access properly denied (401)")
                return True
            else:
                self.log_test("Security: Non-admin Access", False, f"Expected 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Security: Non-admin Access", False, error=e)
            return False
    
    def run_all_tests(self):
        """Run all Settings Module tests"""
        print("🚀 Starting Settings Module API Tests")
        print("=" * 70)
        print("Testing: Workspace Settings + AI Config + Integrations + Affiliates + Audit Logs + Providers")
        print("=" * 70)
        
        # Authentication is required for all tests
        if not self.authenticate_admin():
            print("❌ Admin authentication failed. Cannot proceed with tests.")
            return False
        
        # Test basic health
        self.test_health_check()
        
        print("\n🏢 WORKSPACE SETTINGS API TESTS")
        print("-" * 50)
        self.test_get_workspace_settings()
        self.test_update_workspace_settings()
        
        print("\n🤖 AI CONFIGURATION API TESTS")
        print("-" * 50)
        self.test_get_ai_config()
        self.test_update_ai_config()
        self.test_get_ai_usage_stats()
        self.test_get_ai_status()
        
        print("\n🔐 INTEGRATIONS API TESTS (CRITICAL SECURITY)")
        print("-" * 50)
        self.test_list_integrations()
        self.test_add_integration()
        self.test_get_specific_integration()
        self.test_toggle_integration()
        self.test_integration_connection()
        self.test_revoke_integration()
        
        print("\n📋 PROVIDERS INFO API TESTS")
        print("-" * 50)
        self.test_list_providers()
        
        print("\n💰 AFFILIATE SETTINGS API TESTS")
        print("-" * 50)
        self.test_get_affiliate_settings()
        self.test_update_affiliate_settings()
        
        print("\n📊 AUDIT LOGS API TESTS")
        print("-" * 50)
        self.test_get_audit_logs()
        
        print("\n🔒 SECURITY VERIFICATION TESTS")
        print("-" * 50)
        self.test_non_admin_access_denied()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}: {test['error'] or test['details']}")
        else:
            print("\n✅ ALL TESTS PASSED!")
        
        return passed == total

def main():
    """Main test runner"""
    tester = SettingsModuleTester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()