# Testing TODO for Krill Project

This document outlines the unit testing requirements for the custom functionality built in the Krill project. **Note: We are NOT testing Django framework functionality or Python standard library features - only our custom business logic.**

## 📋 Testing Priority Levels

1. **Critical Priority** - Core business logic and data integrity
2. **High Priority** - User-facing functionality and security
3. **Medium Priority** - Enhancement features and utilities
4. **Low Priority** - Nice-to-have features and edge cases

---

## ✅ COMPLETED TESTS

### Sample Management Models (23 tests) ✅
- **Sample Model Tests** (3 tests) ✅
  - Sample creation with required fields
  - Sample creation with minimal fields
  - Sample string representation

- **AliquotType Model Tests** (3 tests) ✅
  - Aliquot type creation and validation
  - Aliquot type name uniqueness constraint
  - Aliquot type string representation

- **AliquotDisposition Model Tests** (5 tests) ✅
  - Disposition creation with valid type
  - Disposition type choices validation
  - Disposition name uniqueness constraint
  - Disposition string representation
  - Disposition default type is 'stored'

- **Aliquot Model Tests** (10 tests) ✅
  - Aliquot creation with required fields
  - Aliquot disposition state management
  - Aliquot stored tubes count property
  - Aliquot unstored tubes count property
  - Explicit tube creation functionality
  - Tube disposition change
  - Tube storage location
  - Invalid tube number error handling
  - Computed disposition property (exhausted when no tubes, stored when tubes exist)

- **AliquotTube Model Tests** (4 tests) ✅
  - Individual tube creation and tracking
  - Tube number uniqueness within aliquot
  - Tube disposition state management
  - Tube string representation

### Storage Management Models (23 tests) ✅
- **Device Model Tests** (5 tests) ✅
  - Device creation with auto-store settings
  - Device creation without auto-store
  - Device string representation
  - Device-site relationship integrity
  - Auto-store enabled field functionality

- **Box Model Tests** (6 tests) ✅
  - Box creation with dimensions
  - Box auto-store inheritance from device
  - Box available slots calculation
  - Box capacity validation
  - Box string representation
  - Box-rack relationship integrity

- **Shelf Model Tests** (3 tests) ✅
  - Shelf creation
  - Shelf string representation
  - Shelf-device relationship integrity

- **Rack Model Tests** (3 tests) ✅
  - Rack creation
  - Rack string representation
  - Rack-shelf relationship integrity

- **Site Model Tests** (3 tests) ✅
  - Site creation
  - Site string representation
  - Site-device relationship integrity

- **Storage Hierarchy Tests** (3 tests) ✅
  - Site-device-shelf-rack-box hierarchy integrity
  - Storage location navigation
  - Storage capacity calculations across hierarchy

### User Management Models (26 tests) ✅
- **UserRole Model Tests** (7 tests completed) ✅
  - Role creation and assignment
  - Role hierarchy validation
  - Role permission checking
  - Role permission inheritance
  - Role string representation
  - Get or create for user method
  - Has permission method

- **Permission Model Tests** (5 tests completed) ✅
  - Permission creation and validation
  - Permission expiration handling
  - Permission uniqueness constraints
  - Permission validity checking
  - Permission string representation

- **UserAuditLog Model Tests** (8 tests completed) ✅
  - Audit log creation
  - Audit log action tracking
  - Audit log IP address capture
  - Audit log user agent capture
  - Log action convenience method
  - Log action with request
  - Get client IP method
  - Audit log string representation
  - Audit log ordering

- **UserPreference Model Tests** (6 tests completed) ✅
  - Preference creation and defaults
  - Dark mode toggle functionality
  - Preference-user relationship
  - Preference string representation
  - Preference timestamp fields

### Signal Handlers and Business Logic (18 tests) ✅
- **Aliquot Tube Creation Signal Tests** (4/4 tests) ✅
  - Automatic tube creation when aliquot is created
  - Tube creation with different quantities
  - Tube creation with zero quantity
  - Tube creation prevents infinite loops

- **Auto-Storage Signal Tests** (6/6 tests) ✅
  - Automatic storage of stored tubes
  - No auto-storage for non-stored tubes
  - Auto-store box selection algorithm
  - Available slot detection
  - Auto-store disabled scenarios
  - Auto-store inheritance from device to box

- **Tube Disposition Change Signal Tests** (4/4 tests) ✅
  - Storage location removal when tube disposition changes
  - Storage location removal for exhausted tubes
  - No storage removal for stored to stored changes
  - Old disposition storage

- **Aliquot Tube Management Tests** (4/4 tests) ✅
  - Individual tube disposition management
  - Tube count calculations (stored vs unstored)
  - Tube count calculations for non-stored aliquots
  - Simple disposition change without signal interference

---

## 🚧 REMAINING TESTS TO IMPLEMENT

### High Priority Tests

#### 1. Form Validation Tests (79 tests) ✅
- **Sample Form Tests** (30 tests) ✅
  - Sample form validation
  - Sample form with required fields
  - Sample form with optional fields
  - Sample form error handling
  - Aliquot form validation
  - Aliquot form with parent selection
  - Aliquot form quantity validation
  - Aliquot form disposition selection
  - AliquotLocation form validation
  - AliquotType form validation
  - AliquotDisposition form validation
  - Source form validation

- **Storage Form Tests** (30 tests) ✅
  - Site form validation
  - Device form validation
  - Shelf form validation
  - Rack form validation
  - Box form validation

- **Person Form Tests** (19 tests) ✅
  - CreateUser form widgets and help texts
  - CustomUserCreation form widgets and help texts
  - CustomUserChange form widgets and help texts
  - UserRole form widgets and help texts
  - Permission form validation
  - UserPreference form widgets and help texts
  - BulkPermission form validation
  - UserSearch form validation
  - AuditLogFilter form validation

#### 2. View Tests (69 tests) ✅
- **Person View Tests** (40 tests) ✅
  - ToggleTheme view tests
  - CreateUser view tests
  - UserList view tests
  - UserDetail view tests
  - UserRoleEdit view tests
  - PermissionList view tests
  - GrantPermission view tests
  - BulkGrantPermission view tests
  - AuditLog view tests
  - UserPermissionsApi view tests
  - GrantObjectPermissionApi view tests
  - RevokeObjectPermissionApi view tests

- **Sample View Tests** (15 tests) ✅
  - SampleListView tests
  - ModelCreateView tests

- **Storage View Tests** (14 tests) ✅
  - StorageListView tests
  - HomeView tests
  - StorageView tests
  - DashboardStats view tests

#### 3. API Endpoint Tests (0/8 tests) ❌
- **Sample API Tests**
  - Sample list API
  - Sample detail API
  - Sample create API
  - Sample update API
  - Sample delete API

- **Storage API Tests**
  - Storage list API
  - Storage detail API
  - Storage capacity API

#### 4. Management Command Tests (0/3 tests) ❌
- **Setup User Roles Command Tests**
  - Command execution
  - Role assignment logic
  - Error handling

### Medium Priority Tests

#### 1. Utility Function Tests
- **Helper Function Tests**
  - Date formatting utilities
  - String manipulation utilities
  - Validation utilities

#### 2. Template Tests
- **Template Rendering Tests**
  - Template context data
  - Template inheritance
  - Template filters

### Low Priority Tests

#### 1. Edge Case Tests
- **Boundary Condition Tests**
  - Maximum quantity limits
  - Minimum quantity limits
  - Special character handling
  - Unicode support

#### 2. Performance Tests
- **Database Query Tests**
  - Query optimization
  - N+1 query prevention
  - Database index usage

---

## 🎯 NEXT STEPS

1. **Add API Tests** - Test API endpoints and responses
2. **Implement Management Command Tests** - Test custom Django management commands

---

## 📊 TEST COVERAGE SUMMARY

- **Sample Models**: 23/23 tests ✅ (100%)
- **Storage Models**: 23/23 tests ✅ (100%)
- **User Management Models**: 26/26 tests ✅ (100%)
- **Signal Handlers**: 18/18 tests ✅ (100%)
- **Forms**: 79/79 tests ✅ (100%)
- **Views**: 69/69 tests ✅ (100%)
- **API Endpoints**: 0/8 tests ❌ (0%)
- **Management Commands**: 0/3 tests ❌ (0%)

**Overall Progress**: 241/266 tests completed (91%)

---

## 🔧 RECENT CHANGES

### Model Architecture Updates
- **Aliquot.disposition** is now a computed property based on individual tube dispositions
- **Explicit tube creation** via `aliquot.create_tubes()` method instead of automatic signals
- **Individual tube management** via `aliquot.change_tube_disposition()` and `aliquot.store_tube_in_location()`
- **Signals made optional** with global flags to control automatic behavior

### New Functionality Tested
- ✅ Explicit tube creation with `create_tubes(auto_store=False)`
- ✅ Individual tube disposition changes with `change_tube_disposition(tube_number, disposition)`
- ✅ Specific location storage with `store_tube_in_location(tube_number, box, row, column)`
- ✅ Computed disposition logic (exhausted when no tubes, stored when tubes exist)
- ✅ Error handling for invalid tube numbers
- ✅ Tube count properties (`stored_tubes_count`, `unstored_tubes_count`)
- ✅ Signal handler tests for automatic tube creation and storage
- ✅ Signal handler tests for disposition change handling
- ✅ Signal handler tests for auto-storage functionality
- ✅ Form validation tests for all sample forms (Sample, Aliquot, AliquotLocation, AliquotType, AliquotDisposition, Source)
- ✅ Form validation tests for all storage forms (Site, Device, Shelf, Rack, Box)
- ✅ Form validation tests for all person forms (CreateUser, CustomUserCreation, CustomUserChange, UserRole, Permission, UserPreference, BulkPermission, UserSearch, AuditLogFilter)
- ✅ View tests for all person views (ToggleTheme, CreateUser, UserList, UserDetail, UserRoleEdit, PermissionList, GrantPermission, BulkGrantPermission, AuditLog, UserPermissionsApi, GrantObjectPermissionApi, RevokeObjectPermissionApi)
- ✅ View tests for all sample views (SampleListView, ModelCreateView)
- ✅ View tests for all storage views (StorageListView, HomeView, StorageView, DashboardStats)
