import chainlit as cl
import httpx
import asyncio
import json # jsonモジュールが既にインポートされているか確認してください

# --- ここから追加・修正する設定 ---
# 1. API GatewayのVPCエンドポイント固有のDNS名を設定します。
#    これは、VPCコンソールでAPI GatewayのVPCエンドポイントの詳細から確認できます。
#    例: vpce-xxxxxxxxxxxxxxxxx-yyyyyyyy.execute-api.ap-northeast-1.vpce.amazonaws.com
#    **重要**: 末尾に <stage> や <resource-path> は含めないでください。
VPC_ENDPOINT_DNS_NAME = "vpce-xxxxxxxxxxxxxxxxx-yyyyyyyy.execute-api.ap-northeast-1.vpce.amazonaws.com"

# 2. API Gatewayの標準的なホスト名をHostヘッダーに設定します。
#    これは、API GatewayのAPI IDとリージョンから構成されます。
#    <your-api-id> は実際のAPI IDに置き換えてください。
API_GATEWAY_HOST_HEADER = "<your-api-id>.execute-api.ap-northeast-1.amazonaws.com"

# 3. 実際のAPIリソースパスとステージを組み合わせて、API Gatewayの標準URLからのパス部分を作成します。
#    例: "/dev" または "/dev/your-resource-path" など
API_PATH_AND_STAGE = "/dev"

# 4. 最終的にhttpxリクエストで使用する完全なURLを構築します。
#    VPCエンドポイントのDNS名にAPIのパスとステージを結合します。
TARGET_API_URL = f"https://{VPC_ENDPOINT_DNS_NAME}{API_PATH_AND_STAGE}"
# --- ここまで追加・修正する設定 ---


async def main(message: cl.Message):
    """
    ユーザーからメッセージが送信されたときに実行されるメイン関数。
    RAGプロセスとLLMによる回答生成を行う。
    """
    print(f"app.py: @cl.on_messageがトリガーされました。ユーザーメッセージ: '{message.content}'")
    current_settings = cl.user_session.get("settings") # 現在のチャット設定を取得
    chat_history = cl.user_session.get("chat_history") # 現在の会話履歴を取得

    user_message = message.content
    selected_model_id = current_settings["Model"] # UIで選択されたモデルID

    temperature = current_settings["Temperature"]
    max_tokens = int(current_settings["MAX_TOKEN_SIZE"])

    # 応答メッセージ用のChainlit Messageオブジェクトを作成
    # このオブジェクトを初期表示、ステータス更新、最終的な回答表示に使用します。
    bot_response_message = cl.Message(content="処理中...", author="システム")
    await bot_response_message.send()
    print("app.py: 初期ステータスメッセージを送信しました。") # デバッグログ

    response_content = "API Gatewayへの接続に失敗しました。"
    context_docs_meta = [] # 関連ドキュメントのメタデータ格納用

    # httpxのAsyncClientを使用し、セッションを再利用してパフォーマンスを向上
    async with httpx.AsyncClient(timeout=90.0) as client: # クライアントタイムアウトも設定
        try:
            # ステータスを「Elasticsearch検索中」に更新
            bot_response_message.content = "**Elasticsearchを検索中...** 関連情報を探しています。"
            await bot_response_message.update()
            print("app.py: ステータスメッセージをElasticsearch検索中に更新しました。") # デバッグログ

            # バックエンド（API Gateway経由のLambda）に送信するペイロードを構築
            payload = {
                "message": user_message,
                "modelId": selected_model_id,
                "temperature": temperature,
                "maxTokens": max_tokens,
                "history": chat_history,
            }
            print(f"app.py: API Gatewayにペイロードを送信中: {json.dumps(payload)}") # デバッグログ

            # --- ここから修正 ---
            # API GatewayへのリクエストにHostヘッダーを追加
            request_headers = {"Host": API_GATEWAY_HOST_HEADER}

            # API呼び出しを非同期タスクとして実行
            api_call_task = asyncio.create_task(
                client.post(TARGET_API_URL, json=payload, headers=request_headers)
            )
            # --- ここまで修正 ---

            # ここから元のコードの続き
            # ... api_call_task の結果を待機し、処理する部分
            api_response = await api_call_task
            api_response.raise_for_status() # HTTPエラーレスポンス（4xx, 5xx）を例外として発生させる
            response_data = api_response.json()

            # 必要に応じてresponse_dataからresponse_contentやcontext_docs_metaを抽出
            response_content = response_data.get("answer", "回答がありません。")
            context_docs_meta = response_data.get("context", [])

        except httpx.RequestError as e:
            # ネットワーク関連のエラー（DNS解決失敗、接続拒否など）
            print(f"app.py: httpx.RequestErrorが発生しました: {e}")
            bot_response_message.content = f"API Gatewayへの接続に失敗しました: {e}"
            if isinstance(e, httpx.NetworkError):
                print(f"app.py: ネットワークエラー詳細: {e.__cause__}")
            response_content = "API Gatewayへの接続中にネットワークエラーが発生しました。設定を確認してください。"
        except httpx.HTTPStatusError as e:
            # HTTPステータスコードがエラー（4xx, 5xx）の場合
            print(f"app.py: httpx.HTTPStatusErrorが発生しました: {e.response.status_code} - {e.response.text}")
            bot_response_message.content = f"API Gatewayからのエラー応答: {e.response.status_code} - {e.response.text}"
            response_content = f"API Gatewayがエラーを返しました: {e.response.status_code} - {e.response.text}"
        except json.JSONDecodeError as e:
            # APIからの応答がJSONとしてパースできない場合
            print(f"app.py: JSONDecodeErrorが発生しました: {e}")
            bot_response_message.content = f"API Gatewayからの応答を解析できませんでした: {e}"
            response_content = "API Gatewayからの応答形式が不正です。"
        except Exception as e:
            # その他の予期せぬエラー
            print(f"app.py: 予期せぬエラーが発生しました: {e}")
            bot_response_message.content = f"処理中に予期せぬエラーが発生しました: {e}"
            response_content = "処理中に予期せぬエラーが発生しました。"
        finally:
            # 最終的な回答をユーザーに送信
            bot_response_message.content = response_content
            # 必要であれば、context_docs_meta を Chainlit の要素として追加
            if context_docs_meta:
                elements = [
                    cl.Text(name=f"ソース {i+1}", content=json.dumps(doc, indent=2), display="accordion")
                    for i, doc in enumerate(context_docs_meta)
                ]
                bot_response_message.elements = elements
            await bot_response_message.update()
            print("app.py: 最終的な応答を送信しました。") # デバッグログ
