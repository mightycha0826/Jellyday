"""
식약처 "의약품 제품 허가정보" OpenAPI(DrugPrdtPrmsnInfoService07)로
product_alias 테이블을 확장하는 1회성/주기적 유지보수 스크립트.

DUR(병용금기/용량주의/투여기간주의) 자료는 "특별히 주의가 필요한" 성분만
다루기 때문에 ingredients 테이블이 303개로 작다. 반면 이 API는 허가받은
전체 의약품(4만여 건)의 품목명↔주성분(영문)을 제공해서, DUR 경고 여부와
무관하게 실제 시중 약 이름을 알아보는 데(=product_alias 커버리지) 훨씬
넓게 도움이 된다.

주의: ingredients 테이블(1일 최대용량 등 안전 수치)은 이 API로 채우지
않는다 — 그 값은 DUR 자료의 역할이고, 여기서 함부로 추정해 넣으면
잘못된 안전 정보가 될 수 있다. get_info()는 ingredients에 없는 성분도
{max_dose_mg_day: None, max_duration_days: None}로 안전하게 처리하므로
product_alias만 넓혀도 식별률은 크게 오른다.

사용법:
    MFDS_API_KEY=발급받은키 python build_product_alias.py [drug_data.db]

(PowerShell: $env:MFDS_API_KEY='...'; python build_product_alias.py)
"""

import json
import os
import re
import shutil
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService07/getDrugPrdtPrmsnInq07"
PAGE_SIZE = 500  # 이 API의 numOfRows 최대값


# inference.py의 DrugNameNormalizer와 동일한 규칙(별도 의존성 없이 재사용하기 위해 복제).
# "제형 단어 → 숫자 → 단위 단어" 조합을 문자열 끝에서 한 번만 지운다(반복 아님) —
# 반복 치환하면 "케이캡"의 "캡"처럼 우연히 제형 단어와 겹치는 브랜드명 글자까지
# 지워지는 문제가 있다. 자세한 이유는 inference.py 쪽 DrugNameNormalizer docstring 참고.
_TAIL = re.compile(
    r'(정|캡슐|캡|주사|시럽|연고|크림|패치|좌약|과립|앰플'
    r'|tablet|tab|capsule|cap|injection|inj)?'
    r'\s*\d*[\.\d]*\s*'
    r'(mg|mcg|ml|%|밀리그램|밀리그람|마이크로그램|마이크로그람'
    r'|킬로그램|킬로그람|그램|그람|밀리리터|리터|액)?$', re.I)

# 식약처 API의 ITEM_NAME은 "위더캡정밀리그램(테고프라잔고체분산체)",
# "아모크라정625밀리그램(아목시실린-클라불란산칼륨(4:1))"처럼 끝에 성분비/수출명
# 등을 괄호로(종종 중첩까지) 덧붙인 경우가 많다 — 실제 봉투/처방전엔 안 찍히는
# 부가 설명이라 매칭에 방해만 되므로, 짝을 맞추려 하지 말고 첫 '(' 부터 전부
# 잘라낸다(중첩 괄호도 한 번에 처리됨).
_TRAILING_PAREN = re.compile(r'\(.*$')


def normalize_alias(raw: str) -> str:
    import unicodedata
    if not isinstance(raw, str):
        return ''
    t = unicodedata.normalize('NFC', raw.strip())
    t = _TRAILING_PAREN.sub('', t).strip()
    t = _TAIL.sub('', t)
    return re.sub(r'\s+', ' ', t).strip().lower()


def normalize_ingredient(raw: str) -> str:
    if not isinstance(raw, str):
        return ''
    return re.sub(r'\s+', ' ', raw.strip()).lower()


def fetch_page(api_key: str, page_no: int) -> dict:
    params = {
        "serviceKey": api_key,
        "type": "json",
        "numOfRows": PAGE_SIZE,
        "pageNo": page_no,
    }
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            print(f"  재시도 {attempt + 1}/3 ({e})...")
            time.sleep(2)


def main():
    api_key = os.environ.get("MFDS_API_KEY")
    if not api_key:
        print("에러: 환경변수 MFDS_API_KEY가 설정되어 있지 않습니다.")
        sys.exit(1)

    db_path = sys.argv[1] if len(sys.argv) > 1 else "drug_data.db"
    if not os.path.exists(db_path):
        print(f"에러: {db_path} 를 찾을 수 없습니다.")
        sys.exit(1)

    backup_path = db_path + ".bak"
    shutil.copy2(db_path, backup_path)
    print(f"백업: {backup_path}")

    conn = sqlite3.connect(db_path)
    before_count = conn.execute("SELECT COUNT(*) FROM product_alias").fetchone()[0]

    first = fetch_page(api_key, 1)
    if first.get("header", {}).get("resultCode") != "00":
        print("API 에러:", first.get("header"))
        sys.exit(1)
    total = first["body"]["totalCount"]
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"전체 {total}건, {total_pages}페이지 조회 시작")

    added = skipped_cancelled = skipped_empty = skipped_exists = 0

    for page_no in range(1, total_pages + 1):
        data = first if page_no == 1 else fetch_page(api_key, page_no)
        items = data.get("body", {}).get("items", [])
        for it in items:
            if it.get("CANCEL_NAME") != "정상":
                skipped_cancelled += 1
                continue
            alias = normalize_alias(it.get("ITEM_NAME", ""))
            ingredient = normalize_ingredient(it.get("ITEM_INGR_NAME", ""))
            if not alias or not ingredient:
                skipped_empty += 1
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO product_alias (alias, ingredient, product_code) "
                "VALUES (?, ?, ?)",
                (alias, ingredient, it.get("ITEM_SEQ")),
            )
            if cur.rowcount:
                added += 1
            else:
                skipped_exists += 1
        if page_no % 10 == 0 or page_no == total_pages:
            print(f"  {page_no}/{total_pages} 페이지 처리, 지금까지 추가 {added}건")
        conn.commit()
        time.sleep(0.05)  # API 예의상 살짝 텀

    after_import_count = conn.execute("SELECT COUNT(*) FROM product_alias").fetchone()[0]

    # 자가-별칭(self-alias): 봉투/처방전에 브랜드명이 아니라 성분명(영문 등)이
    # 그대로 인쇄된 경우("Tegoprazan" 등) 그 자체가 product_alias 키에 없으면
    # 절대 안 잡힌다. ingredients·product_alias에 등장하는 모든 성분명을
    # 자기 자신에 대한 별칭으로도 등록해 exact/fuzzy 매칭 둘 다에서 잡히게 한다.
    ingredient_names = {r[0] for r in conn.execute("SELECT ingredient FROM ingredients")}
    ingredient_names |= {r[0] for r in conn.execute("SELECT DISTINCT ingredient FROM product_alias")}
    self_alias_added = 0
    for ing in ingredient_names:
        key = normalize_alias(ing)
        if not key:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO product_alias (alias, ingredient, product_code) VALUES (?, ?, NULL)",
            (key, ing),
        )
        if cur.rowcount:
            self_alias_added += 1
    conn.commit()

    after_count = conn.execute("SELECT COUNT(*) FROM product_alias").fetchone()[0]
    conn.close()

    print()
    print(f"완료: product_alias {before_count} -> {after_import_count}건 "
          f"(신규 {added}, 이미 존재 {skipped_exists}, 취소/판매중지 제외 {skipped_cancelled}, "
          f"빈 값 제외 {skipped_empty})")
    print(f"자가-별칭 {self_alias_added}건 추가 -> 최종 {after_count}건")
    print(f"문제가 있으면 {backup_path} 로 되돌릴 수 있습니다.")


if __name__ == "__main__":
    main()
