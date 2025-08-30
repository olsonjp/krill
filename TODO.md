# TODO: Missing Server-Side Functionality

This document tracks frontend functionality that exists but lacks proper server-side implementation.

## 🔴 Critical Issues (Breaking Functionality)

### 1. Storage Capacity Endpoint
**Status**: ✅ COMPLETED & TESTED  
**Frontend**: `dashboard.js` makes fetch request to `/storage/capacity/`  
**Backend**: View exists in `storage/views/capacity.py` and now registered in URLs  
**Impact**: Dashboard storage usage calculation now works  

**Fix Applied**:
```python
# Added to storage/urls.py
from .views.capacity import box_capacity
path('capacity/', box_capacity, name='capacity'),
```

**Test Results**:
- ✅ Endpoint returns 200 status code for authenticated users
- ✅ Endpoint returns 302 redirect for unauthenticated users (login required)
- ✅ Returns correct JSON structure: `{"sites": {}, "total_slots": 0, "used_slots": 0, "free_slots": 0}`
- ✅ Frontend JavaScript can properly parse the response and calculate percentages
- ✅ Handles empty database gracefully
- ✅ Correctly calculates capacity with test data (96 total slots, 0 used)

---

## 🟡 Missing Features (Non-breaking but incomplete)

### 2. Server-Side Search API
**Status**: ❌ No implementation  
**Frontend**: Client-side search in `sample/list.html` and `storage/list.html`  
**Current**: JavaScript filters DOM elements  
**Need**: API endpoints for efficient server-side search  

**Required Endpoints**:
- `GET /samples/search/?q=<query>&type=<model_type>`
- `GET /storage/search/?q=<query>&type=<model_type>`

**Implementation**:
```python
# Add to sample/views/
@login_required
def search_samples(request):
    query = request.GET.get('q', '')
    model_type = request.GET.get('type', 'sample')
    # Implement search logic
    return JsonResponse({'results': results})
```

### 3. Server-Side Sorting API
**Status**: ❌ No implementation  
**Frontend**: Client-side sorting in list templates  
**Current**: JavaScript sorts DOM elements  
**Need**: API endpoints for server-side sorting  

**Required Endpoints**:
- `GET /samples/?sort=<field>&order=<asc|desc>`
- `GET /storage/?sort=<field>&order=<asc|desc>`

### 4. Activity Feed API
**Status**: ❌ No implementation  
**Frontend**: Static activity items in `home.html`  
**Current**: Hardcoded activity examples  
**Need**: Real-time activity tracking and API  

**Required Endpoints**:
- `GET /activity/recent/` - Recent user activities
- `POST /activity/log/` - Log new activity

**Implementation**:
```python
# New app: activity/
class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=50)
    target_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
```

### 5. Dashboard Statistics API
**Status**: ❌ No implementation  
**Frontend**: Hardcoded stats in `home.html`  
**Current**: Static numbers (248 samples, 78% usage, etc.)  
**Need**: Dynamic statistics from database  

**Required Endpoints**:
- `GET /dashboard/stats/` - Overall system statistics
- `GET /dashboard/user-stats/` - User-specific statistics

**Implementation**:
```python
# Add to krill/views/
@login_required
def dashboard_stats(request):
    stats = {
        'active_samples': Sample.objects.filter(active=True).count(),
        'storage_usage': calculate_storage_percentage(),
        'recent_reports': Report.objects.filter(created_at__gte=timezone.now()-timedelta(days=7)).count(),
        'alerts': Alert.objects.filter(resolved=False).count(),
    }
    return JsonResponse(stats)
```

### 6. Quick Actions API
**Status**: ❌ No implementation  
**Frontend**: Action buttons in templates  
**Current**: Buttons exist but no functionality  
**Need**: Server-side handlers for quick actions  

**Required Endpoints**:
- `POST /samples/quick-create/` - Quick sample creation
- `GET /samples/find/` - Sample finder
- `POST /reports/generate/` - Quick report generation

---

## 🟢 Enhancement Opportunities

### 7. Real-time Updates
**Status**: ❌ No implementation  
**Frontend**: Static data that requires page refresh  
**Need**: WebSocket or Server-Sent Events for real-time updates  

### 8. Bulk Operations
**Status**: ❌ No implementation  
**Frontend**: Individual item operations only  
**Need**: Bulk delete, bulk update, bulk export  

### 9. Export Functionality
**Status**: ❌ No implementation  
**Frontend**: No export buttons  
**Need**: CSV, Excel, PDF export APIs  

---

## 📋 Implementation Priority

1. **High Priority** (Fix breaking functionality):
   - ✅ Storage capacity endpoint URL registration

2. **Medium Priority** (Improve user experience):
   - Server-side search API
   - Dashboard statistics API
   - Activity feed API

3. **Low Priority** (Nice to have):
   - Server-side sorting API
   - Quick actions API
   - Real-time updates
   - Bulk operations
   - Export functionality

---

## 🛠️ Development Notes

- All new APIs should include proper authentication (`@login_required`)
- Use Django REST Framework for consistent API responses
- Implement proper error handling and validation
- Add appropriate tests for new functionality
- Consider pagination for list endpoints
- Use Django signals for activity tracking
- Consider caching for dashboard statistics

---

## 📝 Testing Checklist

For each implemented feature:
- [ ] Unit tests for models and views
- [ ] Integration tests for API endpoints
- [ ] Frontend integration testing
- [ ] Error handling validation
- [ ] Performance testing for large datasets
- [ ] Security testing (authentication, authorization)
