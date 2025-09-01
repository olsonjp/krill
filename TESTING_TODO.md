# Testing TODO for Krill Project

This document outlines the unit testing requirements for the custom functionality built in the Krill project. **Note: We are NOT testing Django framework functionality or Python standard library features - only our custom business logic.**

## 📋 Testing Priority Levels

1. **Critical Priority** - Core business logic and data integrity
2. **High Priority** - User-facing functionality and security
3. **Medium Priority** - Enhancement features and utilities
4. **Low Priority** - Nice-to-have features and edge cases

---

## ✅ COMPLETED TESTS

### Sample Management Models (37 tests) ✅
- **Sample Model Tests** (5 tests) ✅
  - Sample creation with required fields
  - Sample creation with minimal fields
  - Sample string representation
  - Sample-source relationship integrity
  - Sample name uniqueness (no unique constraint)

- **AliquotType Model Tests** (4 tests) ✅
  - Aliquot type creation and validation
  - Aliquot type name uniqueness constraint
  - Aliquot type string representation
  - Aliquot type with blank description

- **AliquotDisposition Model Tests** (5 tests) ✅
  - Disposition creation with valid type
  - Disposition type choices validation
  - Disposition name uniqueness constraint
  - Disposition string representation
  - Disposition default type is 'stored'

- **Aliquot Model Tests** (12 tests) ✅
  - Aliquot creation with required fields
  - Aliquot creation with parent-child relationships
  - Aliquot quantity validation
  - Aliquot disposition state management
  - Aliquot soft delete functionality
  - Aliquot timestamp fields
  - Aliquot string representation
  - Aliquot sample relationship integrity
  - Aliquot parent-child lineage tracking
  - Aliquot stored tubes count property
  - Aliquot unstored tubes count property

- **AliquotLocation Model Tests** (6 tests) ✅
  - Location creation with valid coordinates
  - Location coordinate validation
  - Location unique constraint enforcement
  - Aliquot-tube number uniqueness
  - Location box relationship integrity
  - Location string representation

- **AliquotTube Model Tests** (5 tests) ✅
  - Individual tube creation and tracking
  - Tube number uniqueness within aliquot
  - Tube disposition state management
  - Tube storage location property
  - Tube string representation
  - Tube timestamp fields

### Storage Management Models (26 tests) ✅
- **Device Model Tests** (5 tests) ✅
  - Device creation with auto-store settings
  - Device creation without auto-store
  - Device string representation
  - Device-site relationship integrity
  - Auto-store enabled field functionality

- **Box Model Tests** (9 tests) ✅
  - Box creation with dimensions
  - Box auto-store inheritance from device
  - Box available slots calculation
  - Box available slots with occupied slots
  - Box capacity validation
  - Box string representation
  - Box-rack relationship integrity
  - Box has_available_slots method
  - Box aliquots property

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

---

## 🔄 IN PROGRESS / PARTIALLY COMPLETED

### User Management Models (26 tests completed) ✅
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

---

## 🚧 REMAINING TESTS TO IMPLEMENT

### High Priority Tests

#### 1. Signal Handlers and Business Logic
- **Aliquot Tube Creation Signal Tests**
  - Automatic tube creation when aliquot is created
  - Tube creation with different quantities
  - Tube creation with zero quantity
  - Tube creation prevents infinite loops

- **Auto-Storage Signal Tests**
  - Automatic storage of stored tubes
  - No auto-storage for non-stored tubes
  - Auto-store box selection algorithm
  - Available slot detection
  - Auto-store disabled scenarios
  - Auto-store inheritance from device to box

- **Tube Disposition Change Signal Tests**
  - Storage location removal when tube disposition changes
  - Storage location removal for exhausted tubes
  - No storage removal for stored to stored changes
  - Old disposition storage

- **Aliquot Tube Management Tests**
  - Tube count calculations (stored vs unstored)
  - Tube count calculations for non-stored aliquots
  - Individual tube disposition management

#### 2. Form Validation Tests
- **Sample Form Tests**
  - Sample form validation
  - Sample form with required fields
  - Sample form with optional fields
  - Sample form error handling

- **Aliquot Form Tests**
  - Aliquot form validation
  - Aliquot form with parent selection
  - Aliquot form quantity validation
  - Aliquot form disposition selection

#### 3. View Tests
- **Sample View Tests**
  - Sample list view
  - Sample detail view
  - Sample create view
  - Sample edit view
  - Sample delete view

- **Storage View Tests**
  - Storage list view
  - Storage detail view
  - Storage create view
  - Storage capacity view

- **User Management View Tests**
  - User list view
  - User detail view
  - User role edit view
  - User audit log view

#### 4. API Endpoint Tests
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

#### 5. Management Command Tests
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

1. **Implement Signal Handler Tests** - Test the auto-storage and tube creation logic
2. **Add Form Validation Tests** - Test form validation and error handling
3. **Create View Tests** - Test view functionality and permissions
4. **Add API Tests** - Test API endpoints and responses
5. **Implement Management Command Tests** - Test custom Django management commands

---

## 📊 TEST COVERAGE SUMMARY

- **Sample Models**: 37/37 tests ✅ (100%)
- **Storage Models**: 26/26 tests ✅ (100%)
- **User Management Models**: 26/26 tests ✅ (100%)
- **Signal Handlers**: 0/15 tests ❌ (0%)
- **Forms**: 0/8 tests ❌ (0%)
- **Views**: 0/12 tests ❌ (0%)
- **API Endpoints**: 0/8 tests ❌ (0%)
- **Management Commands**: 0/3 tests ❌ (0%)

**Overall Progress**: 103/135 tests completed (76%)
