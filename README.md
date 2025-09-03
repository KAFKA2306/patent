# patent


いいですね。「OPS（EPO）／The Lens APIで“機械化→要点サマリ＋クレーム比較”」の“実務でそのまま使える”ミニ事例を3つ出します。すべてWindows10＋VSCode＋Python前提、公開API仕様に沿ったコード断片つきです。


---

事例A｜VR/3D（リギング／ウェイト転送ツール領域）

ねらい：あなたの得意分野（VRChat／3D）で、関連特許群を自動収集→クレーム要素表を作る→自分案の「差分」を定量化。

① The Lens APIで関連公報の取得

検索例（キーワード＋CPC）：("rigging" OR "weight transfer" OR "skinning") AND (mesh OR avatar) AND CPC:G06T*

Lens Patent APIはJSONで検索→必要フィールドのみ返却できるので整形がラク（claims, title, applicants, cpc等を指定）。 


# pip install requests python-dotenv rapidfuzz
import os, requests, json
from rapidfuzz import fuzz

LENS_ENDPOINT = "https://api.lens.org/patent/search"
LENS_TOKEN = os.getenv("LENS_API_TOKEN")  # LensのBearerトークン

payload = {
  "query": "(title:rigging OR claims:\"weight transfer\" OR claims:skinning) AND (mesh OR avatar) AND cpc.code_tree:\"G06T\"",
  "size": 50,
  "include": ["lens_id","title","abstract","claims","applicants","cpc","date_published"]
}

resp = requests.post(
  LENS_ENDPOINT,
  headers={"Authorization": f"Bearer {LENS_TOKEN}", "Content-Type":"application/json"},
  data=json.dumps(payload)
).json()

docs = resp.get("data", [])

> Lensの例・使い方は公式Examplesが充実。研究／特許の横断取得も可能。 



② クレーム“要素”の自動分割（素朴なヘューリスティック）

import re

def split_claim_elements(text:str):
    # 典型的な英語クレームの連結語を区切りに要素化（簡易版）
    seps = r"(;|, and |, or | comprising | wherein | wherein the | including )"
    parts = [p.strip(" ,;.") for p in re.split(seps, text, flags=re.I) if p and not re.match(seps, p, re.I)]
    # ノイズ除去
    return [p for p in parts if len(p.split()) >= 3]

def first_independent_claim(claims:list[str]):
    for c in claims:
        if re.search(r"independent|claim\s*1", c, flags=re.I) or ("dependent" not in c.lower()):
            return c
    return claims[0] if claims else ""

③ 自分の“発明要旨”との類否スコア（素案）

my_invention = """
A method to transfer vertex weights between a source and target mesh with topology mismatch,
automatic bone mapping, and post-process smoothing for VR avatars.
""".strip()

def similarity(a, b):  # ラフな類似度（Levenshteinベース）
    return fuzz.token_set_ratio(a, b)  # 0-100

table = []
for d in docs:
    claims = d.get("claims", []) or []
    ic = first_independent_claim(claims)
    elems = split_claim_elements(ic)
    score = similarity(my_invention, ic)
    table.append({
        "lens_id": d["lens_id"], "title": d.get("title","")[:80],
        "date": d.get("date_published",""), "score": score,
        "elements": elems[:8]
    })

# score降順でトップ候補を確認 → 要点サマリ／差分観点を起こす
table = sorted(table, key=lambda x: x["score"], reverse=True)[:10]

④ 要点サマリ

技術要素：要素表から頻出語（mesh, bone mapping, smoothing…）

差分：自案にあって先行になければ“新規性のタネ”候補

注意：法的判断は人手レビュー必須（AIは素案支援）。Lens APIの検索例は公式に多数あり。 



---

事例B｜材料・プロセス（ITOスパッタ多層：酸素分圧×結晶化）

ねらい：ITO膜の多層スパッタで「保管時の結晶化度抑制×加熱後の結晶維持」の近接先行を自動抽出し、工程条件×効果の対照表を作る。

① EPO OPSで公報・請求項を取得

OPSはEPO公式REST。**書誌・法的状態・全文（一部公報）**などへ機械アクセス可能。 

Pythonラッパー「patent-client」はOPSキー管理～呼び出しを簡略化。 


# pip install patent-client lxml python-dotenv
from patent_client import PatentSearchClient
import os

EPO_KEY = os.getenv("PATENT_CLIENT_EPO_API_KEY")
EPO_SECRET = os.getenv("PATENT_CLIENT_EPO_SECRET")

client = PatentSearchClient(ops_api_key=EPO_KEY, ops_api_secret=EPO_SECRET)

q = '("indium tin oxide" OR ITO) AND sputter* AND (oxygen OR O2) AND (multilayer OR "multi-layer")'
results = client.search(q, size=50)  # EPO OPS検索 → 書誌ID群

② クレーム抽出→プロセス条件の正規化

def parse_conditions(text:str):
    # 酸素分圧、層数、基板温度などの数値を素朴抽出（例）
    import re
    o2 = re.findall(r"(oxygen|O2)[^0-9]{0,10}(\d+\.?\d*)\s*(Pa|%|sccm)", text, flags=re.I)
    temp = re.findall(r"(\d{2,3})\s*°?C", text)
    layers = re.findall(r"(multi[-\s]?layer|(\d+)\s*layers?)", text, flags=re.I)
    return {"o2": o2, "temp_C": temp, "layers": layers}

landscape = []
for r in results:
    fulltext = r.get_fulltext() or ""  # 利用可否は公報・管轄による
    claims = r.get_claims() or []
    ic = claims[0] if claims else fulltext[:2000]
    cond = parse_conditions(ic)
    landscape.append({
        "pub": r.publication_number, "title": r.title[:80],
        "o2/temp/layers": cond, "cpc": r.cpc_classes[:5]
    })

③ “工程×効果”の対照表 → 要点サマリ

条件（O₂流量/分圧、層数、基板温度、アニール）と効果語（crystallinity, haze, resistivity）をクレーム・抄録から抽出し表化

Jaccard/TF-IDFで“自案の工程セット”と近い先行を抽出→相違工程（例：第4層O₂低→第5層O₂高）を強調

エビデンス：OPSはEPO公式。ラッパー導入手順や無料枠（4GB/月）の記述あり。 


> 補強情報：Automated Patent Landscaping（mRNAのPLS事例）やBoschのPLSベンチマークデータセットが、手法／評価指標の参考になります。 




---

事例C｜「クレーム比較」自動化ミニ実装（共通部品）

ねらい：“請求項の要素表（claim chart）”を自動生成し、差分と類似度をスコア化 → Pre-check納品のコア。

from collections import Counter
from rapidfuzz import fuzz
import itertools, re

def normalize_term(s:str):
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\-_/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def claim_elements(claim_text:str):
    toks = split_claim_elements(claim_text)       # 事例Aの関数を再利用
    return [normalize_term(t) for t in toks]

def chart_and_diff(my_claim:str, prior_claims:list[str]):
    my_elems = set(claim_elements(my_claim))
    rows = []
    for pc in prior_claims:
        pe = set(claim_elements(pc))
        overlap = my_elems & pe
        missing = my_elems - pe    # 先行に“ない”→新規性のタネ候補
        extra   = pe - my_elems
        sim = fuzz.token_set_ratio(" ".join(my_elems), " ".join(pe))
        rows.append({"sim": sim, "overlap": list(overlap)[:10],
                     "missing": list(missing)[:10], "extra": list(extra)[:10]})
    return sorted(rows, key=lambda x: x["sim"], reverse=True)[:5]

NLPの改善余地：技術語抽出（TechPhrase等）やトピックモデリングで要点抽出を強化可能。産学の先行研究が豊富です。 


---

運用ノウハウ（共通）

API仕様と認証：OPS（EPO公式REST、開発者ポータルとSwaggerあり）／Lens（特許APIの例多数）。まず公式サンプルを叩いて最小実装を動かす。 

Pythonラッパー：patent-clientはOPSキー設定～検索が簡単（手順と無料枠記載）。python-epo-ops-clientも歴史的に有名（WIPOのOSS手引きでも言及）。 

PLS（Patent Landscape Study）自動化のリファレンス：実データ／評価枠組みを公開する事例や論文を参照（mRNAの自動PLS、Boschベンチ）。 

法務・品質：自動抽出は素案。請求項の法的評価は人手で最終確認（弁理士登録後はあなたがレビュー）。

出力物テンプレ：①対象定義②検索式③トップN一覧（類似度・CPC・要素表）④差分観点⑤結論（出願の可否ではなくリスク観点）を1枚サマリに。



---

自己点検（効率×品質）

良い点：Lens/OPSは公式・安定、JSON/RESTで自動化しやすい。

注意点：OPSはレート・無料枠に留意。クレーム分割は言語差や書き方に左右されるので、辞書・ルールを案件ごとに育てるのが吉。 



---

必要なら、上のA/B/Cを統合した最小リポ構成（.env、/src/collect_lens.py、/src/collect_ops.py、/src/claim_compare.py、/notebooks/PLS_demo.ipynb）を中身まで作って渡します。どのドメイン（VR/3D・ITO・AIソフト等）から最初に量産化しますか？

