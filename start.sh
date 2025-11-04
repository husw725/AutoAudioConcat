#!/bin/bash
# 启动 Streamlit 连续语音拼接工具

# 设置 Python 环境（可选，根据需要启用）
# source venv/bin/activate

APP_FILE="app.py"

# 检查文件是否存在
if [ ! -f "$APP_FILE" ]; then
  echo "❌ 未找到 $APP_FILE，请确认路径正确"
  exit 1
fi

# 启动 Streamlit 应用
echo "🚀 启动 Streamlit 应用中..."
streamlit run "$APP_FILE" --server.port 8501 --server.address 0.0.0.0