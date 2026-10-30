#!/usr/bin/env python3
"""Create a new native project for one frame interval, preserving its assets."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from minestory.native_retake import prepare_region
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--project',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
p.add_argument('--start-frame',required=True,type=int);p.add_argument('--end-frame-exclusive',required=True,type=int)
a=p.parse_args();print(json.dumps(prepare_region(a.project,a.output,a.start_frame,a.end_frame_exclusive),indent=2))
