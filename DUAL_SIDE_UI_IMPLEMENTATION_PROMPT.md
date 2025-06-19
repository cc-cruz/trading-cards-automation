# Dual-Side UI/UX Implementation Prompt

## Context
FlipHero trading card automation has successfully implemented dual-side OCR processing in the backend that significantly improves accuracy from ~40% to 80% confidence. The backend supports both single-side and dual-side workflows, but the frontend UI only supports single-side uploads.

## Current Backend Implementation Status ✅
- **Dual-side processing logic**: `process_dual_side_card()` function with smart field merging
- **Priority rules**: year/card_number from back > front, set/parallel from front > back
- **Enhanced confidence scoring**: Weighs critical fields with dual-side bonuses
- **API endpoints ready**:
  - `POST /api/v1/uploads/signed-urls-dual` - Generate signed URLs for front + back
  - `POST /api/v1/cards/process-dual-side` - Process cards with both images
- **Backward compatibility**: Single-side endpoints still work
- **Testing verified**: All systems passing, dual-side showing 80% vs 40% single-side confidence

## Problem Statement
The current UI (`src/pages/dashboard/upload.tsx`) only supports single image uploads and uses the old `/api/v1/cards/upload` endpoint. Users cannot take advantage of the superior dual-side OCR accuracy.

## Required Implementation

### 1. Update Upload UI Workflow
**File**: `src/pages/dashboard/upload.tsx`

Current workflow:
- Single file dropzone → Single image per card → Process individually

Required workflow:
- **Dual-side mode**: Upload TWO images per card (front + back)
- **Single-side mode**: Fallback for users with only one image
- **Visual pairing interface**: Associate front/back images clearly
- **Mode toggle**: Switch between single and dual-side workflows

### 2. Key UI Components Needed

#### A. Mode Selection
```typescript
enum UploadMode {
  SINGLE_SIDE = 'single',
  DUAL_SIDE = 'dual'
}
```

#### B. Dual-Side File Pairing Interface
- Visual card pairing component
- Drag-and-drop zones labeled "Front" and "Back"  
- Preview thumbnails showing paired images
- Ability to remove/replace individual sides

#### C. Enhanced Processing Display
- Show confidence scores from dual-side processing
- Indicate which fields came from front vs back
- Display the accuracy improvement message

### 3. API Integration Updates

#### Replace Current Single-Side Flow:
```typescript
// CURRENT (single-side)
const response = await fetch('/api/v1/cards/upload', {
  method: 'POST',
  body: formData  // single file
});
```

#### With New Dual-Side Flow:
```typescript
// NEW (dual-side)
// Step 1: Get signed URLs for both images
const response = await fetch('/api/v1/uploads/signed-urls-dual', {
  method: 'POST',
  body: JSON.stringify({
    front_content_type: 'image/jpeg',
    back_content_type: 'image/jpeg',
    front_filename: 'front.jpg',
    back_filename: 'back.jpg'
  })
});

// Step 2: Upload both images to GCS
// Step 3: Process with dual-side endpoint
const processResponse = await fetch('/api/v1/cards/process-dual-side', {
  method: 'POST',
  body: JSON.stringify({
    front_image_url: frontUrl,
    back_image_url: backUrl,
    collection_id: selectedCollection
  })
});
```

### 4. User Experience Enhancements

#### A. Educational Messaging
- Tooltip/banner explaining dual-side benefits
- "Get 80% accuracy vs 40% with dual-side scanning"
- Visual comparison showing field extraction improvements

#### B. Flexible Workflow
- Allow users to start with single-side and add back image later
- Option to process incomplete pairs (front-only or back-only)
- Batch processing for multiple card pairs

#### C. Visual Feedback
- Progress indicators for each processing step
- Field-level indicators showing front vs back extraction
- Confidence score visualization

### 5. Implementation Priority

1. **High Priority**: Basic dual-side upload and pairing UI
2. **High Priority**: Integration with new dual-side API endpoints  
3. **Medium Priority**: Mode toggle and educational messaging
4. **Medium Priority**: Enhanced visual feedback and confidence displays
5. **Low Priority**: Batch processing and advanced pairing features

## Technical Requirements

### Dependencies
- React with TypeScript (already configured)
- react-dropzone (already installed)
- Existing authentication context
- Current upload service patterns

### File Structure
```
src/pages/dashboard/
├── upload.tsx (UPDATE - main implementation)
├── scan.tsx (UPDATE - currently just imports upload)
└── components/
    ├── DualSideUploader.tsx (NEW)
    ├── CardPairingInterface.tsx (NEW)
    └── ConfidenceDisplay.tsx (NEW)
```

### Backward Compatibility
- Keep single-side workflow as fallback
- Don't break existing upload functionality
- Gradual migration path for users

## Expected Outcome
Users will be able to upload both front and back images of their trading cards, resulting in significantly improved OCR accuracy (80% vs 40%) with proper field extraction of years and card numbers that are critical for valuation.

## Testing Validation
- Verify dual-side uploads work end-to-end
- Confirm API integration with new endpoints
- Test single-side fallback still works
- Validate confidence score improvements display correctly

## Context Files to Reference
- `src/pages/dashboard/upload.tsx` - Current single-side implementation
- `src/main.py` - Backend API endpoints (lines 747-800+ for dual-side)
- `src/utils/enhanced_card_processor.py` - Dual-side processing logic
- `DUAL_SIDE_WORKFLOW.md` - Complete backend workflow documentation
- `test_dual_side.py` - Working dual-side test examples

The backend is complete and tested. Focus entirely on the frontend UI/UX implementation to enable users to access the superior dual-side OCR capabilities. 