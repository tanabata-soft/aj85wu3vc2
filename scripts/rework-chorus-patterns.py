#!/usr/bin/env python3
"""譜面（src/game/data/charts.json）を「サビ共通の型」方式に作り替える。

v1.4.2 の譜面方針転換（オーナー指示 2026-11-22）専用の決定的な変換スクリプト。
v1.4.0 の scripts/add-flick-notes.py（曲全体に一律ルールで約8%を機械的に
フリック化）は廃止し、次に置き換える:

1. サビは「全サビ共通の型」: 各曲・各難易度で第1サビの既存ノーツを土台に
   標準サビ譜面（型）を作り、第2サビ以降へ相対時刻のまま時間シフトして移植
   する。1番・2番・ラスサビでサビ譜面を変えない。
2. フリックはサビの型の中が主軸: サビ内の歌詞行の頭（サビの入り・フレーズ
   の頭・キメ）に、難易度別の最小間隔を守って置き直す。全サビで相対位置が
   そろう（型の一部として移植される）。
3. サビ外にも「決め」のフリックを少数だけ置く: イントロのフック、サビ直前
   の盛り上がりの頂点、ラスサビ後の締めの一打など、歌詞・フレーズ構造から
   理由を説明できるアクセントのみ（ACCENTS に理由つきで定義）。それ以外の
   サビ外フリック（従来の機械変換分）は全て外す。
4. サビ外のノーツはフリックの付け外し以外いっさい変えない。サビ区間の境界
   をまたぐ長押しは触らない（移植先では保持し、型のノーツが衝突したら
   型側を落として報告する）。

サビ内の繰り返しフレーズの鏡写し: saki のサビは「We keep the SHIFT!」の
フックが2回出る（16行目と20行目）ため、20行目のフレーズ区間のノーツを
16行目のフレーズ区間のノーツの複写に置き換えて型をそろえる（MIRRORS）。

変換後は validateCharts（src/game/logic.ts）相当の検証に加え、次を機械
チェックする:
- サビ外ノーツが（フリックの付け外しを除き）変換前と完全一致すること
- サビ同士の譜面が相対時刻・レーン・種別で一致すること（落としたノーツは
  ログに残し、一致率として報告する）

使い方: python3 scripts/rework-chorus-patterns.py
（charts.json は冪等ではない: 実行は v1.4.1 の譜面に対して1回だけ。
やり直すときは charts.json を git から戻してから実行する）
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARTS_PATH = ROOT / "src" / "game" / "data" / "charts.json"
LYRICS_PATH = ROOT / "src" / "game" / "data" / "lyrics.json"

LANE_COUNT = 4
SAME_LANE_MIN_GAP_MS = 250  # フリック適格性（v1.4.0 と同じ、同レーン前後との最小間隔）
CHORUS_FLICK_WINDOW_MS = 900  # サビ行頭の候補を探す窓（前後）
CHORUS_FLICK_GAP_MS = {"easy": 4500, "normal": 2400, "hard": 1400}  # サビ内フリックの最小間隔（行頭同士で測る）
LAST_LINE_MIN_GAP_MS = 2200  # 最終行（キメ）は最小間隔未満でもこの間隔があれば置く
FLICK_NOTE_FLOOR_MS = 1200  # 実際に置いたフリック同士の絶対下限間隔
ACCENT_WINDOW_MS = 900  # アクセント候補の第1窓（アンカー前後）
ACCENT_WIDE_WINDOW_MS = 1600  # アクセント候補の最終窓

# サビ内の繰り返しフレーズの鏡写し: (曲, コピー元行index, コピー先行index)
# 区間は [行の startMs, 次の行の startMs) とする。
MIRRORS = [("saki", 16, 20)]

# サビ外の「決め」フリック: (曲, 歌詞行index, アンカーms, 理由)
# 難易度ごとに、アンカーに最も近い適格ノーツを1つ選ぶ（窓: ±900ms →
# 行区間内 → ±1600ms の順に探す）。全難易度で同じ音楽的瞬間を指す。
ACCENTS = [
    # warae『胸を張って笑え』
    ("warae", 0, 8500, "イントロの掛け声「Yeah! Alright! 1, 2, 3, Go!」の入りの打点（曲の顔となる最初の決め）"),
    ("warae", 8, 45160, "1番サビ直前「世界を救う仕事だぜ」の頭（盛り上がりの頂点からサビへ入る決め）"),
    ("warae", 21, 108480, "2番サビ直前「時代を動かす番だろが」の頭（サビ直前の決め台詞）"),
    ("warae", 38, 173080, "ラスサビ後の締め「イエーイ！サンキュー！」の頭（アウトロの決め）"),
    # saki『頂点のその先へ』
    ("saki", 1, 4380, "歌い出し「今やITの頂点 掴むこの栄光」の頭（タイトルワード「頂点」を含むイントロのフック）"),
    ("saki", 15, 60260, "1番サビ直前「俺たちの時代が 今 始まる!」の頭（サビ直前の決め台詞）"),
    ("saki", 31, 124000, "2番サビ直前「俺たちの進化は もう誰にも止められないはず」の頭（長いビルドアップの頂点）"),
    ("saki", 44, 174760, "締めの「We are SHIFT.」（曲の署名フレーズ）"),
    # kizu『きずだらけのまま』
    ("kizu", 0, 11580, "歌い出し「くらやみの なかで ひとつ」の頭（静かなイントロのフック）"),
    ("kizu", 3, 27100, "1番サビ直前「ただ しずかに いのちを ふくむ」の頭（静かな盛り上がりの頂点）"),
    ("kizu", 19, 109200, "ラスサビ直前「いま あたらしい ひを ともそう」の頭（ラスサビへの決め）"),
    ("kizu", 24, 145880, "ラスサビ後のコーダ「SHIFT...」の入り（締めの一打）"),
]


def norm(note):
    """JSON のノーツを {t, lane, hold, flick} に正規化する。"""
    return {
        "t": note[0],
        "lane": note[1],
        "hold": note[2] if len(note) > 2 else 0,
        "flick": len(note) > 3 and note[3] == "flick",
    }


def denorm(n):
    if n["flick"]:
        return [n["t"], n["lane"], 0, "flick"]
    if n["hold"] > 0:
        return [n["t"], n["lane"], n["hold"]]
    return [n["t"], n["lane"]]


def in_chorus(t, fever):
    return any(int(a * 1000) <= t < int(b * 1000) for a, b in fever)


def eligible_indices(notes):
    """フリック適格なノーツのインデックス集合（単独ノーツ・ホールドでない・
    同レーンの前後と 250ms 以上離れている）。notes は時刻順前提。"""
    times = {}
    for n in notes:
        times[n["t"]] = times.get(n["t"], 0) + 1
    by_lane = {}
    for i, n in enumerate(notes):
        by_lane.setdefault(n["lane"], []).append(i)
    out = set()
    for idxs in by_lane.values():
        for k, i in enumerate(idxs):
            n = notes[i]
            if n["hold"] > 0 or times[n["t"]] > 1:
                continue
            if k > 0 and n["t"] - notes[idxs[k - 1]]["t"] < SAME_LANE_MIN_GAP_MS:
                continue
            if k < len(idxs) - 1 and notes[idxs[k + 1]]["t"] - n["t"] < SAME_LANE_MIN_GAP_MS:
                continue
            out.add(i)
    return out


def validate_charts(song):
    """src/game/logic.ts の validateCharts の移植（add-flick-notes.py と同一）。"""
    errors = []
    order = ["easy", "normal", "hard"]
    prev_count = -1
    for diff in order:
        notes = [norm(n) for n in song["charts"][diff]]
        if len(notes) == 0:
            errors.append(f"{diff}: ノーツがありません")
        seen = set()
        prev_time = -1
        for n in notes:
            t, lane = n["t"], n["lane"]
            if t < prev_time:
                errors.append(f"{diff}: 時刻が昇順ではありません ({t})")
            prev_time = t
            if lane < 0 or lane >= LANE_COUNT:
                errors.append(f"{diff}: レーンが範囲外です ({lane})")
            key = f"{t}:{lane}"
            if key in seen:
                errors.append(f"{diff}: 同刻・同レーンの重複があります ({key})")
            seen.add(key)
        holds = [n for n in notes if n["hold"] > 0]
        for n in notes:
            if n["flick"]:
                if n["hold"] > 0:
                    errors.append(f"{diff}: フリックノーツに長押しが付いています ({n['t']}ms)")
            elif n["hold"] < 0:
                errors.append(f"{diff}: 長押しの長さが不正です ({n['t']}ms)")
        for h in holds:
            t, lane, hold = h["t"], h["lane"], h["hold"]
            tail = t + hold
            if tail > song["durationMs"] - 500:
                errors.append(f"{diff}: 長押しの尾が曲の終わりに近すぎます ({t}ms)")
            for n in notes:
                if n["lane"] == lane and t < n["t"] <= tail:
                    errors.append(f"{diff}: 長押しの帯の中に同じレーンのノーツがあります ({n['t']}ms)")
            for h2 in holds:
                if t < h2["t"] < tail:
                    errors.append(f"{diff}: 長押し同士が重なっています ({t}ms と {h2['t']}ms)")
        if notes:
            if notes[0]["t"] < 2000:
                errors.append(f"{diff}: 最初のノーツがイントロの途中です ({notes[0]['t']}ms)")
            if notes[-1]["t"] > song["durationMs"] - 1000:
                errors.append(f"{diff}: 最後のノーツが曲の終わりに近すぎます ({notes[-1]['t']}ms)")
        if len(notes) < prev_count:
            errors.append(f"{diff}: ノーツ数が前の難易度より少ないです")
        prev_count = len(notes)
    for frm, to in song["fever"]:
        if not (0 <= frm < to <= song["durationMs"] / 1000):
            errors.append(f"FEVER区間が不正です [{frm}, {to}]")
    return errors


def build_pattern(song_id, diff, notes, fever, lyrics, log):
    """第1サビから標準サビ譜面（型）を作る。相対時刻のノーツ列を返す。"""
    a1, b1 = int(fever[0][0] * 1000), int(fever[0][1] * 1000)
    base = [dict(n, t=n["t"] - a1) for n in notes if a1 <= n["t"] < b1]
    for n in base:
        n["flick"] = False

    # 鏡写し（サビ内の繰り返しフレーズ）: コピー先区間をコピー元の複写に置換
    for sid, src_line, dst_line in MIRRORS:
        if sid != song_id:
            continue
        src_lo = lyrics[src_line]["startMs"] - a1
        src_hi = lyrics[src_line + 1]["startMs"] - a1
        dst_lo = lyrics[dst_line]["startMs"] - a1
        dst_hi = lyrics[dst_line + 1]["startMs"] - a1
        for n in base:
            tail = n["t"] + n["hold"]
            if (n["t"] < src_hi and tail > src_lo and not (src_lo <= n["t"] and tail <= src_hi)) or (
                n["t"] < dst_hi and tail > dst_lo and not (dst_lo <= n["t"] and tail <= dst_hi)
            ):
                raise SystemExit(f"{song_id} {diff}: 鏡写し区間をまたぐノーツがあり中止します: {n}")
        src_notes = [n for n in base if src_lo <= n["t"] < src_hi]
        kept = [n for n in base if not (dst_lo <= n["t"] < dst_hi)]
        shift = dst_lo - src_lo
        copies = [dict(n, t=n["t"] + shift) for n in src_notes]
        log.append(
            f"鏡写し: 行{dst_line}区間 [{dst_lo + a1}..{dst_hi + a1}) の {len(base) - len(kept)} 件を"
            f"行{src_line}区間の複写 {len(copies)} 件に置換"
        )
        base = sorted(kept + copies, key=lambda n: (n["t"], n["lane"]))

    # フリックを置き直す: サビ内の歌詞行の頭に最も近い適格ノーツ。
    # 候補は (1) 行頭±900ms の窓、(2) 行区間内（サビ内）の順に探す。(2) は
    # 行頭がロングトーンのホールドや休符で打点が無いフレーズ用（例: kizu の
    # サビ入りはホールドが頭を覆い、easy では続く最初の打点が入りになる）。
    # 間隔は行頭同士で測る（置いたノーツ同士は下限 1200ms を別途守る）。
    chorus_lines = [ln for ln in lyrics if a1 <= ln["startMs"] < b1]
    elig = eligible_indices(base)
    gap_ms = CHORUS_FLICK_GAP_MS[diff]
    chosen = []  # (行頭の相対ms, 置いたノーツの相対ms)
    used = set()
    for li, ln in enumerate(chorus_lines):
        head = ln["startMs"] - a1
        span_hi = min(ln["endMs"], b1) - a1
        pools = [
            ("行頭±900ms", [i for i, n in enumerate(base) if i in elig and i not in used and abs(n["t"] - head) <= CHORUS_FLICK_WINDOW_MS]),
            ("行区間内", [i for i, n in enumerate(base) if i in elig and i not in used and head <= n["t"] < span_hi]),
        ]
        picked = None
        how = None
        for how_name, pool in pools:
            if pool:
                picked = min(pool, key=lambda j: abs(base[j]["t"] - head))
                how = how_name
                break
        if picked is None:
            log.append(f"サビ行頭フリック: 「{ln['text']}」(相対{head}ms) は候補なし")
            continue
        t = base[picked]["t"]
        if chosen:
            head_gap = head - chosen[-1][0]
            note_gap = t - chosen[-1][1]
            is_last = li == len(chorus_lines) - 1
            if note_gap < FLICK_NOTE_FLOOR_MS:
                log.append(
                    f"サビ行頭フリック: 「{ln['text']}」(相対{t}ms) は直前のフリックと {note_gap}ms しか空かないため見送り"
                )
                continue
            if head_gap < gap_ms and not (is_last and head_gap >= LAST_LINE_MIN_GAP_MS):
                log.append(
                    f"サビ行頭フリック: 「{ln['text']}」(相対{t}ms) は行頭間隔 {head_gap}ms < {gap_ms}ms のため見送り"
                )
                continue
        base[picked]["flick"] = True
        used.add(picked)
        chosen.append((head, t))
        log.append(f"サビ行頭フリック: 「{ln['text']}」頭 → 相対{t}ms レーン{base[picked]['lane']}（{how}）")
    return base


def conflicts_with_kept(p, kept):
    """型のノーツ p（絶対時刻）が保持ノーツ群と衝突したら理由文字列を返す。"""
    t, lane, hold = p["t"], p["lane"], p["hold"]
    for k in kept:
        if k["t"] == t and k["lane"] == lane:
            return f"保持ノーツと同刻・同レーン ({t}ms レーン{lane})"
        if hold > 0 and k["hold"] > 0:
            if t < k["t"] < t + hold or k["t"] < t < k["t"] + k["hold"]:
                return f"保持長押しと重なる ({t}ms と {k['t']}ms)"
        if hold > 0 and k["lane"] == lane and t < k["t"] <= t + hold:
            return f"保持ノーツが長押しの帯の中に入る ({k['t']}ms レーン{lane})"
        if k["hold"] > 0 and k["lane"] == lane and k["t"] < t <= k["t"] + k["hold"]:
            return f"保持長押しの帯の中に入る ({k['t']}ms レーン{lane})"
    return None


def rework_song(song_id, song, lyrics, report):
    fever = song["fever"]
    ranges = [(int(a * 1000), int(b * 1000)) for a, b in fever]
    for diff in ("easy", "normal", "hard"):
        orig = [norm(n) for n in song["charts"][diff]]
        log = []
        before_total = len(orig)
        before_flicks = sum(1 for n in orig if n["flick"])

        pattern = build_pattern(song_id, diff, orig, fever, lyrics, log)
        pattern_flicks = sum(1 for n in pattern if n["flick"])

        # サビ外ノーツ（フリックは全て外す。境界をまたぐ長押しはそのまま保持）
        outside = []
        for n in orig:
            if not in_chorus(n["t"], fever):
                m = dict(n)
                m["flick"] = False
                outside.append(m)

        new_notes = list(outside)
        a1 = ranges[0][0]
        for ci, (ai, bi) in enumerate(ranges):
            if ci == 0:
                new_notes += [dict(p, t=p["t"] + a1) for p in pattern]
                continue
            # 移植先で保持するノーツ: 区間内始まりで境界をまたぐ長押し
            kept_span_out = [
                n for n in orig if ai <= n["t"] < bi and n["hold"] > 0 and n["t"] + n["hold"] > bi
            ]
            kept = outside + kept_span_out
            inserted = 0
            for p in pattern:
                t = p["t"] + ai
                if t >= bi:
                    log.append(f"移植見送り(区間長超過): サビ{ci + 1} 相対{p['t']}ms レーン{p['lane']}")
                    continue
                cand = dict(p, t=t)
                reason = conflicts_with_kept(cand, kept)
                if reason:
                    log.append(f"移植見送り(衝突): サビ{ci + 1} {t}ms レーン{p['lane']}: {reason}")
                    continue
                new_notes.append(cand)
                kept.append(cand)
                inserted += 1
            for n in kept_span_out:
                new_notes.append(dict(n))
                log.append(
                    f"境界長押しを保持: サビ{ci + 1} {n['t']}ms レーン{n['lane']} 長さ{n['hold']}ms（区間外まで伸びるため型で置き換えない）"
                )
            log.append(f"サビ{ci + 1}へ型を移植: {inserted}/{len(pattern)} 件")

        new_notes.sort(key=lambda n: (n["t"], n["lane"]))

        # サビ外の「決め」フリック
        accent_notes = []
        elig = eligible_indices(new_notes)
        for sid, line_idx, anchor, reason in ACCENTS:
            if sid != song_id:
                continue
            ln = lyrics[line_idx]
            picked = None
            how = None
            pools = [
                ("アンカー±900ms", [i for i in elig if abs(new_notes[i]["t"] - anchor) <= ACCENT_WINDOW_MS]),
                (
                    "行区間内",
                    [i for i in elig if ln["startMs"] <= new_notes[i]["t"] < ln["endMs"]],
                ),
                ("アンカー±1600ms", [i for i in elig if abs(new_notes[i]["t"] - anchor) <= ACCENT_WIDE_WINDOW_MS]),
            ]
            for how_name, pool in pools:
                pool = [i for i in pool if not new_notes[i]["flick"] and not in_chorus(new_notes[i]["t"], fever)]
                if pool:
                    picked = min(pool, key=lambda j: abs(new_notes[j]["t"] - anchor))
                    how = how_name
                    break
            if picked is None:
                log.append(f"サビ外フリック見送り: 行{line_idx}「{ln['text']}」は適格ノーツなし")
                continue
            new_notes[picked]["flick"] = True
            accent_notes.append((new_notes[picked]["t"], new_notes[picked]["lane"], reason, how))
            log.append(
                f"サビ外フリック: {new_notes[picked]['t']}ms レーン{new_notes[picked]['lane']}（{how}）: {reason}"
            )

        # ---- 機械チェック ----
        # 1) サビ外ノーツがフリック以外不変か
        orig_out = sorted((n["t"], n["lane"], n["hold"]) for n in orig if not in_chorus(n["t"], fever))
        new_out = sorted((n["t"], n["lane"], n["hold"]) for n in new_notes if not in_chorus(n["t"], fever))
        outside_ok = orig_out == new_out
        # 2) サビ同士の一致（共通窓 = 最短区間長まで）
        min_len = min(b - a for a, b in ranges)
        rel_sets = []
        for ai, bi in ranges:
            rel_sets.append(
                sorted(
                    (n["t"] - ai, n["lane"], n["hold"], n["flick"])
                    for n in new_notes
                    if ai <= n["t"] < bi and n["t"] - ai < min_len
                )
            )
        match_info = []
        for ci in range(1, len(ranges)):
            s0, si = set(rel_sets[0]), set(rel_sets[ci])
            union = s0 | si
            rate = len(s0 & si) / len(union) * 100 if union else 100.0
            match_info.append(
                f"サビ1↔サビ{ci + 1}: 共通窓{min_len}msで一致率 {rate:.1f}%"
                f"（サビ1 {len(s0)}件 / サビ{ci + 1} {len(si)}件 / 差分 {len(s0 ^ si)}件）"
            )

        after_total = len(new_notes)
        after_flicks = sum(1 for n in new_notes if n["flick"])
        report.append(
            {
                "song": song_id,
                "diff": diff,
                "before_total": before_total,
                "after_total": after_total,
                "before_flicks": before_flicks,
                "after_flicks": after_flicks,
                "pattern_flicks": pattern_flicks,
                "accents": accent_notes,
                "outside_ok": outside_ok,
                "match_info": match_info,
                "log": log,
            }
        )
        song["charts"][diff] = [denorm(n) for n in new_notes]
    return song


def main():
    data = json.loads(CHARTS_PATH.read_text(encoding="utf-8"))
    lyrics_data = json.loads(LYRICS_PATH.read_text(encoding="utf-8"))
    report = []
    for song_id, song in data.items():
        rework_song(song_id, song, lyrics_data[song_id], report)

    for song_id, song in data.items():
        errors = validate_charts(song)
        if errors:
            print(f"{song_id}: 検証エラー")
            for e in errors:
                print(f"  {e}")
            return 1

    for r in report:
        print(
            f"== {r['song']} {r['diff']}: ノーツ {r['before_total']} → {r['after_total']}, "
            f"フリック {r['before_flicks']} → {r['after_flicks']}（うちサビの型 {r['pattern_flicks']}件/サビ, "
            f"サビ外アクセント {len(r['accents'])}件）"
        )
        print(f"   サビ外ノーツ不変チェック: {'OK' if r['outside_ok'] else 'NG'}")
        for m in r["match_info"]:
            print(f"   {m}")
        for line in r["log"]:
            print(f"   - {line}")

    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    CHARTS_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"書き換え完了（検証通過）: {CHARTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
