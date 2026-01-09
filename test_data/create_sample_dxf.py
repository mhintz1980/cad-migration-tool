#!/usr/bin/env python3
"""
Create sample DXF files for testing.
"""

import ezdxf
from pathlib import Path

def create_legacy_drawing(filename):
    """Create a legacy-style DXF drawing."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Use old layer names
    doc.layers.new('0', dxfattribs={'color': 7})
    doc.layers.new('DIMS', dxfattribs={'color': 2})
    doc.layers.new('NOTES', dxfattribs={'color': 3})
    
    # Add some geometry on layer 0
    msp.add_line((0, 0), (10, 10), dxfattribs={'layer': '0'})
    msp.add_circle((5, 5), 3, dxfattribs={'layer': '0'})
    msp.add_arc((5, 5), 2, 0, 180, dxfattribs={'layer': '0'})
    
    # Add dimensions
    msp.add_text('Ø6.0', dxfattribs={'layer': 'DIMS', 'height': 0.1})
    
    # Add notes
    msp.add_text('LEGACY DRAWING', dxfattribs={'layer': 'NOTES', 'height': 0.15})
    
    doc.saveas(filename)
    print(f"Created: {filename}")

def create_modern_drawing(filename):
    """Create a modern-style DXF drawing."""
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Use modern layer names
    doc.layers.new('GEOMETRY', dxfattribs={'color': 7, 'lineweight': 25})
    doc.layers.new('DIMENSIONS', dxfattribs={'color': 1, 'lineweight': 18})
    doc.layers.new('TEXT', dxfattribs={'color': 3, 'lineweight': 13})
    
    # Add geometry
    msp.add_line((0, 0), (10, 10), dxfattribs={'layer': 'GEOMETRY'})
    msp.add_circle((5, 5), 3, dxfattribs={'layer': 'GEOMETRY'})
    msp.add_arc((5, 5), 2, 0, 180, dxfattribs={'layer': 'GEOMETRY'})
    
    # Add dimensions
    msp.add_text('Ø6.0', dxfattribs={'layer': 'DIMENSIONS', 'height': 0.125})
    
    # Add text
    msp.add_text('MODERN DRAWING', dxfattribs={'layer': 'TEXT', 'height': 0.125})
    
    doc.saveas(filename)
    print(f"Created: {filename}")

if __name__ == '__main__':
    # Create legacy drawings for migration
    print("Creating legacy drawings...")
    for i in range(1, 6):
        create_legacy_drawing(f'test_data/input/legacy-drawing-{i:02d}.dxf')
    
    # Create sample pairs for learning
    print("\nCreating sample pairs for learning...")
    for i in range(1, 4):
        create_legacy_drawing(f'test_data/samples/old/sample-{i}.dxf')
        create_modern_drawing(f'test_data/samples/new/sample-{i}.dxf')
    
    print("\n✓ Sample DXF files created successfully!")
