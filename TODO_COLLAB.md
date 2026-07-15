## 共同作業タスクリスト

### Manus-Alpha (担当: Manus-Alpha)
- [x] **タスクID 1**: `/setting` コマンドの実装（Embed + Select Menu + Modal）
- [x] **タスクID 2**: `/coding` サブコマンドの拡充（panel, list, info, export, rename, delete）
- [x] **タスクID 3**: CodingRoom 内の自動応答実装と `/coding chat` の削除
- [x] **タスクID 4**: エラーハンドリングの強化（共通エラーハンドラ、Embed 通知）
- [x] **タスクID 5**: DBリポジトリのテストコード作成
- [x] **タスクID 6**: 本番環境対応（Docker化）
- [x] **タスクID 7**: 管理者・オーナー用コマンドの刷新 (/health, /stats, /shutdown)
- [x] **タスクID 8**: ドキュメントの最新化（README.md, COMMANDS.md）
- [x] **タスクID 18**: CodingRoom 内コマンド (!list, !get, !download, !close, !readme) の実装
- [x] **タスクID 19**: `/coding server` コマンドの実装

### Manus-Beta (担当: Manus-Beta)
- [ ] **タスクID 9**: `/coding` サブコマンドの拡充（panel, list, info, export, rename, delete）
- [ ] **タスクID 10**: `/setting` コマンドの利用制限実装（要件定義書 31.1）
- [ ] **タスクID 11**: `/coding start` 時のモデルプリセット反映
- [ ] **タスクID 12**: `/coding panel` の実装
- [ ] **タスクID 13**: `/coding server` の実装

### 共通タスク
- [ ] **タスクID 14**: 全体的なコードレビューとリファクタリング
- [ ] **タスクID 15**: パフォーマンス最適化
- [ ] **タスクID 16**: セキュリティ強化（詳細な権限チェックなど）
- [ ] **タスクID 17**: テストコードの拡充

---

### 共同作業ルール
- **独自の名前**: 各エージェントは独自の名前（例: Manus-Alpha, Manus-Beta）を使用し、`COMMUNICATION.md` でやり取りを行います。
- **`COMMUNICATION.md` の利用**: 他のエージェントへの依頼、進捗報告、質問などは `COMMUNICATION.md` に記載します。自分の発言が長くなったら、適宜削除して新しく書き始めてください。
- **GitHub を正とする**: 作業開始前に `git pull origin main` で最新のコードを取得し、作業終了後は `git push origin main` で変更を共有します。
- **変更内容の明記**: `git commit -m "feat: /admin stats コマンドでDBから統計情報を取得` のように、変更の意図がわかるように記述します。
- **プルリクエスト**: `main` ブランチへのプルリクエストを作成し、レビューを依頼します。
- **タスク更新**: 自身の担当タスクのステータスを `TODO_COLLAB.md` 内で更新し、完了したタスクは `✅` に変更します。
