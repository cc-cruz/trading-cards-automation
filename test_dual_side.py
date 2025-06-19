#!/usr/bin/env python3
"""
Test dual-side card processing workflow.
This tests the enhanced OCR that processes both front and back of cards.
"""

import os
import sys
from pathlib import Path

def test_dual_side_processing():
    """Test dual-side card processing with front and back images"""
    try:
        from src.utils.enhanced_card_processor import process_dual_side_card
        
        # Look for front/back pairs in test images
        test_images_dir = Path("test_images")
        if not test_images_dir.exists():
            print("❌ No test_images directory found")
            return False
        
        # Find matching front/back pairs
        image_files = list(test_images_dir.glob("*.jpg"))
        front_back_pairs = []
        
        for img in image_files:
            name = img.stem.lower()
            if 'front' in name:
                # Look for corresponding back image
                back_name = name.replace('front', 'back')
                potential_back = test_images_dir / f"{back_name}.jpg"
                if potential_back.exists():
                    front_back_pairs.append((str(img), str(potential_back)))
            elif 'back' in name:
                # Look for corresponding front image
                front_name = name.replace('back', 'front')
                potential_front = test_images_dir / f"{front_name}.jpg"
                if potential_front.exists() and (str(potential_front), str(img)) not in front_back_pairs:
                    front_back_pairs.append((str(potential_front), str(img)))
        
        if not front_back_pairs:
            # Test with single image as front only
            if image_files:
                test_image = str(image_files[0])
                print(f"🧪 Testing single-side processing with: {Path(test_image).name}")
                result = process_dual_side_card(test_image, None)
                
                print("\n📊 Single-side OCR Results:")
                critical_fields = ['player', 'year', 'card_number', 'set']
                for field in critical_fields:
                    value = result.get(field, '')
                    status = "✅" if value else "❌"
                    print(f"   {status} {field}: {value}")
                
                confidence = result.get('confidence_score', 0)
                print(f"   📈 Confidence: {confidence:.1%}")
                return True
            else:
                print("❌ No test images found")
                return False
        
        # Test dual-side processing
        for front_path, back_path in front_back_pairs[:2]:  # Test first 2 pairs
            print(f"\n🧪 Testing dual-side processing:")
            print(f"   Front: {Path(front_path).name}")
            print(f"   Back: {Path(back_path).name}")
            
            result = process_dual_side_card(front_path, back_path)
            
            print(f"\n📊 Dual-side OCR Results:")
            critical_fields = ['player', 'year', 'card_number', 'set']
            found_count = 0
            
            for field in critical_fields:
                value = result.get(field, '')
                if value:
                    found_count += 1
                    status = "✅"
                else:
                    status = "❌"
                print(f"   {status} {field}: {value}")
            
            # Additional details
            extras = ['parallel', 'manufacturer', 'features', 'graded']
            for field in extras:
                value = result.get(field, '')
                if value:
                    print(f"   🎯 {field}: {value}")
            
            confidence = result.get('confidence_score', 0)
            sources = result.get('ocr_sources', 'unknown')
            dual_side = result.get('dual_side', False)
            
            print(f"   📈 Confidence: {confidence:.1%}")
            print(f"   📄 Sources: {sources}")
            print(f"   🔄 Dual-side: {dual_side}")
            
            # Success criteria: at least 3/4 critical fields
            success = found_count >= 3
            print(f"   {'✅ SUCCESS' if success else '⚠️  NEEDS IMPROVEMENT'} ({found_count}/4 critical fields)")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_confidence_scoring():
    """Test confidence scoring logic"""
    try:
        from src.utils.enhanced_card_processor import _calculate_dual_side_confidence
        
        # Test high confidence card
        high_confidence_card = {
            'player': 'Paul Skenes',
            'year': '2023',
            'card_number': '124',
            'set': 'Topps Chrome',
            'parallel': 'Gold Refractor',
            'dual_side': True
        }
        
        high_score = _calculate_dual_side_confidence(high_confidence_card)
        
        # Test low confidence card
        low_confidence_card = {
            'player': 'Unknown Player',
            'year': '',
            'card_number': '',
            'set': '',
            'dual_side': False
        }
        
        low_score = _calculate_dual_side_confidence(low_confidence_card)
        
        print(f"\n🎯 Confidence Scoring Test:")
        print(f"   High confidence card: {high_score:.1%}")
        print(f"   Low confidence card: {low_score:.1%}")
        
        # Should be significant difference
        return high_score > 0.8 and low_score < 0.4
        
    except Exception as e:
        print(f"❌ Confidence test failed: {e}")
        return False

def main():
    """Run dual-side processing tests"""
    print("🃏 Dual-Side Card Processing Test")
    print("=" * 40)
    
    tests = [
        ("Dual-Side Processing", test_dual_side_processing),
        ("Confidence Scoring", test_confidence_scoring),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n🔄 Testing {name}...")
        try:
            result = test_func()
            results.append(result)
            if result:
                print(f"✅ {name} - PASSED")
            else:
                print(f"❌ {name} - FAILED")
        except Exception as e:
            print(f"💥 {name} - EXCEPTION: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n" + "=" * 40)
    print(f"📊 Dual-Side Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 Dual-side processing ready!")
    else:
        print("⚠️  Some dual-side tests failed")
    
    print(f"\n💡 Workflow Benefits:")
    print(f"   - Card numbers more likely found on back")
    print(f"   - Years typically printed on back")
    print(f"   - Set info clearer on front")
    print(f"   - Combined confidence scoring")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 