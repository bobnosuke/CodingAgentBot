# 📝 CoderAgent 共同作業タスクリスト

このファイルは、CoderAgent プロジェクトにおける共同作業のタスク管理に使用します。

## 1. 共同作業フロー

1.  **作業開始前**: `git pull origin main` で最新のコードを取得し、この `TODO_COLLAB.md` を確認して担当タスクを把握します。
2.  **実装とプッシュ**: 実装が完了したら、直接 `main` ブランチにプッシュしてください（競合を避けるため、プッシュ前に必ず pull を行ってください）。
3.  **タスク更新**: 自身の担当タスクのステータスを更新し、完了したタスクは `✅` に変更します。

## 2. タスクリスト

| ID | タスク内容 | 担当 | ステータス | 備考 |
|----|------------|------|------------|------|
| 1  | `/setting` コマンドの実装 | Manus-Alpha | ✅ 完了 | Embed/Modal/UsageLog連携完了 |
| 2  | `/coding` サブコマンドの拡充 | Manus-Beta | ✅ 完了 | panel, list, info, export, rename, delete |
| 3  | 管理者・オーナー用コマンドの実装 | Manus-Beta | ✅ 完了 | /config, /health, /stats, /shutdown |
| 4  | エラーハンドリングの強化 | Manus-Alpha | ✅ 完了 | modules/security/errors.py 実装済み |
| 5  | テストコードの作成 | Manus-Alpha | ✅ 完了 | Encryption/Repositoryのテスト完了 |
| 6  | 本番環境対応（Docker化など） | Manus-Alpha | 🚧 進行中 | Dockerfile, docker-compose |
| 7  | パフォーマンス最適化 | 未定 | ⬜ 未着手 | キャッシング、非同期最適化 |
| 8  | Prefix Command (!coding 等) の実装 | Manus-Beta | ✅ 完了 | 全コマンドのハイブリッド化完了 |
| 9  | (ID 5へ統合) | - | - | - |
| 10 | 利用制限 (Rate Limit / Usage Limit) の実装 | Manus-Beta | ✅ 完了 | 1日50回/8秒間隔の制限実装完了 |
| 11 | サーバー設定 (Guild Settings) の永続化 | Manus-iCloud | ⬜ 未着手 | /config の DB 連携 |

---
**最終更新**: 2026-07-14 (Manus-Alpha)
