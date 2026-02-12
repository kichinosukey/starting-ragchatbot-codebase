# RAG システムテストガイド

このディレクトリには、RAG チャットボットシステムの包括的なテストスイートが含まれています。

## テスト構成

### テストファイル

- **`test_api.py`** - FastAPI エンドポイントのテスト (15 tests)
  - `/api/query` エンドポイント
  - `/api/courses` エンドポイント
  - ルートエンドポイント
  - エラーハンドリング
  - CORS 設定
  - セッション管理

- **`test_ai_generator.py`** - AI 生成コンポーネントのテスト (4 tests)
  - Claude API との統合
  - ツール呼び出し処理
  - エラーハンドリング

- **`test_rag_system.py`** - RAG システムの統合テスト (5 tests)
  - クエリ処理
  - セッション管理
  - ソース属性

- **`test_search_tools.py`** - 検索ツールのテスト (22 tests)
  - CourseSearchTool
  - CourseOutlineTool
  - ToolManager
  - フィルタリングとメタデータ

### 共有フィクスチャ (`conftest.py`)

テスト全体で使用される共有フィクスチャ：

- `sample_course` - テスト用のサンプルコースデータ
- `sample_search_results` - モックの検索結果
- `sample_sources` - ソース属性データ
- `mock_vector_store` - モック VectorStore
- `mock_anthropic_client` - モック Anthropic クライアント
- `mock_rag_system` - API テスト用のモック RAG システム
- `test_app` - 静的ファイルマウントなしのテスト用 FastAPI アプリ
- `test_client` - FastAPI TestClient

## テストの実行

### 全テストを実行

```bash
# プロジェクトルートから
uv run pytest backend/tests/ -v

# backend ディレクトリから
uv run pytest tests/ -v
```

### マーカーでフィルタリング

```bash
# API テストのみ
uv run pytest tests/ -m api

# ユニットテストのみ（将来的に追加する場合）
uv run pytest tests/ -m unit

# 統合テストのみ（将来的に追加する場合）
uv run pytest tests/ -m integration
```

### 特定のテストファイルを実行

```bash
# API テストのみ
uv run pytest tests/test_api.py -v

# RAG システムテストのみ
uv run pytest tests/test_rag_system.py -v
```

### 特定のテストクラスやメソッドを実行

```bash
# 特定のテストクラス
uv run pytest tests/test_api.py::TestQueryEndpoint -v

# 特定のテストメソッド
uv run pytest tests/test_api.py::TestQueryEndpoint::test_query_without_session_id -v
```

## pytest 設定

`pyproject.toml` で設定されたオプション：

- **testpaths**: `backend/tests` - テストディレクトリ
- **python_files**: `test_*.py` - テストファイルのパターン
- **addopts**:
  - `-v` - 詳細な出力
  - `--strict-markers` - 未定義のマーカーを検出
  - `--tb=short` - 短いトレースバック
  - `--disable-warnings` - 警告を無効化

## テストマーカー

定義済みマーカー：

- `@pytest.mark.api` - API エンドポイントテスト
- `@pytest.mark.unit` - ユニットテスト（個別コンポーネント）
- `@pytest.mark.integration` - 統合テスト（複数コンポーネント）

## API テストの特徴

### 静的ファイルマウントの問題を解決

本番の `app.py` は `/frontend` ディレクトリの静的ファイルをマウントしますが、これはテスト環境では存在しません。この問題を解決するため、`conftest.py` の `test_app` フィクスチャは：

1. 静的ファイルマウントなしで FastAPI アプリを作成
2. 必要なエンドポイントのみを定義
3. モック RAG システムを使用して外部依存関係を排除

### テストカバレッジ

API テストは以下をカバーしています：

- ✅ リクエスト/レスポンスの検証
- ✅ セッション管理
- ✅ エラーハンドリング
- ✅ スキーマ検証（Pydantic モデル）
- ✅ CORS 設定
- ✅ エッジケース（空のクエリ、無効な JSON など）

## 新しいテストの追加

### 1. 新しい API テストを追加

```python
@pytest.mark.api
class TestNewFeature:
    def test_new_endpoint(self, test_client):
        response = test_client.get("/api/new-endpoint")
        assert response.status_code == 200
```

### 2. 新しいフィクスチャを追加

`conftest.py` に追加：

```python
@pytest.fixture
def new_fixture():
    # セットアップ
    yield data
    # クリーンアップ（必要に応じて）
```

### 3. 新しいマーカーを定義

`pyproject.toml` の `markers` セクションに追加：

```toml
markers = [
    "api: API endpoint tests",
    "unit: Unit tests for individual components",
    "integration: Integration tests across multiple components",
    "new_marker: Description of new marker",  # 新しいマーカー
]
```

## ベストプラクティス

1. **モックを使用** - 外部依存関係（Anthropic API、ChromaDB など）をモック化
2. **フィクスチャを再利用** - `conftest.py` の共有フィクスチャを活用
3. **明確なテスト名** - テストが何を検証するかが明確な名前を使用
4. **AAA パターン** - Arrange（準備）、Act（実行）、Assert（検証）
5. **エッジケースをテスト** - 正常系だけでなく異常系もテスト

## トラブルシューティング

### インポートエラー

テストファイルで backend モジュールのインポートエラーが発生する場合：

```python
# conftest.py で sys.path が正しく設定されているか確認
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
```

### 依存関係のエラー

```bash
# 依存関係を再同期
uv sync
```

### ChromaDB の警告

ChromaDB が resource_tracker 警告を出す場合、`app.py` の先頭で警告をフィルタリング：

```python
import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")
```

## 今後の改善案

- [ ] カバレッジレポートの追加（`pytest-cov`）
- [ ] パフォーマンステストの追加
- [ ] E2E テストの追加
- [ ] CI/CD パイプラインとの統合
- [ ] テストデータファクトリの実装（`factory_boy` など）
