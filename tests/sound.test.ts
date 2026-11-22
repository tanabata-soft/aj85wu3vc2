import { describe, expect, it } from 'vitest';
import { FLICK_RING_PARTIALS, MISS_MIN_INTERVAL_MS, flickToneFor, missSoundDue, missToneFor, resultJingleDurationMs } from '../src/game/sound';
import { hitPitchMultiplier } from '../src/game/logic';

describe('結果発表ジングル（素材ファイルへの差し替え後）', () => {
  it('結果カードを出すまでの待ち時間は、差し替え前の合成ジングルと同じ', () => {
    // 旧合成ジングルの長さ: 通常は最後の和音が 0.56+0.62=1.18 秒で消え +80ms、
    // S ランクはきらめき分だけ和音が遅れて 0.78+0.62=1.40 秒 +80ms
    expect(resultJingleDurationMs('A')).toBe(1260);
    expect(resultJingleDurationMs('B')).toBe(1260);
    expect(resultJingleDurationMs('C')).toBe(1260);
    expect(resultJingleDurationMs('S')).toBe(1480);
  });

  it('S ランクだけ待ち時間が長い（旧合成できらめきが入っていた名残）', () => {
    expect(resultJingleDurationMs('S')).toBeGreaterThan(resultJingleDurationMs('A'));
  });
});

describe('フリック音（シャキーン）', () => {
  it('全判定で擦過音の掃引は上向き（終わりの周波数が始まりより高い）', () => {
    for (const judge of ['perfect', 'great', 'good'] as const) {
      const tone = flickToneFor(judge, 0);
      expect(tone.sweepToHz).toBeGreaterThan(tone.sweepFromHz);
    }
  });

  it('金属の響きは基本音＋1.5倍＋2倍の倍音構成で、全判定とも同じ基本周波数', () => {
    expect(FLICK_RING_PARTIALS.map((p) => p.ratio)).toEqual([1, 1.5, 2]);
    for (const judge of ['perfect', 'great', 'good'] as const) {
      expect(flickToneFor(judge, 0).ringHz).toBe(2093);
    }
  });

  it('PERFECT は最も長く・大きく・響きが長く、GOOD は最も短く鈍い', () => {
    const perfect = flickToneFor('perfect', 0);
    const great = flickToneFor('great', 0);
    const good = flickToneFor('good', 0);
    expect(perfect.sweepSec).toBeGreaterThan(great.sweepSec);
    expect(great.sweepSec).toBeGreaterThan(good.sweepSec);
    expect(perfect.peak).toBeGreaterThan(great.peak);
    expect(great.peak).toBeGreaterThan(good.peak);
    expect(perfect.ringTauSec).toBeGreaterThan(great.ringTauSec);
    expect(great.ringTauSec).toBeGreaterThan(good.ringTauSec);
    expect(perfect.ringPeak).toBeGreaterThan(great.ringPeak);
    expect(great.ringPeak).toBeGreaterThan(good.ringPeak);
  });

  it('tier でピッチが hitPitchMultiplier の規則どおり上がる（長さ・音量・減衰は不変）', () => {
    const base = flickToneFor('perfect', 0);
    const tier2 = flickToneFor('perfect', 2);
    const mul = hitPitchMultiplier(2);
    expect(tier2.sweepFromHz).toBeCloseTo(base.sweepFromHz * mul);
    expect(tier2.sweepToHz).toBeCloseTo(base.sweepToHz * mul);
    expect(tier2.ringHz).toBeCloseTo(base.ringHz * mul);
    expect(tier2.sweepSec).toBe(base.sweepSec);
    expect(tier2.peak).toBe(base.peak);
    expect(tier2.ringTauSec).toBe(base.ringTauSec);
    expect(tier2.ringPeak).toBe(base.ringPeak);
  });
});

describe('ミス音（ポッ）', () => {
  it('下降サイン音（終わりの周波数が始まりより低い）で、音量は控えめ', () => {
    const tone = missToneFor();
    expect(tone.toHz).toBeLessThan(tone.fromHz);
    expect(tone.fromHz).toBe(320);
    expect(tone.toHz).toBe(180);
    // ヒット音（サンプル peak 0.32〜0.5）より小さい
    expect(tone.peak).toBeLessThan(0.32);
    expect(tone.peak).toBeGreaterThan(0);
  });

  it('最小間隔未満の連続ミスでは鳴らさない', () => {
    expect(MISS_MIN_INTERVAL_MS).toBe(60);
    expect(missSoundDue(1000, 1000 + MISS_MIN_INTERVAL_MS - 1)).toBe(false);
    expect(missSoundDue(1000, 1000 + MISS_MIN_INTERVAL_MS)).toBe(true);
    expect(missSoundDue(Number.NEGATIVE_INFINITY, 0)).toBe(true);
  });
});
