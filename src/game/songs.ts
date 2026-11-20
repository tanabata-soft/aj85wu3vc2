// リズムゲームの収録曲（この作品のデータ）。デジタルCDエンジン v1.4.0 の任意モジュール。
// CD 側の曲目（src/album/tracks.ts）と並び・タイトルを一致させる。
// - id: 曲 ID（譜面・歌詞データのキー）
// - audioUrl / jacketUrl: ゲーム用の音源（CD の MP4 から抽出した MP3 192kbps）とジャケット
// - accent: 曲のテーマ色（パターン3＝曲ごとに切り替え、オーナー決定 2026-11-20）。
//   各曲のジャケットから scripts/jacket-accent.py で抽出（視認性のため明度・彩度を持ち上げ済み）
// - frameInset: ジャケット絵の四辺に焼き込まれた紙枠の幅（px、1024px 基準）。枠が無い絵は 0
// - slidePosition: カルーセルでのジャケットの寄せ（必要な曲だけ）
// - bonus: ボーナストラックなら true（CD 側 tracks.ts の bonus と一致。スライドに金色の BONUS チップ）
// - album: 収録アルバム名（表示用） / genre: ジャンル（表示用）
import audio01 from './assets/track01.mp3';
import audio02 from './assets/track02.mp3';
import audio03 from './assets/track03.mp3';
import jacket01 from './assets/track01.jpg';
import jacket02 from './assets/track02.jpg';
import jacket03 from './assets/track03.jpg';

export interface GameSongDef {
  id: string;
  audioUrl: string;
  jacketUrl: string;
  accent: string;
  frameInset: number;
  slidePosition?: string;
  bonus?: boolean;
  album: string;
  genre: string;
}

export const SONG_DEFS: GameSongDef[] = [
  {
    id: 'warae',
    audioUrl: audio01,
    jacketUrl: jacket01,
    accent: '#d67e51',
    // 紙枠あり（クリーム色・実測38px、四辺ほぼ均一）。当初は端の分散だけの
    // 実測で 0 と誤判定した（枠に紙の質感があり分散が大きいため）。
    // 2026-11-20 オーナー指摘で目視確認のうえ設定
    frameInset: 38,
    album: 'NK-S006 SHIFT AWARD 2026 応援歌',
    genre: '90s Japanese Funk Rock',
  },
  {
    id: 'saki',
    audioUrl: audio02,
    jacketUrl: jacket02,
    accent: '#51d67b',
    frameInset: 0,
    album: 'NK-S006 SHIFT AWARD 2026 応援歌',
    genre: 'Corporate Hip-Hop',
  },
  {
    id: 'kizu',
    audioUrl: audio03,
    jacketUrl: jacket03,
    accent: '#51d6c6',
    frameInset: 0,
    bonus: true,
    album: 'NK-S006 SHIFT AWARD 2026 応援歌',
    genre: 'Contemporary J-R&B',
  },
];
