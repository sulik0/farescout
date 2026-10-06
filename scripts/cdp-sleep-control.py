"""Run only after the user agrees to a brief Mac sleep; never reconnects Chrome."""
import argparse
import asyncio
import json
import runpy
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from farescout.config import Settings


async def main(args):
    snapshot = runpy.run_path(str(Path(__file__).with_name('probe-socai-reuse.py')))['snapshot']
    settings = Settings.from_env()
    before = await snapshot(settings)
    if not before.get('browser_connected'):
        raise RuntimeError('必须先有有效 CDP 连接，才能做睡眠对照；脚本不会请求连接')
    result = {'before':before, 'sleep_command_at':datetime.now(timezone.utc).isoformat(),
              'human_confirmation':'not_recorded', 'condition':'user_approved_manual_sleep'}
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('BEFORE',json.dumps(before,ensure_ascii=False),flush=True)
    start = datetime.now(timezone.utc)
    subprocess.run(['pmset','sleepnow'],check=True)
    # A wall-clock delay also works when the process resumes after system sleep.
    while (datetime.now(timezone.utc)-start).total_seconds() < 60:
        await asyncio.sleep(2)
    result['after'] = await snapshot(settings)
    result['elapsed_wall_seconds'] = round((datetime.now(timezone.utc)-start).total_seconds(),3)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('AFTER',json.dumps(result['after'],ensure_ascii=False),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--confirm-sleep',action='store_true',help='已安排用户唤醒，确认此脚本会让本机立即睡眠')
    args=parser.parse_args()
    if not args.confirm_sleep:
        parser.error('需要明确传入 --confirm-sleep；此脚本会让 Mac 睡眠，不能用于自动状态检查')
    asyncio.run(main(args))
