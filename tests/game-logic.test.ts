import { describe, expect, it } from 'vitest';
import {
  clampSpeed,
  effectiveFallSeconds,
  findFlickHit,
  findHit,
  findNearestNote,
  makePlayNotes,
  rankFor,
  rankMeterState,
  RANK_THRESHOLDS,
  validateCharts,
  type JudgementCounts,
  type NoteData,
  type SongData,
} from '../src/game/logic';

// リズムゲームのルール層（src/game/logic.ts）の単体テスト。
// 実データの整合は tests/game-data.test.ts が担当し、ここは関数の振る舞いだけを見る。

const play = (chart: NoteData[]) => makePlayNotes(chart, 0);

describe('makePlayNotes（フリックの伝播）', () => {
  it('4要素目 "flick" が PlayNote.flick になる', () => {
    const notes = play([
      [1000, 0],
      [2000, 1, 0, 'flick'],
      [3000, 2, 800],
    ]);
    expect(notes.map((n) => n.flick)).toEqual([false, true, false]);
    expect(notes[1].holdMs).toBe(0);
    expect(notes[2].holdMs).toBe(800);
  });
});

describe('findHit（タップ判定）', () => {
  it('フリックノーツはタップでは取れない', () => {
    const notes = play([[1000, 1, 0, 'flick']]);
    expect(findHit(notes, 1, 1000)).toBeNull();
  });

  it('フリックが近くにあっても、タップノーツは取れる', () => {
    const notes = play([
      [1000, 1, 0, 'flick'],
      [1090, 1],
    ]);
    const hit = findHit(notes, 1, 1000);
    expect(hit?.note.timeMs).toBe(1090);
    expect(hit?.judge).toBe('great');
  });

  it('通常ノーツと長押しの頭は従来どおり取れる', () => {
    const notes = play([
      [1000, 0],
      [2000, 2, 800],
    ]);
    expect(findHit(notes, 0, 1010)?.judge).toBe('perfect');
    expect(findHit(notes, 2, 2000)?.note.holdMs).toBe(800);
  });
});

describe('findFlickHit（フリック判定）', () => {
  it('タップノーツよりフリックノーツを優先する（タップのほうが近くても）', () => {
    const notes = play([
      [1000, 1],
      [1140, 1, 0, 'flick'],
    ]);
    const hit = findFlickHit(notes, 1, 1000);
    expect(hit?.note.flick).toBe(true);
    expect(hit?.note.timeMs).toBe(1140);
  });

  it('フリックノーツが無ければ通常のタップノーツを取る', () => {
    const notes = play([[1000, 1]]);
    const hit = findFlickHit(notes, 1, 1030);
    expect(hit?.note.timeMs).toBe(1000);
    expect(hit?.judge).toBe('perfect');
  });

  it('長押しの頭はフリックでは取らない', () => {
    const notes = play([[1000, 1, 800]]);
    expect(findFlickHit(notes, 1, 1000)).toBeNull();
  });

  it('判定窓の外は null', () => {
    const notes = play([[1000, 1, 0, 'flick']]);
    expect(findFlickHit(notes, 1, 1300)).toBeNull();
    expect(findFlickHit(notes, 0, 1000)).toBeNull();
  });

  it('判定済みのフリックノーツは対象にしない', () => {
    const notes = play([
      [1000, 1, 0, 'flick'],
      [1100, 1],
    ]);
    notes[0].state = 1;
    const hit = findFlickHit(notes, 1, 1000);
    expect(hit?.note.timeMs).toBe(1100);
  });
});

describe('findNearestNote（タップ無効化の判定用）', () => {
  it('最寄りがフリックノーツならそれを返す', () => {
    const notes = play([
      [1000, 1, 0, 'flick'],
      [1150, 1],
    ]);
    expect(findNearestNote(notes, 1, 1000)?.flick).toBe(true);
  });

  it('窓の外なら null', () => {
    const notes = play([[1000, 1, 0, 'flick']]);
    expect(findNearestNote(notes, 1, 2000)).toBeNull();
  });
});

const songWith = (notes: NoteData[]): SongData => ({
  title: 'テスト曲',
  durationMs: 60000,
  bpm: 120,
  fever: [],
  charts: { easy: notes, normal: notes, hard: notes },
});

describe('validateCharts（フリックの規則）', () => {
  it('長押し付きのフリックノーツはエラー', () => {
    const errors = validateCharts(
      songWith([
        [3000, 0, 500, 'flick'],
        [5000, 1],
        [7000, 2],
      ]),
    );
    expect(errors.some((e) => e.includes('フリックノーツに長押し'))).toBe(true);
  });

  it('長押しなしのフリックノーツは通る（[t, lane, 0, "flick"]）', () => {
    const errors = validateCharts(
      songWith([
        [3000, 0, 0, 'flick'],
        [5000, 1],
        [7000, 2],
      ]),
    );
    expect(errors).toEqual([]);
  });

  it('長押しの帯の中にあるフリックノーツは、通常ノーツと同じくエラー', () => {
    const errors = validateCharts(
      songWith([
        [3000, 0, 3000],
        [4000, 0, 0, 'flick'],
        [8000, 1],
      ]),
    );
    expect(errors.some((e) => e.includes('長押しの帯の中'))).toBe(true);
  });
});

describe('速度調整（clampSpeed / effectiveFallSeconds）', () => {
  it('0.1 刻みに丸める', () => {
    expect(clampSpeed(1.26)).toBe(1.3);
    expect(clampSpeed(1.24)).toBe(1.2);
    expect(clampSpeed(1.0)).toBe(1.0);
  });

  it('範囲（×0.8〜×2.0）に収める', () => {
    expect(clampSpeed(0.5)).toBe(0.8);
    expect(clampSpeed(2.4)).toBe(2.0);
    expect(clampSpeed(0.8)).toBe(0.8);
    expect(clampSpeed(2.0)).toBe(2.0);
  });

  it('不正な値は既定の ×1.0', () => {
    expect(clampSpeed(NaN)).toBe(1.0);
    expect(clampSpeed(Infinity)).toBe(1.0);
  });

  it('実効落下時間は fallSeconds ÷ 倍率', () => {
    expect(effectiveFallSeconds(2.0, 1.0)).toBe(2.0);
    expect(effectiveFallSeconds(2.0, 2.0)).toBe(1.0);
    expect(effectiveFallSeconds(1.6, 0.8)).toBe(2.0);
    expect(effectiveFallSeconds(1.3, 1.3)).toBe(1.0);
  });
});

describe('rankFor / RANK_THRESHOLDS（ランクの境目）', () => {
  it('境目は S=95 / A=85 / B=70 で、ちょうど境目なら上のランク', () => {
    expect(RANK_THRESHOLDS).toEqual({ S: 95, A: 85, B: 70 });
    expect(rankFor(95)).toBe('S');
    expect(rankFor(85)).toBe('A');
    expect(rankFor(70)).toBe('B');
    expect(rankFor(69.9)).toBe('C');
    expect(rankFor(0)).toBe('C');
  });
});

describe('rankMeterState（演奏中のランクメーター）', () => {
  const counts = (p: Partial<JudgementCounts>): JudgementCounts => ({ perfect: 0, great: 0, good: 0, miss: 0, ...p });

  it('判定がまだ無いときは精度 0・ランク C・次は B まで 70', () => {
    const st = rankMeterState(counts({}));
    expect(st.judged).toBe(0);
    expect(st.accuracy).toBe(0);
    expect(st.rank).toBe('C');
    expect(st.nextRank).toBe('B');
    expect(st.toNext).toBeCloseTo(70);
  });

  it('全 PERFECT なら S で、次のランクは無い', () => {
    const st = rankMeterState(counts({ perfect: 10 }));
    expect(st.judged).toBe(10);
    expect(st.accuracy).toBeCloseTo(100);
    expect(st.rank).toBe('S');
    expect(st.nextRank).toBeNull();
    expect(st.toNext).toBe(0);
  });

  it('精度は結果画面と同じ重み（GREAT×0.7 / GOOD×0.4）で、判定済みノーツが分母', () => {
    // (8 + 2×0.7) / 10 = 94% → A、S まであと 1
    const st = rankMeterState(counts({ perfect: 8, great: 2 }));
    expect(st.accuracy).toBeCloseTo(94);
    expect(st.rank).toBe('A');
    expect(st.nextRank).toBe('S');
    expect(st.toNext).toBeCloseTo(1);
  });

  it('ミスは分母に入り分子には入らない（B 帯の例）', () => {
    // (7 + 0.7) / 10 = 77% → B、A まであと 8
    const st = rankMeterState(counts({ perfect: 7, great: 1, miss: 2 }));
    expect(st.judged).toBe(10);
    expect(st.accuracy).toBeCloseTo(77);
    expect(st.rank).toBe('B');
    expect(st.nextRank).toBe('A');
    expect(st.toNext).toBeCloseTo(8);
  });

  it('GOOD の重み 0.4 が効く（C 帯の例）', () => {
    // (5 + 4×0.4) / 10 = 66% → C、B まであと 4
    const st = rankMeterState(counts({ perfect: 5, good: 4, miss: 1 }));
    expect(st.accuracy).toBeCloseTo(66);
    expect(st.rank).toBe('C');
    expect(st.nextRank).toBe('B');
    expect(st.toNext).toBeCloseTo(4);
  });
});
