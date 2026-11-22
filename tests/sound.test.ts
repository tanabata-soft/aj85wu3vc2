import { describe, expect, it } from 'vitest';
import { flickToneFor, resultJingleDurationMs } from '../src/game/sound';
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

describe('フリック音', () => {
  it('全判定で掃引は上向き（終わりの周波数が始まりより高い）', () => {
    for (const judge of ['perfect', 'great', 'good'] as const) {
      const tone = flickToneFor(judge, 0);
      expect(tone.sweepToHz).toBeGreaterThan(tone.sweepFromHz);
    }
  });

  it('PERFECT は最も長く・大きく・きらめきが多く、GOOD はきらめきなし', () => {
    const perfect = flickToneFor('perfect', 0);
    const great = flickToneFor('great', 0);
    const good = flickToneFor('good', 0);
    expect(perfect.sweepSec).toBeGreaterThan(great.sweepSec);
    expect(great.sweepSec).toBeGreaterThan(good.sweepSec);
    expect(perfect.peak).toBeGreaterThan(great.peak);
    expect(great.peak).toBeGreaterThan(good.peak);
    expect(perfect.sparkleHz).toHaveLength(2);
    expect(great.sparkleHz).toHaveLength(1);
    expect(good.sparkleHz).toHaveLength(0);
  });

  it('tier でピッチが hitPitchMultiplier の規則どおり上がる（長さ・音量は不変）', () => {
    const base = flickToneFor('perfect', 0);
    const tier2 = flickToneFor('perfect', 2);
    const mul = hitPitchMultiplier(2);
    expect(tier2.sweepFromHz).toBeCloseTo(base.sweepFromHz * mul);
    expect(tier2.sweepToHz).toBeCloseTo(base.sweepToHz * mul);
    expect(tier2.sparkleHz[0]).toBeCloseTo(base.sparkleHz[0] * mul);
    expect(tier2.sweepSec).toBe(base.sweepSec);
    expect(tier2.peak).toBe(base.peak);
  });
});
