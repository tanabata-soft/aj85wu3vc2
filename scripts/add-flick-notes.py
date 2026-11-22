#!/usr/bin/env python3
"""譜面（src/game/data/charts.json）のタップノーツの一部をフリックノーツ化する。

フリック試作（v1.4.0）専用の決定的な変換スクリプト。音源解析からの再生成
（generate-charts.py）は全ノーツが変わってしまうため使わず、既存の譜面の
タップノーツの一部だけを [t, lane, 0, "flick"] に書き換える。

変換ルール（決定的）:
- 対象はホールドでない単独ノーツ（同時刻に他レーンのノーツがある同時押しは除外）。
- 同レーンの前後ノーツと 250ms 以上離れていること。
- 各曲の最初2ノーツと最後1ノーツは対象外。
- 変換の目安はタップノーツの 5〜10%: 対象候補を時刻順に並べ、約8%になるよう
  均等に間引いて選ぶ（上の条件だけだと 20〜45% になってしまうための調整）。
  選んだ中でも、直前のフリック化から難易度別の間隔（easy 1600ms / normal
  1200ms / hard 1000ms）以上空いていないものは落とす。
- 変換後は validateCharts（src/game/logic.ts）相当の検証を通すこと。

すでにフリックノーツが入っている譜面には実行しない（やり直すときは
charts.json を git から戻してから実行する）。

使い方: python3 scripts/add-flick-notes.py
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARTS_PATH = ROOT / "src" / "game" / "data" / "charts.json"

LANE_COUNT = 4
SAME_LANE_MIN_GAP_MS = 250
FLICK_MIN_GAP_MS = {"easy": 1600, "normal": 1200, "hard": 1000}
TARGET_RATIO = 0.08  # 目安 5〜10% の中央寄り


def hold_of(note):
    return note[2] if len(note) > 2 else 0


def is_flick(note):
    return len(note) > 3 and note[3] == "flick"


def candidates(notes, diff):
    """変換候補（対象条件をすべて満たすノーツのインデックス、時刻順）。"""
    times = {}
    for n in notes:
        times[n[0]] = times.get(n[0], 0) + 1
    by_lane = {}
    for i, n in enumerate(notes):
        by_lane.setdefault(n[1], []).append(i)
    lane_pos = {}
    for idxs in by_lane.values():
        for k, i in enumerate(idxs):
            lane_pos[i] = k
    out = []
    for i, n in enumerate(notes):
        t, lane = n[0], n[1]
        if hold_of(n) > 0 or is_flick(n):
            continue
        if i < 2 or i >= len(notes) - 1:
            continue  # 最初2ノーツ・最後1ノーツは対象外
        if times[t] > 1:
            continue  # 同時押しは除外
        idxs = by_lane[lane]
        k = lane_pos[i]
        if k > 0 and t - notes[idxs[k - 1]][0] < SAME_LANE_MIN_GAP_MS:
            continue
        if k < len(idxs) - 1 and notes[idxs[k + 1]][0] - t < SAME_LANE_MIN_GAP_MS:
            continue
        out.append(i)
    return out


def select(notes, diff):
    """候補から、目安の割合になるよう均等に間引いて選ぶ（間隔ルールも守る）。"""
    cand = candidates(notes, diff)
    taps = sum(1 for n in notes if hold_of(n) == 0 and not is_flick(n))
    target = max(1, round(taps * TARGET_RATIO)) if cand else 0
    target = min(target, len(cand))
    picked = []
    if target > 0:
        step = len(cand) / target
        last_time = None
        for j in range(target):
            i = cand[math.floor(j * step)]
            t = notes[i][0]
            if last_time is not None and t - last_time < FLICK_MIN_GAP_MS[diff]:
                continue
            picked.append(i)
            last_time = t
    return picked, taps


def validate_charts(song):
    """src/game/logic.ts の validateCharts の移植（フリック規則を含む）。"""
    errors = []
    order = ["easy", "normal", "hard"]
    prev_count = -1
    for diff in order:
        notes = song["charts"][diff]
        if len(notes) == 0:
            errors.append(f"{diff}: ノーツがありません")
        seen = set()
        prev_time = -1
        for n in notes:
            t, lane = n[0], n[1]
            if t < prev_time:
                errors.append(f"{diff}: 時刻が昇順ではありません ({t})")
            prev_time = t
            if lane < 0 or lane >= LANE_COUNT:
                errors.append(f"{diff}: レーンが範囲外です ({lane})")
            key = f"{t}:{lane}"
            if key in seen:
                errors.append(f"{diff}: 同刻・同レーンの重複があります ({key})")
            seen.add(key)
        holds = [n for n in notes if hold_of(n) > 0]
        for n in notes:
            if is_flick(n):
                if hold_of(n) > 0:
                    errors.append(f"{diff}: フリックノーツに長押しが付いています ({n[0]}ms)")
            elif len(n) > 2 and n[2] <= 0:
                errors.append(f"{diff}: 長押しの長さが不正です ({n[0]}ms)")
        for h in holds:
            t, lane, hold = h[0], h[1], hold_of(h)
            tail = t + hold
            if tail > song["durationMs"] - 500:
                errors.append(f"{diff}: 長押しの尾が曲の終わりに近すぎます ({t}ms)")
            for n in notes:
                if n[1] == lane and t < n[0] <= tail:
                    errors.append(f"{diff}: 長押しの帯の中に同じレーンのノーツがあります ({n[0]}ms)")
            for h2 in holds:
                if t < h2[0] < tail:
                    errors.append(f"{diff}: 長押し同士が重なっています ({t}ms と {h2[0]}ms)")
        if notes:
            if notes[0][0] < 2000:
                errors.append(f"{diff}: 最初のノーツがイントロの途中です ({notes[0][0]}ms)")
            if notes[-1][0] > song["durationMs"] - 1000:
                errors.append(f"{diff}: 最後のノーツが曲の終わりに近すぎます ({notes[-1][0]}ms)")
        if len(notes) < prev_count:
            errors.append(f"{diff}: ノーツ数が前の難易度より少ないです")
        prev_count = len(notes)
    for frm, to in song["fever"]:
        if not (0 <= frm < to <= song["durationMs"] / 1000):
            errors.append(f"FEVER区間が不正です [{frm}, {to}]")
    return errors


def main():
    data = json.loads(CHARTS_PATH.read_text(encoding="utf-8"))
    for song in data.values():
        for notes in song["charts"].values():
            if any(is_flick(n) for n in notes):
                print("すでにフリックノーツが入っています。中止します（やり直すときは charts.json を戻してください）")
                return 1
    total = 0
    for song_id, song in data.items():
        for diff in ("easy", "normal", "hard"):
            notes = song["charts"][diff]
            picked, taps = select(notes, diff)
            for i in picked:
                t, lane = notes[i][0], notes[i][1]
                notes[i] = [t, lane, 0, "flick"]
            total += len(picked)
            pct = len(picked) / taps * 100 if taps else 0
            print(f"{song_id} {diff}: タップ {taps} 件中 {len(picked)} 件をフリック化 ({pct:.1f}%)")
    for song_id, song in data.items():
        errors = validate_charts(song)
        if errors:
            print(f"{song_id}: 検証エラー")
            for e in errors:
                print(f"  {e}")
            return 1
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    CHARTS_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"合計 {total} 件をフリック化し、検証を通りました: {CHARTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
