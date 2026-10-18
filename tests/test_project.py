from __future__ import annotations
import ast
import json
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAST_IDS=('bot_hai_xuong_cang_tay_duoi','bot_mot_xuong_cang_tay','bot_xuong_ban_chan',
          'bot_xuong_chay','bot_xuong_got','bot_xuong_ngon_chan','bot_trat_co_chan','bot_trat_khuyu')

class ProjectIntegrityTests(unittest.TestCase):
    def test_python_parses(self):
        for name in ('autofill_portal.py','prepare_data.py','run_all.py'):
            with self.subTest(name=name):
                ast.parse((ROOT/name).read_text(encoding='utf-8'))

    def test_distinct_and_reviewed_clinical_drafts(self):
        drafts=json.loads((ROOT/'data/clinical_drafts.json').read_text(encoding='utf-8'))['procedures']
        procs=json.loads((ROOT/'data/procedures.json').read_text(encoding='utf-8'))['procedures']
        self.assertEqual(set(CAST_IDS), set(drafts))
        steps=[]
        for pid in CAST_IDS:
            with self.subTest(procedure=pid):
                draft=drafts[pid]
                proc=procs[pid]
                self.assertTrue(proc['requires_clinical_review'])
                self.assertEqual(proc['autofill_fields'], ['source'])
                self.assertTrue(draft['steps'].startswith('Bước 1.'))
                self.assertEqual(proc['form_fields']['steps'], draft['steps'])
                self.assertTrue(proc['form_fields']['preparation'])
                self.assertTrue(proc['form_fields']['late_complications'])
                steps.append(draft['steps'])
        self.assertEqual(len(steps),len(set(steps)))

    def test_no_implicit_save_or_raw_snapshot(self):
        src=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        self.assertIn('if not args.save:',src)
        self.assertIn('confirmation != "LƯU"',src)
        self.assertIn('procedure.get("requires_clinical_review", False)',src)
        self.assertNotIn('snapshot = "Không thể tạo snapshot HTML.\\n" + (driver.page_source or "")',src)

    def test_credential_file_not_tracked(self):
        if not (ROOT/'.git').exists(): return
        p=subprocess.run(['git','-C',str(ROOT),'ls-files','login.json'],capture_output=True,text=True)
        self.assertEqual(p.stdout.strip(),'','login.json MUST NOT be tracked by Git')

if __name__=='__main__':
    unittest.main()
