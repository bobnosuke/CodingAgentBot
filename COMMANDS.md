# CoderAgent コマンドリファレンス

すべての利用可能なコマンドの詳細説明です。

## 🔑 API キー管理

### api-key register

OpenRouter API キーを登録します。

```
!api-key register <api_key>
```

**例:**
```
!api-key register sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxx
```

**説明:**
- API キーはAES-256で暗号化されて保存されます
- 登録後、コーディングセッションでAIを使用できます
- 既に登録済みの場合は上書きされます

**権限:** User以上

---

### api-key remove

登録済みの API キーを削除します。

```
!api-key remove
```

**説明:**
- API キーが削除されます
- 削除後、新しいセッションを開始する前に新しいキーを登録する必要があります

**権限:** User以上

---

## 💻 コーディング

### coding start

新しいコーディングセッションを開始します。

```
!coding start [project_name]
```

**例:**
```
!coding start MyPythonProject
!coding start  # プロジェクト名なし
```

**説明:**
- プライベートなコーディングルーム（チャンネル）が作成されます
- セッションIDが表示されます
- 複数のセッションを同時に実行できます

**権限:** User以上

**必須:** OpenRouter API キーが登録されていること

---

### coding chat

AI とチャットしてコードを生成します。

```
!coding chat <message>
```

**例:**
```
!coding chat Create a Python function that calculates fibonacci numbers
!coding chat Fix this code: def hello(): print("hello")
!coding chat Explain how decorators work in Python
```

**説明:**
- AI がメッセージに基づいてコードを生成または説明します
- ストリーミング処理で段階的に応答が表示されます
- 複数行のメッセージに対応しています

**権限:** User以上

**必須:** アクティブなコーディングセッションが必要

---

### coding end

現在のコーディングセッションを終了します。

```
!coding end
```

**説明:**
- セッションが閉じられます
- コーディングルーム（チャンネル）が削除されます
- セッション内のファイルは保存されたままです

**権限:** User以上

---

## 📁 ファイル管理

### save

ファイルをセッションに保存します。

```
!save <filename> <content>
```

**例:**
```
!save hello.py print("Hello, World!")
!save config.json {"api_key": "xxx", "timeout": 30}
```

**説明:**
- ファイルがセッションディレクトリに保存されます
- ファイル名は自動的に安全な形式に変換されます
- 既存ファイルは上書きされます

**権限:** User以上

**必須:** アクティブなコーディングセッションが必要

---

### list

セッション内のすべてのファイルを表示します。

```
!list
```

**説明:**
- セッション内のファイル一覧が表示されます
- ファイル数と合計サイズが表示されます

**権限:** User以上

**必須:** アクティブなコーディングセッションが必要

---

### get

特定のファイルの内容を表示します。

```
!get <filename>
```

**例:**
```
!get hello.py
!get config.json
```

**説明:**
- ファイルの内容が表示されます
- 長いファイルは複数のメッセージに分割されます
- コード強調表示が自動的に適用されます

**権限:** User以上

**必須:** アクティブなコーディングセッションが必要

---

### download

セッション内のすべてのファイルを ZIP にしてダウンロードします。

```
!download
```

**説明:**
- すべてのファイルが ZIP アーカイブに圧縮されます
- ZIP ファイルがDiscordで添付されます
- ファイル名は `{session_uuid}.zip` です
- Discord の 25MB 制限に対応しています

**権限:** User以上

**必須:** アクティブなコーディングセッションが必要

---

## ℹ️ 情報・ヘルプ

### guide

ガイドメニューを表示します。

```
!guide [topic]
```

**例:**
```
!guide                # メインメニュー
!guide api-key        # API キー管理について
!guide coding         # コーディングコマンドについて
!guide files          # ファイル管理について
```

**説明:**
- 各トピックの詳細なガイドが表示されます
- コマンド例が含まれています

**権限:** 誰でも使用可能

---

### about

CoderAgent についての情報を表示します。

```
!about
```

**説明:**
- プロジェクトの概要が表示されます
- 主な機能が表示されます
- 使用技術が表示されます
- クイックスタートガイドが表示されます

**権限:** 誰でも使用可能

---

### status

Bot のステータスを表示します。

```
!status
```

**説明:**
- Bot の名前と ID が表示されます
- 接続されているサーバー数が表示されます
- レイテンシー（応答時間）が表示されます
- Bot のオンライン状態が表示されます

**権限:** 誰でも使用可能

---

## 📊 コマンド一覧表

| コマンド | 説明 | 権限 | 必須 |
|---------|------|------|------|
| `!api-key register` | API キーを登録 | User | - |
| `!api-key remove` | API キーを削除 | User | - |
| `!coding start` | セッション開始 | User | API キー |
| `!coding chat` | AI とチャット | User | セッション |
| `!coding end` | セッション終了 | User | セッション |
| `!save` | ファイル保存 | User | セッション |
| `!list` | ファイル一覧 | User | セッション |
| `!get` | ファイル表示 | User | セッション |
| `!download` | ファイルダウンロード | User | セッション |
| `!guide` | ガイド表示 | 誰でも | - |
| `!about` | 情報表示 | 誰でも | - |
| `!status` | ステータス表示 | 誰でも | - |

---

## 💡 使用例

### 例1: Python 関数を作成

```
!coding start PythonProject
!coding chat Create a function that reverses a string
!save reverse.py <AI が生成したコード>
!download
!coding end
```

### 例2: Web スクレイパーを作成

```
!coding start WebScraper
!api-key register <your_api_key>
!coding chat Create a web scraper for hacker news using beautifulsoup
!save scraper.py <AI が生成したコード>
!coding chat Add error handling to the scraper
!save scraper_v2.py <更新されたコード>
!list
!download
!coding end
```

### 例3: コードをデバッグ

```
!coding start DebugSession
!coding chat This code has a bug: def add(a,b) return a+b
!coding chat Explain what's wrong
!save fixed.py <修正されたコード>
!get fixed.py
!coding end
```

---

## 🔒 権限レベル

| レベル | 説明 | 実行可能なコマンド |
|--------|------|------------------|
| User | 通常ユーザー | すべてのコマンド |
| Admin | サーバー管理者 | すべてのコマンド |
| Owner | Bot オーナー | すべてのコマンド |

---

## ⚠️ 注意事項

- **API キーの安全性**: API キーは絶対に他人と共有しないでください
- **ファイルサイズ**: Discord の 25MB 制限に注意してください
- **セッション数**: 複数のセッションを同時に実行できますが、リソース使用量に注意してください
- **タイムアウト**: 長時間の処理はタイムアウトする可能性があります

---

## 🆘 トラブルシューティング

### コマンドが認識されない

- Bot がサーバーにいることを確認
- コマンドプレフィックスが正しい（デフォルト: `!`）
- Bot に必要な権限があることを確認

### AI が応答しない

- API キーが正しく登録されているか確認
- OpenRouter のアカウントが有効か確認
- API キーの使用制限に達していないか確認

### ファイルが保存されない

- セッションがアクティブか確認
- ディスク容量が十分か確認
- ファイル名に無効な文字がないか確認

---

## 📝 更新履歴

- v1.0.0 (2026-07-14): 初版リリース
