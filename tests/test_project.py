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

    def test_inspect_opens_procedure_form(self):
        src=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        self.assertLess(
            src.index('current_step = "Chờ biểu mẫu sẵn sàng"'),
            src.index('if args.inspect:')
        )
        self.assertLess(
            src.index('if args.inspect:'),
            src.index('filled, skipped, field_selectors = fill_fields(driver)')
        )

    def test_stale_elements_are_reacquired(self):
        """A rerender can detach an element during is_displayed(), before click()."""
        source=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        funcs=[node for node in tree.body
               if isinstance(node,ast.FunctionDef)
               and node.name in ('click_unique','set_text_fresh')]
        self.assertEqual(len(funcs), 2)

        class StaleElementReferenceException(Exception):
            pass

        class By:
            CSS_SELECTOR='css'

        class WebDriverWait:
            def __init__(self, driver, timeout, poll_frequency=0.2):
                self.driver=driver
            def until(self, callback):
                for _ in range(4):
                    value=callback(self.driver)
                    if value:
                        return value
                raise AssertionError('Selenium did not recover from stale element')

        class Element:
            def __init__(self, stale=False):
                self.stale=stale
                self.clicked=False
                self.typed=None
            def is_displayed(self):
                if self.stale:
                    raise StaleElementReferenceException('detached')
                return True
            def is_enabled(self):
                return True
            def click(self):
                self.clicked=True
            def clear(self):
                self.typed=''
            def send_keys(self, value):
                self.typed=value

        class Driver:
            def __init__(self):
                self.calls=0
                self.fresh=Element()
            def find_elements(self, by, selector):
                self.calls+=1
                return [Element(stale=True)] if self.calls==1 else [self.fresh]

        namespace={'By':By,'WebDriverWait':WebDriverWait,
                   'StaleElementReferenceException':StaleElementReferenceException}
        excerpt=ast.fix_missing_locations(ast.Module(body=funcs,type_ignores=[]))
        exec(compile(excerpt,'autofill_portal.py','exec'),namespace)
        driver=Driver()
        namespace['click_unique'](driver,'#tab','Quy trình kỹ thuật')
        self.assertEqual(driver.calls,2)
        self.assertTrue(driver.fresh.clicked)

        driver=Driver()
        namespace['set_text_fresh'](driver,'#input','QTKT','Tên kỹ thuật')
        self.assertEqual(driver.calls,2)
        self.assertEqual(driver.fresh.typed,'QTKT')

    def test_verified_form_field_selectors(self):
        selectors=json.loads((ROOT/'selectors.json').read_text(encoding='utf-8'))
        expected={
            'precautions':'thanTrong',
            'support_personnel':'nhanLucHT',
            'drugs':'thuoc',
            'supplies':'vatTu',
            'equipment':'thietBi',
            'patient':'nguoiBenh',
            'records':'hoSoBA',
            'duration_hours':'thoiGian',
            'location':'diaDiem',
            'preprocedure_checks':'kiemTraHS',
            'during_procedure_events':'taiBien1',
            'post_procedure_events':'taiBien2',
            'late_complications':'bienChungMuon'
        }
        for key, data_qf in expected.items():
            with self.subTest(key=key):
                self.assertEqual(selectors[key], f'[data-qf="{data_qf}"]')

    def test_draft_preview_gated_and_never_saves(self):
        source=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        self.assertIn('if args.draft_preview and (args.save or args.inspect)', source)
        self.assertIn('if input("Chỉ xem trước trong biểu mẫu, KHÔNG LƯU. Nhập XEM', source)
        self.assertIn('btn.disabled = true', source)
        self.assertIn('allowed_fields = set(field_selectors) if args.draft_preview else', source)
        self.assertIn('if not args.save:', source)

    def test_separate_personnel_into_two_fields(self):
        source=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        fn=next(node for node in tree.body
                if isinstance(node,ast.FunctionDef) and node.name=='separate_personnel')
        ns={}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),
                     'autofill_portal.py','exec'),ns)
        text='Nhân lực trực tiếp: 01 bác sĩ, 03 KTV\\nNhân lực hỗ trợ: 01 điều dưỡng'
        primary,support=ns['separate_personnel'](text,'Người được phân công')
        self.assertIn('01 bác sĩ, 03 KTV',primary)
        self.assertEqual(support,'01 điều dưỡng')

    def test_credential_file_not_tracked(self):
        if not (ROOT/'.git').exists(): return
        p=subprocess.run(['git','-C',str(ROOT),'ls-files','login.json'],capture_output=True,text=True)
        self.assertEqual(p.stdout.strip(),'','login.json MUST NOT be tracked by Git')

if __name__=='__main__':
    unittest.main()
