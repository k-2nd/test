import os
import chainlit as cl
import httpx # requestsの代わりにhttpxをインポート
import asyncio # 非同期処理のためにインポート
import boto3
import re
import json
from chainlit.input_widget import Select, Slider
from botocore.config import Config
from urllib.parse import urlparse # URL解析のためにインポート

# --- 環境変数から設定を取得 ---
# API Gatewayの標準エンドポイントURL（環境変数で設定）
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL")
if not API_GATEWAY_URL:
    raise ValueError("API_GATEWAY_URL 環境変数が設定されていません。App Runnerサービス設定で設定してください。")

# API GatewayのVPCエンドポイントのDNS名（環境変数で設定）
# プライベートDNSが有効でない場合、このエンドポイントを使用します
VPC_ENDPOINT_DNS_NAME = os.environ.get("VPC_ENDPOINT_DNS_NAME")
# プライベートDNSが無効な場合はVPC_ENDPOINT_DNS_NAMEの設定が必須
USE_VPC_ENDPOINT = VPC_ENDPOINT_DNS_NAME is not None and VPC_ENDPOINT_DNS_NAME != ""

if USE_VPC_ENDPOINT:
    # API GatewayのHostヘッダーを動的に生成
    # 例: <your-api-id>.execute-api.ap-northeast-1.amazonaws.com
    parsed_api_url = urlparse(API_GATEWAY_URL)
    # パス部分を除外したAPI Gatewayのホスト名のみを取得
    API_GATEWAY_HOST_HEADER = parsed_api_url.netloc
    # 最終的なリクエストURLをVPCエンドポイントのDNS名で構築
    TARGET_API_URL = f"https://{VPC_ENDPOINT_DNS_NAME}{parsed_api_url.path}"
    print(f"DEBUG: Using VPC Endpoint. TARGET_API_URL: {TARGET_API_URL}, Host Header: {API_GATEWAY_HOST_HEADER}")
else:
    # プライベートDNSが有効な場合、またはパブリックAPI Gatewayにアクセスする場合
    TARGET_API_URL = API_GATEWAY_URL
    API_GATEWAY_HOST_HEADER = None # Hostヘッダーは自動で設定されるため不要
    print(f"DEBUG: Not using VPC Endpoint for direct access. TARGET_API_URL: {TARGET_API_URL}")

# --- その他の設定（変更なし） ---
# BedrockモデルIDのパターンマッチング用正規表現
PATTERN = re.compile(r'v\d+(?!.*\d[kK]$)')

# デフォルトモデルID
FALLBACK_DEFAULT_MODELID = "anthropic.claude-sonnet-4-20250514-v1:0"

# デフォルトの温度（LLMの応答の多様性）
DEFAULT_TEMPERATURE = 0.3
# デフォルトの最大トークン数（LLMが生成する応答の長さ）
DEFAULT_MAX_TOKENS = 4096

# LambdaのINFERENCE_MAPPINGと同期する、利用可能なモデルキーのリスト（表示用）
INFERENCE_MAPPING_KEYS = [
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
]

# Bedrockクライアントの共通設定
# API呼び出しのタイムアウト時間とリトライポリシーを定義
bedrock_config = Config(
    read_timeout=60, # Bedrock APIからの応答を待つ最大時間（秒）
    retries={
        'max_attempts': 2, # リトライの最大試行回数
        'mode': 'standard' # 標準のリトライモード
    }
)

@cl.on_chat_start
async def start():
    """
    チャット開始時に実行される関数。
    UIの初期設定（モデル選択、温度、最大トークン数スライダー）を行う。
    """
    print(f"app.py: @cl.on_chat_startがトリガーされました。API_GATEWAY_URL: {API_GATEWAY_URL}")
    print(f"app.py: VPC_ENDPOINT_DNS_NAME: {VPC_ENDPOINT_DNS_NAME}, USE_VPC_ENDPOINT: {USE_VPC_ENDPOINT}")
    if USE_VPC_ENDPOINT:
        print(f"app.py: TARGET_API_URL: {TARGET_API_URL}, API_GATEWAY_HOST_HEADER: {API_GATEWAY_HOST_HEADER}")

    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    
    # boto3クライアントを初期化し、共通設定を適用
    bedrock = boto3.client("bedrock", region_name=aws_region, config=bedrock_config) 

    model_options = []
    try:
        # 1. Foundation Modelのリストを取得（オンデマンドモデル）
        print("app.py: bedrock.list_foundation_modelsを呼び出し中...")
        response_fm = bedrock.list_foundation_models(
            byOutputModality="TEXT" # テキスト生成モデルに限定
        )
        for item in response_fm["modelSummaries"]:
            model_id = item['modelId']
            # 定義済みのキーに含まれるモデル、またはINFERENCE_MAPPING_KEYSが空の場合は全て追加
            if model_id in INFERENCE_MAPPING_KEYS or not INFERENCE_MAPPING_KEYS:
                model_options.append(model_id)
        print(f"app.py: ListFoundationModelsから{len(model_options)}個の基盤モデルが見つかりました。")

        # 2. 推論プロファイルのリストを取得し、その対象モデルIDをリストに追加
        print("app.py: bedrock.list_inference_profilesを呼び出し中...")
        response_ip = bedrock.list_inference_profiles()
        for item in response_ip["inferenceProfileSummaries"]:
            profile_name = item['inferenceProfileName']
            profile_id = item['inferenceProfileId']
            # 推論プロファイル名/IDから関連するモデルキーを特定し、オプションに追加
            for lm_key in INFERENCE_MAPPING_KEYS:
                # 推論プロファイルとモデルの紐付けロジック（例: 名前に特定の文字列が含まれるか）
                if (lm_key.lower().replace('-', '') in profile_name.lower().replace('-', '') and \
                    (lm_key.startswith("anthropic.claude-3") and "claude-3" in profile_id.lower())) or \
                   (lm_key.startswith("amazon.nova") and "nova" in profile_id.lower()):
                    model_options.append(lm_key) # UIではINFERENCE_MAPPING_KEYSのキー値を表示し、Lambdaに渡す
                    break # 一致するものがあれば追加して次へ

        # 重複を排除し、モデルオプションをアルファベット順にソート
        model_options = sorted(list(set(model_options)))

        print(f"app.py: {len(response_ip['inferenceProfileSummaries'])}個の推論プロファイルが見つかりました。合計オプション数 (重複排除後): {len(model_options)}")

        if not model_options:
            print("app.py: モデルオプションが取得できませんでした。フォールバックのデフォルトモデルを使用します。")
            await cl.Message(content="警告: Bedrockモデルまたは推論プロファイルのリスト取得に失敗しました。デフォルトモデルを使用します。", author="システム").send()

    except Exception as e:
        print(f"app.py: モデルリスト取得中にエラーが発生しました: {e}")
        model_options = [FALLBACK_DEFAULT_MODELID] # エラー時もデフォルトモデルは設定
        await cl.Message(content=f"警告: Bedrockモデルのリスト取得中にエラーが発生しました: {e}。デフォルトモデルを使用します。App RunnerのIAMロールに`bedrock:ListFoundationModels`, `bedrock:ListInferenceProfiles`の権限があるか確認してください。", author="システム").send()

    # デフォルトモデルの初期選択インデックスを決定
    default_model_index = 0
    if FALLBACK_DEFAULT_MODELID in model_options:
        default_model_index = model_options.index(FALLBACK_DEFAULT_MODELID)
        print(f"app.py: デフォルトモデル '{FALLBACK_DEFAULT_MODELID}' がインデックス {default_model_index} で見つかりました。")
    elif model_options:
        print("app.py: フォールバックのデフォルトモデルがオプションに見つかりませんでした。最初の利用可能なオプションをデフォルトとして設定します。")
        default_model_index = 0
    else:
        print("app.py: 利用可能なモデルオプションがありません。デフォルトインデックスは0のままです。")

    # ChatSettingsUIを設定
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="Amazon Bedrock - モデル / 推論プロファイル",
                values=model_options,
                initial_index=default_model_index,
            ),
            Slider(
                id="Temperature",
                label="温度",
                initial=DEFAULT_TEMPERATURE, # 初期値としてDEFAULT_TEMPERATUREを適用
                min=0,
                max=1,
                step=0.1,
            ),
            Slider(
                id="MAX_TOKEN_SIZE",
                label="最大トークン数",
                initial=DEFAULT_MAX_TOKENS, # 初期値としてDEFAULT_MAX_TOKENSを適用
                min=256,
                max=8192, # モデルの最大コンテキストウィンドウに合わせて調整可能
                step=256,
                ),
            ]
        ).send()

    cl.user_session.set("settings", settings) # 現在の設定をユーザーセッションに保存
    cl.user_session.set("chat_history", []) # 会話履歴を初期化
    print(f"app.py: チャット設定が初期化され、セッション変数が設定されました。")

    await cl.Message(
        content=f"スマート企業探索 のテストアプリへようこそ！\n\nメッセージを送信してください。",
    ).send()

@cl.on_settings_update
async def setup_chat_settings(settings):
    """
    チャット設定が更新されたときに実行される関数。
    """
    print(f"app.py: @cl.on_settings_updateがトリガーされました。新しい設定: {settings}")
    cl.user_session.set("settings", settings)
    await cl.Message(content="設定が更新されました。").send()

@cl.on_message
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
            request_headers = {}
            if USE_VPC_ENDPOINT and API_GATEWAY_HOST_HEADER:
                request_headers["Host"] = API_GATEWAY_HOST_HEADER
                print(f"app.py: Hostヘッダーを設定: {API_GATEWAY_HOST_HEADER}")
            
            # API呼び出しを非同期タスクとして実行
            api_call_task = asyncio.create_task(
                client.post(TARGET_API_URL, json=payload, headers=request_headers)
            )
            # --- ここまで修正 ---

            # タスクが完了するか、停止要求があるまで待機
            # ChainlitのメッセージストリームAPIを使用することで、より細やかな制御も可能ですが、
            # ここではシンプルなタスクキャンセルで実装
            while not api_call_task.done():
                if message.should_stop: # ユーザーが「停止」ボタンを押した場合
                    print("app.py: ユーザーが回答生成をキャンセルしました。") # デバッグログ
                    api_call_task.cancel() # タスクをキャンセル
                    raise asyncio.CancelledError("回答生成がユーザーによってキャンセルされました。")
                await asyncio.sleep(0.1) # 短い間隔でチェック

            # タスクの結果を取得
            api_response = await api_call_task # キャンセルされていない場合はここで応答を取得
            api_response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる

            print(f"app.py: API Gatewayから応答を受信しました (HTTPステータス: {api_response.status_code})。") # デバッグログ
            response_data = api_response.json()
            print(f"app.py: API応答データ: {response_data}") # デバッグログ

            if "response" in response_data:
                # LLMからの最終回答を取得
                response_content = response_data["response"]
                # 関連ドキュメントのメタデータを取得
                if "context_docs_meta" in response_data and response_data["context_docs_meta"]:
                    context_docs_meta = response_data["context_docs_meta"]
                    print(f"app.py: API Gatewayから{len(context_docs_meta)}件の関連ドキュメントを受信しました。")
                else:
                    print("app.py: API Gatewayから関連ドキュメントは受信されませんでした。")
                print(f"app.py: API Gatewayからの応答 (先頭200文字): {response_content[:200]}...")
            elif "error" in response_data: # Lambdaからのエラーメッセージを処理
                print("app.py: API Gatewayからエラーキーを含む応答を受信しました。") # デバッグログ
                error_code = response_data.get('error', 'Unknown_Error')
                error_details = response_data.get('details', '詳細不明')
                
                # エラーコードに基づいてユーザーフレンドリーなメッセージを生成
                if error_code == 'Elasticsearch_Connection_Error':
                    response_content = "現在、情報検索システムが利用できません。Elasticsearchに接続できませんでした。システム管理者にお問い合わせください。"
                    print(f"app.py: Elasticsearch接続エラーを受信しました: {error_details}")
                elif error_code == 'Embeddings_Generation_Error':
                    response_content = "質問の理解に問題が発生しました。Bedrockの埋め込みモデルにアクセスできない可能性があります。システム管理者にお問い合わせください。"
                    print(f"app.py: 埋め込み生成エラーを受信しました: {error_details}")
                elif error_code == 'Invalid_Request_Body':
                    response_content = f"入力されたメッセージの形式に問題があります。詳細: {error_details}"
                    print(f"app.py: 無効なリクエストボディエラーを受信しました: {error_details}")
                else:
                    # その他のバックエンドエラー
                    response_content = f"バックエンドで予期せぬエラーが発生しました。詳細: {error_details}"
                    print(f"app.py: その他のバックエンドエラーを受信しました: {error_details}")
            else:
                response_content = f"API Gatewayからの予期せぬ応答: {response_data}"
                print(f"app.py: API Gatewayからの応答構造が予期せぬものでした: {response_data}")

        except asyncio.CancelledError:
            response_content = "回答の生成がユーザーによってキャンセルされました。"
            print("app.py: asyncio.CancelledErrorを捕捉しました。") # デバッグログ
        except httpx.TimeoutException: # httpx独自のタイムアウト例外
            response_content = "API Gatewayへの接続がタイムアウトしました。バックエンドの処理（Elasticsearch検索やLLM推論）に時間がかかっている可能性があります。システム管理者にお問い合わせください。"
            print("app.py: httpx.TimeoutExceptionを捕捉しました。") # デバッグログ
        except httpx.RequestError as e: # httpx独自の一般的なリクエストエラー
            print(f"app.py: httpx.RequestErrorを捕捉しました: {e}") # デバッグログ
            if e.response is not None:
                # HTTPエラー応答が返された場合の詳細処理
                try:
                    error_response_data = e.response.json()
                    print(f"app.py: RequestError.response.json()を解析しました: {error_response_data}") # デバッグログ
                    if "error" in error_response_data:
                        error_code = error_response_data.get('error', 'Unknown_Error')
                        error_details = error_response_data.get('details', '詳細不明')
                        
                        if error_code == 'Elasticsearch_Connection_Error':
                            response_content = f"現在、情報検索システムが利用できません。Elasticsearchに接続できませんでした。システム管理者にお問い合わせください。詳細: {error_details}"
                            print(f"app.py: Elasticsearch接続エラーを受信しました（HTTPエラー経由）: {error_details}")
                        elif error_code == 'Embeddings_Generation_Error':
                            response_content = f"質問の理解に問題が発生しました。Bedrockの埋め込みモデルにアクセスできない可能性があります。システム管理者にお問い合わせください。詳細: {error_details}"
                            print(f"app.py: 埋め込み生成エラーを受信しました（HTTPエラー経由）: {error_details}")
                        elif error_code == 'Invalid_Request_Body':
                            response_content = f"入力されたメッセージの形式に問題があります。詳細: {error_details}"
                            print(f"app.py: 無効なリクエストボディエラーを受信しました（HTTPエラー経由）: {error_details}")
                        elif error_code == 'Internal_Server_Error':
                            response_content = f"バックエンドで予期せぬエラーが発生しました。詳細: {error_details}"
                            print(f"app.py: その他のバックエンドエラーを受信しました（HTTPエラー経由）: {error_details}")
                        else:
                            response_content = f"バックエンドエラー: {error_response_data.get('details', '不明なエラーが発生しました。')}"
                            print(f"app.py: 不明なバックエンドエラーを受信しました（HTTPエラー経由）: {error_response_data}")
                    else:
                        response_content = f"API Gatewayからの予期せぬエラー応答: HTTP {e.response.status_code} - {e.response.text}"
                        print(f"app.py: API Gatewayからの予期せぬエラー応答を受信しました: {e.response.text}")
                except json.JSONDecodeError:
                    print("app.py: RequestError.responseのJSON解析に失敗しました。") # デバッグログ
                    response_content = f"API Gatewayからのエラー応答を解析できませんでした: HTTP {e.response.status_code} - {e.response.text}"
                    print(f"app.py: API Gatewayからのエラー応答をJSONとして解析できませんでした: {e.response.text}")
                except Exception as inner_e:
                    print(f"app.py: RequestError処理中に予期せぬエラーが発生しました: {inner_e}") # デバッグログ
                    response_content = f"API Gatewayエラー応答の処理中に予期せぬエラー: {inner_e}. 元のエラー: {e}"
                    print(f"app.py: エラー応答処理中に予期せぬエラー: {inner_e}. 元のエラー: {e}")
            else:
                response_content = f"API Gatewayへの接続エラーが発生しました: {e}。ネットワーク接続やバックエンドの稼働状況を確認してください。"
                print(f"app.py: エラー: API Gateway接続エラー（応答なし）: {e}")
        except Exception as e: # その他の予期せぬフロントエンドエラー
            print(f"app.py: 予期せぬ汎用エラーを捕捉しました: {e}") # デバッグログ
            response_content = f"フロントエンドで予期せぬエラーが発生しました: {e}。システム管理者にお問い合わせください。"
            print(f"app.py: エラー: API呼び出し中に予期せぬエラーが発生しました: {e}")
        finally:
            print("app.py: finallyブロックを実行中...") # デバッグログ
            # 最終的な回答またはエラーメッセージをbot_response_messageに設定し、更新
            bot_response_message.content = response_content
            bot_response_message.author = "チャットボット (Bedrock RAG)" # 最終的な著者を設定
            await bot_response_message.update() # この更新で以前のステータスメッセージが置き換えられる
            print("app.py: 最終回答/エラーメッセージでステータスメッセージを更新しました。") # デバッグログ

    # 関連ドキュメントがある場合、それをユーザーに表示 (bot_response_messageとは別の新しいメッセージとして)
    if context_docs_meta:
        elements = []
        for doc in context_docs_meta:
            title = doc.get("タイトル", "不明なタイトル")
            url = doc.get("URL", "#")
            doc_id = doc.get("ID", "N/A")
            elements.append(
                cl.Element(name=f"{title} (ID: {doc_id})", url=url, display="inline") # インラインで表示される要素として追加
            )
        await cl.Message(
            content="**参照情報:**", # 参照情報であることを示すヘッダー
            elements=elements, # 関連ドキュメントを要素として追加
            author="システム"
        ).send()
        print("app.py: 参照情報を送信しました。") # デバッグログ

    # 会話履歴を更新
    chat_history.append(f"Human: {user_message}")
    chat_history.append(f"AI: {response_content}")
    cl.user_session.set("chat_history", chat_history)
    print("app.py: 会話履歴が更新されました。") # デバッグログ
