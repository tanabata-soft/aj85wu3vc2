"""作品の曲設定（NK-S006）。

単位D（生成器一本化）: 生成器本体の正はテンプレート repo
（mmishina-art/digitalcd-engine）の scripts/chartgen/ パッケージ1か所。
作品側はこの SONGS メタデータと歌詞入力（src/game/data/lyrics.json）だけを
持ち、scripts/generate-charts.py（入口ブートストラップ）がテンプレートの
chartgen を参照して生成する。曲を足すときはここに1曲分を足す。
各キーの意味はテンプレート scripts/chartgen/config.py のコメント参照。
"""

SONGS = {
    # SONGS メタ（FEVER 区間・chorus_layer vocal・chorus_bonus 0.5）は従来どおり。
    # v1.4.16 で v6 生成器（v6-1.2 + フリック v6-2、ラスサビ伝播の修正込み）に
    # ネイティブ化し、各曲に flick: True を付けた。
    "warae": {
        "title": "胸を張って笑え",
        "audio": "src/game/assets/track01.mp3",
        "fever": [[48.0, 68.0], [112.0, 131.0], [144.0, 163.0]],
        "chart_v5": True,
        "chorus_layer": "vocal",
        "chorus_bonus": 0.5,
        "flick": True,
        "flick_budget": {'easy': 11, 'normal': 17, 'hard': 22},
        "ballad": False,
    },
    "saki": {
        "title": "頂点のその先へ",
        "audio": "src/game/assets/track02.mp3",
        "fever": [[64.0, 96.0], [128.0, 160.0]],
        "chart_v5": True,
        "chorus_layer": "vocal",
        "chorus_bonus": 0.5,
        "flick": True,
        "flick_budget": {'easy': 12, 'normal': 17, 'hard': 23},
        "ballad": False,
    },
    "kizu": {
        "title": "きずだらけのまま",
        "audio": "src/game/assets/track03.mp3",
        "fever": [[31.0, 52.0], [73.0, 94.0], [114.0, 135.0]],
        "chart_v5": True,
        "chorus_layer": "vocal",
        "chorus_bonus": 0.5,
        "flick": True,
        "flick_budget": {'easy': 6, 'normal': 11, 'hard': 13},
        "ballad": True,
        "flick_lock": [[21943,0,0],[29768,1,2],[31742,0,0],[34992,3,1],[37593,1,0],[51618,1,1],[53243,0,2],[73424,1,0],[76742,3,1],[79319,1,0],[93367,2,1],[114242,1,1],[150419,0,0]],
    },
}
