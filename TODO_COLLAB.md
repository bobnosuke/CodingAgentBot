# 🤝 CoderAgent 共同作業タスクリスト

このファイルは、CoderAgent プロジェクトにおける共同作業のタスク管理に使用します。

## 📝 コミュニケーションルール
- 各エージェントは独自の名前（例: Manus-Alpha, Manus-Beta）でコミュニケーションログに記載すること。
- 作業開始前には必ず `git pull origin main` で最新のコードを取得し、`TODO_COLLAB.md` と `COMMUNICATION.md` を確認すること。
- 自身の担当タスクのステータスを更新すること。
- `COMMUNICATION.md` が長大になることを避けるため、自身の記述が一定量に達したら、その部分を削除して新しい記述を開始すること。
- 要件定義書は `docs/` フォルダに格納されており、常に最新版を参照すること。

## 📋 タスクリスト (最新コマンド仕様に基づく)

| タスクID | 内容 | 担当 | ステータス | 備考 |
|:---|:---|:---|:---|:---|
| 1 | `/coding` コマンドの刷新 (panel, server) | Manus-Beta | ⬜ 未着手 | `panel` は開発開始、プロジェクト一覧、詳細確認、プロジェクト名変更を統合。`server` は利用状況表示。 | 
| 2 | `/setting` コマンドの刷新 (Embed + Select Menu + Modal) | Manus-Alpha | 🚧 進行中 | `/setting` は設定表示パネル、`!setting` は直接設定パネルを表示。APIキー登録/削除、モデル選択、利用状況確認を統合。 | 
| 3 | `/guide` コマンドのページ送り機能実装 | Manus-Beta | ⬜ 未着手 | Embed パネルでページ送りボタンを実装。 | 
| 4 | CodingRoom 内の自動応答実装と `/coding chat` の削除 | Manus-Alpha | ⬜ 未着手 | `!` 以外のユーザー発言を AI との会話と認識。`/coding chat` を削除。 | 
| 5 | CodingRoom 内コマンド (!list, !get, !download, !close, !readme) の実装と修正 | Manus-Beta | ⬜ 未着手 | `!list` は階層表示、`!get` は Select Menu、`!download` は複数選択と「全てダウンロード」ボタン、`!close` は確認ボタン、`!readme` はプロジェクト README 表示。 | 
| 6 | `/config` コマンドの刷新 (Embed パネル) | Manus-Beta | ⬜ 未着手 | カテゴリ、同時チャンネル数、利用人数制限を設定可能。 | 
| 7 | 管理者・オーナー用コマンドの刷新 (/health, /stats, /shutdown) | Manus-Alpha | ⬜ 未着手 | `/health` は Embed パネル、`/stats` はグラフ表示、`/shutdown` は安全停止。 | 
| 8 | 最終動作確認と GitHub への最終同期 | 全員 | ⬜ 未着手 | プロジェクト全体の最終確認。 | 
