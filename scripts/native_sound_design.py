#!/usr/bin/env python3
"""Install the local vanilla SFX catalog or build one production's sound mix."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from minestory import native_sound as sound


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library',type=Path,default=sound.DEFAULT_LIBRARY)
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('install');sub.add_parser('verify');sub.add_parser('list')
    timeline=sub.add_parser('timeline');timeline.add_argument('cues',type=Path)
    timeline.add_argument('--output',type=Path,required=True)
    mix=sub.add_parser('mix');mix.add_argument('--narration',type=Path,required=True)
    mix.add_argument('--effects',type=Path,required=True);mix.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action in ('install','verify'):
        report=sound.install(args.library,verify_only=args.action=='verify')
        result={'assets':len(report['assets']),'bytes':sum(a['bytes'] for a in report['assets']),
                'version':report['version'],'license':report['license'],'library':str(args.library),
                'verified':True}
    elif args.action=='list':
        data=sound.catalog();result={'minecraft':list(data['events']),'original':sorted(sound.ORIGINAL_EVENTS),
                                     'license':data['license']}
    else:
        report_path=args.output.with_suffix('.sound.json')
        if report_path.exists():
            raise FileExistsError(f'Existing production report preserved: {report_path}')
        if args.action=='timeline':
            result=sound.build_timeline(json.loads(args.cues.read_text()),args.output,library=args.library)
        else:
            from minestory.audio import probe_audio
            duration=probe_audio(args.narration)['duration']
            result=sound.mix_narration(args.narration,args.effects,args.output,duration)
        with report_path.open('x') as handle:
            json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
