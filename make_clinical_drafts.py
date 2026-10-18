from __future__ import annotations

import json
import re
from pathlib import Path
from docx import Document

SOURCE = Path(__file__).resolve().parent / 'Cap_nhat_8_quy_trinh_nan_bo_bot_2026.docx'
OUTPUT = Path(__file__).resolve().parent / 'data' / 'clinical_drafts.json'
ids = [
    'bot_hai_xuong_cang_tay_duoi',
    'bot_mot_xuong_cang_tay',
    'bot_xuong_ban_chan',
    'bot_xuong_chay',
    'bot_xuong_got',
    'bot_xuong_ngon_chan',
    'bot_trat_co_chan',
    'bot_trat_khuyu',
]
headings = {
    '1. ĐẠI CƯƠNG':'overview',
    '2. CHỈ ĐỊNH':'indications',
    '3. CHỐNG CHỈ ĐỊNH':'contraindications',
    '4. THẬN TRỌNG':'precautions',
    '5.1. Người thực hiện':'personnel',
    '5.2. Thuốc':'drugs',
    '5.3. Vật tư':'supplies',
    '5.4. Trang thiết bị':'equipment',
    '5.5. Người bệnh':'patient',
    '5.6. Hồ sơ bệnh án':'records',
    '5.7. Thời gian thực hiện kỹ thuật (giờ)':'duration_hours',
    '5.8. Địa điểm thực hiện kỹ thuật':'location',
    '5.9. Kiểm tra hồ sơ và người bệnh':'preprocedure_checks',
    '6. CÁC BƯỚC TIẾN HÀNH':'steps',
    '7.1. Tai biến trong khi thực hiện kỹ thuật':'during_procedure_events',
    '7.2. Tai biến sau khi thực hiện kỹ thuật':'post_procedure_events',
    '7.3. Biến chứng muộn':'late_complications',
    'TÀI LIỆU THAM KHẢO RIÊNG':'references',
}
doc = Document(SOURCE)
text = [p.text.strip() for p in doc.paragraphs]
start_idx = [i for i,s in enumerate(text) if re.match(r'^[1-8]\. NẮN, BÓ BỘT', s)]
assert len(start_idx) == 8, f'Expected 8 procedure headings, found {len(start_idx)}'
start_idx.append(next(i for i,s in enumerate(text) if s.startswith('TÀI LIỆU THAM KHẢO CHUNG')))
result = {}
for n, pid in enumerate(ids):
    part = text[start_idx[n]:start_idx[n+1]]
    out = {'title':part[0], 'review_status':'DRAFT_REQUIRES_CLINICAL_APPROVAL', 'source_kind':'draft_document_updated_2026-10-18'}
    key = None
    for t in part[1:]:
        if t in headings:
            key=headings[t]
            out[key]=''
        elif t in ('5. CHUẨN BỊ','7. THEO DÕI VÀ XỬ TRÍ TAI BIẾN'):
            key=None
        elif key is not None and t:
            out[key] += ('\n' if out[key] else '') + t
    missing = set(headings.values())-set(out)
    assert not missing,(pid,missing)
    assert all(out[v] for v in headings.values()),pid
    result[pid]=out
assert len({result[i]['steps'] for i in ids})==8,'Same steps shared by multiple procedures'
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
OUTPUT.write_text(json.dumps({'metadata':{'description':'Drafts extracted from the supplied Word document; NOT approved by the hospital or Ministry of Health','review_required':True,'source_file':SOURCE.name},'procedures':result},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Created',OUTPUT,'with',len(result),'distinct procedure drafts')
