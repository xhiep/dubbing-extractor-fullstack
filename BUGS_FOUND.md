# Bugs Found - Playwright Testing

## Test Run: 2026-04-25

### Critical Issues

#### 1. Test Locators Mismatch with Vietnamese UI
- **Status**: FOUND
- **Severity**: High
- **Description**: Tests use English text ("Source", "Adjust", "Dub") but UI displays Vietnamese ("Nguồn Video", "Điều Chỉnh", "Lồng Tiếng")
- **Impact**: 16/20 tests failed due to element not found
- **Fix**: Update test selectors to match Vietnamese UI

#### 2. Backend API Endpoint Incorrect
- **Status**: FOUND
- **Severity**: Medium
- **Description**: Test calls `/api/system/health` but actual endpoint is `/health`
- **Impact**: Health check test fails with 404
- **Fix**: Update API endpoint in test

#### 3. Tab Role Attributes Missing
- **Status**: FOUND
- **Severity**: Medium
- **Description**: Tabs don't have `role="tab"` attribute, they are buttons
- **Impact**: All tab navigation tests timeout
- **Fix**: Update selectors to use button elements

#### 4. WebSocket Connection Failing (403 Forbidden)
- **Status**: FOUND
- **Severity**: High
- **Description**: WebSocket connection to `ws://localhost:5173/ws/socket.io/` fails with 403 error
- **Impact**: Real-time updates not working, "Disconnected" status shown in UI
- **Root Cause**: Frontend trying to connect to WebSocket through Vite dev server, but backend WebSocket is on port 8000
- **Fix**: Update WebSocket connection URL to point to backend server

### Round 1 Tests (15/15 passed)
- ✓ All basic UI tests passed
- ✓ WebSocket connected successfully
- ✓ Dark mode toggle works
- ✓ Backend API healthy

### Round 2 - Stress Tests (11/15 passed, 4 failed)

#### New Bugs Found:

##### 5. Preview Button Not Disabled During Processing
- **Status**: FOUND
- **Severity**: Medium
- **Description**: Preview button can be spam-clicked, not disabled during processing
- **Impact**: Multiple concurrent preview requests possible
- **Fix**: Add loading state and disable button during preview

##### 6. Input Field Becomes Unresponsive After Tab Switching
- **Status**: FOUND
- **Severity**: High
- **Description**: After rapid tab switching (20+ times), URL input field stops responding
- **Impact**: User cannot enter URL after heavy tab switching
- **Root Cause**: Possible React state issue or event listener leak
- **Fix**: Investigate component re-rendering and cleanup

##### 7. Preview Button Disabled on Empty/Invalid URL
- **Status**: FOUND (Expected behavior, but test needs fix)
- **Severity**: Low
- **Description**: Preview button correctly disables when URL is empty/invalid
- **Impact**: Test fails because it tries to click disabled button
- **Fix**: Update test to check disabled state instead of clicking

##### 8. Browser Back Navigation Breaks SPA
- **Status**: FOUND
- **Severity**: Medium
- **Description**: Using browser back button navigates to about:blank instead of staying in SPA
- **Impact**: User loses app state when using browser navigation
- **Fix**: Implement proper history management or disable browser navigation
