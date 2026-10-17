import argparse
import json
from pathlib import Path
import sys
from .analysis import analyze, AnalysisError

def main():
    parser=argparse.ArgumentParser(description='FlowScope static analyzer; never executes input code.')
    parser.add_argument('path',type=Path)
    parser.add_argument('--kind',choices=['auto','python','workflow'],default='auto')
    parser.add_argument('--fail-score-below',type=float)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        if args.path.stat().st_size>1_000_000:raise AnalysisError('Input exceeds the 1 MB limit.')
        result=analyze(args.path.read_text(encoding='utf-8-sig'),args.kind)
    except (AnalysisError,OSError,UnicodeError) as exc:
        print(str(exc),file=sys.stderr);return 2
    output=json.dumps(result,indent=2,ensure_ascii=False)
    if args.output:args.output.write_text(output+'\n')
    else:print(output)
    return 1 if args.fail_score_below is not None and result['quality']['value']<args.fail_score_below else 0
if __name__=='__main__':sys.exit(main())
