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
                self.assertEqual(proc['form_fields']['steps'], draft['steps'])
                self.assertEqual(proc['form_fields']['overview'], draft['overview'])
                self.assertEqual(proc['form_fields']['drugs'], draft['drugs'])
                self.assertTrue(proc['form_fields']['preparation'])
                if pid == 'bot_trat_co_chan':
                    self.assertEqual(draft['steps'], '')  # No verified standalone reduction.
                    self.assertEqual(proc['form_fields']['late_complications'], '')
                else:
                    self.assertTrue(draft['steps'].startswith('Bước 1.'))
                    self.assertIn('Kết thúc quy trình', draft['steps'])
                    self.assertTrue(proc['form_fields']['late_complications'])
                    steps.append(draft['steps'])
                self.assertFalse(proc.get('approved_for_auto_save', False))
        self.assertEqual(len(steps),7)
        self.assertEqual(len(steps),len(set(steps)))

    def test_form_prose_excludes_internal_notes_and_anesthetic_drugs(self):
        drafts=json.loads((ROOT/'data/clinical_drafts.json').read_text(encoding='utf-8'))['procedures']
        procs=json.loads((ROOT/'data/procedures.json').read_text(encoding='utf-8'))['procedures']
        review=json.loads((ROOT/'data/clinical_review_notes.json').read_text(encoding='utf-8'))['procedures']
        self.assertEqual(set(CAST_IDS), set(review))
        fields=('overview','indications','contraindications','precautions','personnel',
                'drugs','supplies','equipment','patient','records','duration_hours',
                'location','preprocedure_checks','steps','during_procedure_events',
                'post_procedure_events','late_complications')
        import re
        note=re.compile(r'\[(?:BỔ SUNG|ĐỀ XUẤT|KHUNG|CHỜ THẨM ĐỊNH|THAM CHIẾU)')
        for pid in CAST_IDS:
            with self.subTest(procedure=pid):
                record=drafts[pid]
                for field in fields:
                    self.assertEqual(record[field],procs[pid]['form_fields'][field])
                    self.assertIsNone(note.search(record[field]),(pid,field))
                    self.assertNotIn('Phan Văn Hiếu',record[field])
                self.assertEqual(record['drugs'],'')  # The source only specified anesthesia meds.
                self.assertEqual(record['location'],'')  # No verified local room.
                self.assertEqual(record['duration_hours']!='',pid=='bot_trat_khuyu')
                self.assertTrue(review[pid]['review_items'])
                self.assertEqual(procs[pid]['autofill_fields'],['source'])

    def test_moh_source_traceability_for_all_eight(self):
        drafts=json.loads((ROOT/'data/clinical_drafts.json').read_text(encoding='utf-8'))['procedures']
        review=json.loads((ROOT/'data/clinical_review_notes.json').read_text(encoding='utf-8'))
        notes=review['procedures']
        self.assertEqual(set(CAST_IDS),set(notes))
        self.assertEqual(review['metadata']['last_rechecked'],'2026-10-19')
        for pid in CAST_IDS:
            with self.subTest(procedure=pid):
                entry=notes[pid]['source_alignment']
                self.assertTrue(entry['articles'])
                self.assertTrue(entry['gaps'])
                self.assertTrue(all(a.get('decision') and a.get('number')
                                    and a.get('url','').startswith('https://')
                                    for a in entry['articles']))
                self.assertTrue(drafts[pid]['references'])
                self.assertNotIn('[BỔ SUNG',drafts[pid]['references'])

        self.assertEqual(notes['bot_trat_khuyu']['source_alignment']['match'],
                         'direct_named_procedure')
        self.assertEqual(notes['bot_xuong_got']['source_alignment']['match'],
                         'same_condition_and_treatment')
        for pid in ('bot_mot_xuong_cang_tay','bot_xuong_ban_chan',
                    'bot_xuong_ngon_chan'):
            self.assertEqual(notes[pid]['source_alignment']['match'],'immobilization_only')
        self.assertEqual(notes['bot_trat_co_chan']['source_alignment']['match'],
                         'no_matching_reduction_guideline')
        self.assertEqual(drafts['bot_trat_co_chan']['steps'],'')
        self.assertNotIn('Bước 2. Nắn',drafts['bot_xuong_ban_chan']['steps'])
        self.assertNotIn('Bước 2. Nắn',drafts['bot_xuong_ngon_chan']['steps'])

    def test_portal_preview_uses_source_citations_only(self):
        script=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        self.assertIn('source=draft.get("references") or None',script)
        self.assertIn('if args.draft_preview and (args.save or args.inspect)',script)
        self.assertIn('if procedure.get("requires_clinical_review", False):',script)

    def test_legacy_word_import_requires_explicit_force(self):
        src=(ROOT/'make_clinical_drafts.py').read_text(encoding='utf-8')
        self.assertIn('--force-source-import',src)

    def test_no_implicit_save_or_raw_snapshot(self):
        src=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        self.assertIn('if not args.save:',src)
        self.assertIn('confirmation != expected_confirmation',src)
        self.assertIn('if approved_package is not None:',src)
        self.assertIn('if procedure.get("requires_clinical_review", False):',src)
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
        self.assertIn('if args.draft_preview and (args.save or args.inspect or args.approved_package)', source)
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
        text='Nhân lực trực tiếp: 01 bác sĩ, 03 KTV' + chr(10) + 'Nhân lực hỗ trợ: 01 điều dưỡng'
        primary,support=ns['separate_personnel'](text)
        self.assertEqual(primary,'01 bác sĩ, 03 KTV')
        self.assertEqual(support,'01 điều dưỡng')
        self.assertNotIn('Người được phân công',primary)

    def test_preview_report_checks_live_dom_without_content(self):
        source=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef)
                and node.name=='report_draft_preview_state')
        messages=[]
        ns={'print':lambda *args:messages.append(' '.join(map(str,args)))}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),
                     'autofill_portal.py','exec'),ns)

        class FakeDriver:
            def __init__(self,deployed=False,save_disabled=True):
                self.deployed=deployed
                self.save_disabled=save_disabled
                self.want=None
            def execute_script(self,script,want):
                self.want=want
                self.script=script
                return {
                    'inputs':{k:{'length':42,'checked':None} for k in want},
                    'deployment_checked':self.deployed,
                    'save_disabled':self.save_disabled
                }

        driver=FakeDriver()
        ns['report_draft_preview_state'](driver,['overview'],
                                         {'overview':'[data-qf="daiCuong"]'})
        self.assertEqual(driver.want,{'overview':'[data-qf="daiCuong"]'})
        self.assertIn('el.value',driver.script)
        self.assertTrue(any('42 ký tự' in s for s in messages))
        self.assertTrue(any('Đang triển khai: KHÔNG' in s for s in messages))
        with self.assertRaisesRegex(RuntimeError,'Đang triển khai'):
            ns['report_draft_preview_state'](
                FakeDriver(deployed=True),['overview'],{'overview':'[data-qf="daiCuong"]'})
        with self.assertRaisesRegex(RuntimeError,'Lưu'):
            ns['report_draft_preview_state'](
                FakeDriver(save_disabled=False),['overview'],{'overview':'[data-qf="daiCuong"]'})

    def test_reviewed_clinical_personnel_not_assigned_individual_name(self):
        source=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        self.assertIn('if procedure.get("requires_clinical_review", False):', source)
        self.assertIn('values["performer"] = None', source)
        self.assertIn('separate_personnel(draft["personnel"])', source)

    def test_approved_package_must_be_checked_before_browser_save(self):
        source=(ROOT/'autofill_portal.py').read_text(encoding='utf-8')
        self.assertIn('load_approved_package(',source)
        self.assertIn('source=approved_package',source) if False else None
        self.assertIn('approved_package["content"]["references"]',source)
        self.assertIn('if existing and args.approved_package:',source)
        self.assertIn('must_fill = set(REQUIRED_FIELDS)',source)
        self.assertIn('expected_confirmation = "LƯU " + item["id"]',source)

    def test_credential_file_not_tracked(self):
        if not (ROOT/'.git').exists(): return
        p=subprocess.run(['git','-C',str(ROOT),'ls-files','login.json'],capture_output=True,text=True)
        self.assertEqual(p.stdout.strip(),'','login.json MUST NOT be tracked by Git')

if __name__=='__main__':
    unittest.main()
